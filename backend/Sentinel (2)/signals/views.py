"""
Signals endpoints for SENTINEL
"""
import json
import os
import random
from urllib import parse, request
from urllib.error import URLError, HTTPError
from datetime import datetime
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from core.mongodb import get_mongo_connection
from blockchain import blockchain_service


def _serialize_doc(doc):
    if not doc:
        return doc
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    for key, value in list(doc.items()):
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc


def _read_collection(name: str, limit: int = 200, sort_field: str = 'created_at'):
    try:
        conn = get_mongo_connection()
        collection = conn.get_collection(name)
        cursor = collection.find({}).sort(sort_field, -1).limit(limit)
        return [_serialize_doc(doc) for doc in cursor]
    except Exception:
        return []


AI_PIPELINE_BASE_URL = os.environ.get('AI_PIPELINE_BASE_URL', 'http://127.0.0.1:8080').rstrip('/')
AI_PIPELINE_TIMEOUT_SEC = float(os.environ.get('AI_PIPELINE_TIMEOUT_SEC', '8'))
AUTO_SEED_SIGNALS = os.environ.get('SENTINEL_AUTO_SEED', '1').strip().lower() in {'1', 'true', 'yes'}


_THREAT_SEEDS = [
    {'city': 'New York', 'center': [40.7128, -74.0060]},
    {'city': 'London', 'center': [51.5072, -0.1276]},
    {'city': 'Mumbai', 'center': [19.0760, 72.8777]},
    {'city': 'Singapore', 'center': [1.3521, 103.8198]},
    {'city': 'Sao Paulo', 'center': [-23.5505, -46.6333]},
    {'city': 'Lagos', 'center': [6.5244, 3.3792]},
    {'city': 'Tokyo', 'center': [35.6895, 139.6917]},
    {'city': 'Sydney', 'center': [-33.8688, 151.2093]},
]


def _collection_empty(name: str) -> bool:
    try:
        conn = get_mongo_connection()
        collection = conn.get_collection(name)
        return collection.count_documents({}) == 0
    except Exception:
        return True


def _seed_collection(name: str, items: list[dict]) -> None:
    if not items:
        return
    try:
        conn = get_mongo_connection()
        collection = conn.get_collection(name)
        if collection.count_documents({}) > 0:
            return
        now = datetime.utcnow()
        for item in items:
            item.setdefault('created_at', now)
        collection.insert_many(items)
    except Exception:
        return


def _insert_collection(name: str, payload: dict) -> dict | None:
    if not payload:
        return None
    try:
        conn = get_mongo_connection()
        collection = conn.get_collection(name)
        result = collection.insert_one(payload)
        payload['_id'] = str(result.inserted_id)
        return _serialize_doc(payload)
    except Exception:
        return None


def _demo_assets(limit: int = 8) -> list[dict]:
    try:
        conn = get_mongo_connection()
        collection = conn.get_collection('assets')
        return list(collection.find({}).sort('uploaded_at', -1).limit(limit))
    except Exception:
        return []


def _build_demo_violations(assets: list[dict]) -> list[dict]:
    now = datetime.utcnow().isoformat() + 'Z'
    items = []
    for idx, asset in enumerate(assets):
        name = asset.get('file_name') or asset.get('metadata', {}).get('original_name') or f'Asset {idx + 1}'
        score = 0.88 + (idx % 5) * 0.02
        items.append(
            {
                'p': 'UPLOAD',
                'a': name,
                'sim': f"{round(score * 100, 1)}%",
                'time': now,
                'sev': _safe_level(score),
                'status': 'Sent',
                'auto': True,
                'source': 'demo',
                'score': score,
            }
        )
    return items


def _build_demo_forecast(points: int = 12) -> list[dict]:
    now = datetime.utcnow()
    items = []
    for i in range(points):
        t = now.replace(minute=0, second=0, microsecond=0)
        t = t.replace(hour=(t.hour - (points - 1 - i)) % 24)
        prediction = 10 + (i * 7) % 80
        items.append({'time': t.isoformat() + 'Z', 'predictions': prediction})
    return items


def _build_demo_threat_markers(violations: list[dict]) -> list[dict]:
    items = []
    count = max(3, min(len(_THREAT_SEEDS), len(violations) or 6))
    for i in range(count):
        base = _THREAT_SEEDS[i % len(_THREAT_SEEDS)]
        severity = 'critical' if i % 5 == 0 else 'high' if i % 2 == 0 else 'med'
        items.append(
            {
                'id': f"TM-{i + 1}",
                'city': base['city'],
                'center': base['center'],
                'violations': random.randint(3, 16),
                'severity': severity,
            }
        )
    return items


def _build_demo_dmca(violations: list[dict]) -> list[dict]:
    items = []
    for idx, violation in enumerate(violations[:6]):
        items.append(
            {
                'id': f"DMCA-{1000 + idx}",
                'asset': violation.get('a') or f"Asset {idx + 1}",
                'platform': violation.get('p') or 'Unknown',
                'status': 'Complied' if idx % 3 == 0 else 'Sent',
                'auto': True,
                'txHash': violation.get('txHash') or violation.get('hash') or 'DEMO-TX',
                'similarity': violation.get('sim') or '90.0%',
                'date': violation.get('time') or datetime.utcnow().isoformat() + 'Z',
                'takedown_hours': 2 + idx,
            }
        )
    return items


def _safe_level(score: float) -> str:
    if score >= 0.95:
        return 'high'
    if score >= 0.82:
        return 'med'
    return 'low'


def _safe_status(action: str, status: str) -> str:
    action_l = str(action or '').lower()
    status_l = str(status or '').lower()
    if 'auto' in action_l or 'takedown' in action_l:
        return 'Sent'
    if 'review' in action_l or 'pending' in status_l:
        return 'Review'
    if 'closed' in status_l or 'resolved' in status_l:
        return 'Blocked'
    return 'Review'


def _to_violation_from_case(item: dict) -> dict:
    score = float(item.get('score') or 0)
    percent = max(0.0, min(100.0, round(score * 100, 1)))
    created_at = item.get('created_at')
    time_label = ''
    if isinstance(created_at, (int, float)):
        time_label = datetime.utcfromtimestamp(created_at).isoformat() + 'Z'
    elif created_at:
        time_label = str(created_at)

    platform = str(item.get('platform') or 'Unknown').upper()
    media = str(item.get('media_url') or item.get('post_id') or 'Unknown asset')
    matched = str(item.get('matched_asset_id') or '').strip()
    asset_label = matched if matched else media
    action = str(item.get('action') or '')
    status = str(item.get('status') or '')

    return {
        'p': platform,
        'a': asset_label,
        'sim': f'{percent:.1f}%',
        'time': time_label,
        'sev': _safe_level(score),
        'status': _safe_status(action, status),
        'auto': 'auto' in action.lower() or 'takedown' in action.lower(),
        'source': 'ai_pipeline',
        'raw_case_id': item.get('case_id'),
        'score': score,
        'action': action,
    }


def _normalize_ai_case(item: dict) -> dict:
    case = dict(item or {})
    score = float(case.get('score') or case.get('confidence') or 0)

    # Keep existing fields untouched while providing compatibility aliases
    # expected by frontend cards and smoke checks.
    if not case.get('source_type'):
        case['source_type'] = str(case.get('platform') or case.get('source') or 'unknown').lower()
    if not case.get('severity'):
        case['severity'] = _safe_level(score)
    if case.get('confidence') is None:
        case['confidence'] = score
    if not case.get('created_at'):
        case['created_at'] = datetime.utcnow().isoformat() + 'Z'

    return case


def _ai_request(method: str, path: str, query: dict | None = None, body: dict | None = None):
    url = f"{AI_PIPELINE_BASE_URL}{path}"
    if query:
        url = f"{url}?{parse.urlencode(query)}"

    data = None
    headers = {'Accept': 'application/json'}
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'

    req = request.Request(url=url, method=method.upper(), headers=headers, data=data)

    try:
        with request.urlopen(req, timeout=AI_PIPELINE_TIMEOUT_SEC) as res:
            payload = res.read().decode('utf-8')
            return json.loads(payload) if payload else {}
    except (URLError, HTTPError, TimeoutError, ValueError):
        return None


class ViolationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = _read_collection('violations', limit=500)
        ai_cases = _ai_request('GET', '/cases', query={'limit': 200}) or {}
        ai_items = ai_cases.get('items') if isinstance(ai_cases, dict) else []
        if isinstance(ai_items, list) and ai_items:
            items.extend([_to_violation_from_case(case) for case in ai_items])
        if AUTO_SEED_SIGNALS and not items:
            assets = _demo_assets()
            seeded = _build_demo_violations(assets)
            _seed_collection('violations', seeded)
            items = _read_collection('violations', limit=500)
        return Response({'violations': items})


class ForecastView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = _read_collection('forecasts', limit=500, sort_field='time')
        if AUTO_SEED_SIGNALS and not data:
            _seed_collection('forecasts', _build_demo_forecast())
            data = _read_collection('forecasts', limit=500, sort_field='time')
        return Response({'forecast': data})


class ThreatMapView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        markers = _read_collection('threat_markers', limit=500)
        if AUTO_SEED_SIGNALS and not markers:
            violations = _read_collection('violations', limit=200)
            _seed_collection('threat_markers', _build_demo_threat_markers(violations))
            markers = _read_collection('threat_markers', limit=500)
        return Response({'markers': markers})


class BlockchainProofsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        records = _read_collection('blockchain_records', limit=500)
        return Response({'records': records})


class BlockchainModeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        mode = str(getattr(blockchain_service, 'mode', 'demo')).lower()
        return Response(
            {
                'mode': mode,
                'network': getattr(blockchain_service, 'network', 'Polygon Amoy (Simulated)'),
                'status': 'CONFIRMED (DEMO)' if mode == 'demo' else 'CONFIRMED',
            },
            status=200,
        )


class BlockchainRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phash = str(request.data.get('phash') or '').strip()
        asset_name = str(request.data.get('asset_name') or '').strip()
        org_name = (
            str(request.data.get('org_name') or '').strip()
            or getattr(request.user, 'organization_name', None)
            or getattr(request.user, 'org_name', None)
            or getattr(request.user, 'full_name', None)
            or request.user.email
        )
        ipfs_cid = request.data.get('ipfs_cid')

        if not phash or not asset_name:
            return Response({'error': 'phash and asset_name are required'}, status=400)

        record = blockchain_service.register_asset(
            phash=phash,
            asset_name=asset_name,
            org_name=str(org_name),
            user_id=str(request.user.id),
            ipfs_cid=ipfs_cid,
        )
        return Response({'ok': True, 'record': _serialize_doc(record)}, status=201)


class BlockchainVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        phash = str(request.GET.get('phash') or '').strip()
        if not phash:
            return Response({'error': 'phash query param is required'}, status=400)
        return Response(blockchain_service.verify_asset(phash), status=200)


class BlockchainViolationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phash = str(request.data.get('phash') or '').strip()
        violation_url = str(request.data.get('violation_url') or '').strip()
        platform = str(request.data.get('platform') or 'unknown')
        risk_score = float(request.data.get('risk_score') or 0)
        evidence_cid = request.data.get('evidence_cid')

        if not phash or not violation_url:
            return Response({'error': 'phash and violation_url are required'}, status=400)

        record = blockchain_service.log_violation(
            phash=phash,
            violation_url=violation_url,
            platform=platform,
            risk_score=risk_score,
            user_id=str(request.user.id),
            evidence_cid=evidence_cid,
        )
        return Response({'ok': True, 'record': _serialize_doc(record)}, status=201)


class DmcaNoticesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notices = _read_collection('dmca_notices', limit=500)
        if AUTO_SEED_SIGNALS and not notices:
            violations = _read_collection('violations', limit=200)
            seeded = _build_demo_dmca(violations)
            _seed_collection('dmca_notices', seeded)
            notices = _read_collection('dmca_notices', limit=500)
        return Response({'notices': notices})

    def post(self, request):
        asset = str(request.data.get('asset') or '').strip()
        platform = str(request.data.get('platform') or '').strip()
        url = str(request.data.get('url') or '').strip()
        similarity = str(request.data.get('similarity') or '').strip()
        status = str(request.data.get('status') or 'Sent').strip()
        notes = str(request.data.get('notes') or '').strip()

        if not asset or not platform or not url:
            return Response({'error': 'asset, platform, and url are required'}, status=400)

        ref_id = f"DMCA-{int(datetime.utcnow().timestamp())}-{random.randint(100, 999)}"
        payload = {
            'id': ref_id,
            'asset': asset,
            'platform': platform,
            'status': status,
            'auto': False,
            'url': url,
            'similarity': similarity or None,
            'notes': notes or None,
            'issuer_email': request.user.email,
            'user_id': str(request.user.id),
            'date': datetime.utcnow().isoformat() + 'Z',
            'created_at': datetime.utcnow(),
        }

        created = _insert_collection('dmca_notices', payload)
        if not created:
            return Response({'error': 'Unable to save DMCA notice'}, status=500)

        return Response({'notice': created}, status=201)


class AiHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payload = _ai_request('GET', '/health')
        if payload is None:
            return Response({'connected': False, 'message': 'AI pipeline unavailable'})
        return Response({'connected': True, 'health': payload})


class AiCasesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.GET.get('limit', 100))
        status_filter = request.GET.get('status')
        payload = _ai_request('GET', '/cases', query={'limit': limit, 'status': status_filter} if status_filter else {'limit': limit})
        if payload is None:
            return Response({'items': [], 'connected': False})
        raw_items = payload.get('items', []) if isinstance(payload, dict) else []
        items = [_normalize_ai_case(item) for item in raw_items if isinstance(item, dict)]
        return Response({'items': items, 'connected': True})


class AiAuditView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.GET.get('limit', 100))
        payload = _ai_request('GET', '/audit', query={'limit': limit})
        if payload is None:
            return Response({'items': [], 'connected': False})
        return Response({'items': payload.get('items', []), 'connected': True})


class AiYouTubeMockIngestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        limit = int(request.data.get('limit', 20))
        payload = _ai_request('POST', '/ingest/youtube/mock', query={'limit': limit})
        if payload is None:
            return Response({'connected': False, 'enqueued': 0, 'message': 'AI pipeline unavailable'})
        return Response({'connected': True, **payload})


class AiYouTubeRealIngestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        limit = int(request.data.get('limit', 10))
        query = request.data.get('query')
        channel_id = request.data.get('channel_id')
        query_params = {'limit': limit}
        if query:
            query_params['query'] = query
        if channel_id:
            query_params['channel_id'] = channel_id
        payload = _ai_request('POST', '/ingest/youtube/real', query=query_params)
        if payload is None:
            return Response({'connected': False, 'enqueued': 0, 'message': 'AI pipeline unavailable'})
        return Response({'connected': True, **payload})


class AiXRealIngestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        limit = int(request.data.get('limit', 25))
        query = request.data.get('query')
        query_params = {'limit': limit}
        if query:
            query_params['query'] = query
        payload = _ai_request('POST', '/ingest/x/real', query=query_params)
        if payload is None:
            return Response({'connected': False, 'enqueued': 0, 'message': 'AI pipeline unavailable'})
        return Response({'connected': True, **payload})


class AiInstagramRealIngestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        limit = int(request.data.get('limit', 10))
        payload = _ai_request('POST', '/ingest/instagram/real', query={'limit': limit})
        if payload is None:
            return Response({'connected': False, 'enqueued': 0, 'message': 'AI pipeline unavailable'})
        return Response({'connected': True, **payload})


class AiRedditRealIngestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        limit = int(request.data.get('limit', 25))
        query = request.data.get('query')
        subreddit = request.data.get('subreddit')
        query_params = {'limit': limit}
        if query:
            query_params['query'] = query
        if subreddit:
            query_params['subreddit'] = subreddit
        payload = _ai_request('POST', '/ingest/reddit/real', query=query_params)
        if payload is None:
            return Response({'connected': False, 'enqueued': 0, 'message': 'AI pipeline unavailable'})
        return Response({'connected': True, **payload})
