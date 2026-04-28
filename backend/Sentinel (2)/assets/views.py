"""
Asset Upload and Management Views for SENTINEL
"""
import json
import os
import time
import uuid
from datetime import datetime
from urllib import parse, request
from urllib.error import HTTPError, URLError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from core.hashing import generate_file_hash
from core.mongodb import get_asset_manager, get_mongo_connection
from blockchain import blockchain_service


AI_PIPELINE_BASE_URL = os.environ.get('AI_PIPELINE_BASE_URL', 'http://127.0.0.1:8080').rstrip('/')
AI_PIPELINE_TIMEOUT_SEC = float(os.environ.get('AI_PIPELINE_TIMEOUT_SEC', '10'))
DEMO_AI_ON_UPLOAD = os.environ.get('SENTINEL_DEMO_AI', '0').strip().lower() in {'1', 'true', 'yes'}
LIVE_INGEST_ON_UPLOAD = os.environ.get('SENTINEL_LIVE_INGEST_ON_UPLOAD', '1').strip().lower() in {'1', 'true', 'yes'}
LIVE_INGEST_LIMIT = int(os.environ.get('SENTINEL_LIVE_INGEST_LIMIT', '10'))
LIVE_INGEST_SOURCES = [
    s.strip().lower()
    for s in os.environ.get('SENTINEL_LIVE_INGEST_SOURCES', 'youtube,x,instagram,reddit').split(',')
    if s.strip()
]


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


def _infer_media_type(file_obj: UploadedFile) -> str:
    content_type = str(getattr(file_obj, 'content_type', '') or '').lower()
    if content_type.startswith('image/'):
        return 'image'
    if content_type.startswith('video/'):
        return 'video'
    if content_type.startswith('audio/'):
        return 'audio'

    extension = os.path.splitext(file_obj.name)[1].lower().lstrip('.')
    if extension in {'jpg', 'jpeg', 'png', 'webp', 'bmp'}:
        return 'image'
    if extension in {'mp4', 'mov', 'mkv', 'avi', 'webm'}:
        return 'video'
    if extension in {'mp3', 'wav', 'flac', 'ogg', 'aac', 'm4a', 'opus'}:
        return 'audio'

    return 'image'


def _map_ai_case_status(case_status: str) -> str:
    status = str(case_status or '').upper()
    if status in {'AUTO_NOTICE', 'HUMAN_REVIEW', 'MONITOR', 'NO_MATCH'}:
        return 'checked'
    if status in {
        'STACK_UNAVAILABLE',
        'NO_REFERENCES',
        'FETCH_FAILED',
        'PROCESS_FAILED',
        'WORKER_ERROR',
        'UNSUPPORTED_MEDIA',
        'NO_VALID_REFERENCES',
    }:
        return 'failed'
    return 'checking'


def _make_demo_ai_case(asset_id: str, file_name: str) -> dict:
    case_id = f"DEMO-{uuid.uuid4().hex[:8].upper()}"
    return {
        'case_id': case_id,
        'job_id': f"demo-job-{uuid.uuid4().hex[:8]}",
        'status': 'AUTO_NOTICE',
        'score': 0.934,
        'action': 'AUTO_NOTICE',
        'matched_asset_id': str(asset_id),
        'media_url': file_name,
        'platform': 'upload',
    }


def _insert_demo_violation(file_name: str, file_hash: str, user_id: str) -> None:
    conn = get_mongo_connection()
    col = conn.get_collection('violations')
    now = datetime.utcnow()
    col.insert_one(
        {
            'p': 'UPLOAD',
            'a': file_name,
            'sim': '93.4%',
            'time': now.isoformat() + 'Z',
            'sev': 'high',
            'status': 'Sent',
            'source': 'demo',
            'user_id': user_id,
            'asset_hash': file_hash,
            'created_at': now,
        }
    )


def _trigger_live_ingest() -> dict:
    results: dict[str, dict] = {}
    for source in LIVE_INGEST_SOURCES:
        path = f"/ingest/{source}/real"
        payload = _ai_request('POST', path, query={'limit': LIVE_INGEST_LIMIT})
        if payload is None:
            results[source] = {'connected': False, 'message': 'AI pipeline unavailable'}
        else:
            results[source] = payload
    return results


class AssetUploadView(APIView):
    """Asset Upload View - JWT Authentication Required"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Upload asset file (video/image) and store metadata in MongoDB
        """
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file_obj = request.FILES['file']
            
            # Validate file
            validation_error = self._validate_file(file_obj)
            if validation_error:
                return Response(validation_error, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate unique filename
            file_extension = os.path.splitext(file_obj.name)[1].lower()
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create upload directory if it doesn't exist
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'videos')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(upload_dir, unique_filename)
            with open(file_path, 'wb') as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)
            
            # Generate file hash
            with open(file_path, 'rb') as f:
                file_hash = generate_file_hash(f)
            
            # Check if file with same hash already exists
            asset_manager = get_asset_manager()
            existing_asset = asset_manager.get_asset_by_hash(file_hash)
            if existing_asset:
                # Remove uploaded file as it's a duplicate
                os.remove(file_path)
                return Response(
                    {
                        'message': 'File already exists',
                        'asset_id': existing_asset['_id'],
                        'file_hash': file_hash,
                        'duplicate': True
                    },
                    status=status.HTTP_200_OK
                )
            
            # Prepare asset metadata
            asset_data = {
                'user_id': str(request.user.id),
                'file_name': file_obj.name,
                'file_path': f"/media/videos/{unique_filename}",
                'file_hash': file_hash,
                'uploaded_at': datetime.utcnow(),
                'status': 'checking',
                'metadata': {
                    'size': file_obj.size,
                    'content_type': file_obj.content_type,
                    'original_name': file_obj.name
                },
                'fingerprints': {
                    'phash': None,
                    'dhash': None,
                    'video': None
                }
            }
            
            # Store in MongoDB
            asset_id = asset_manager.insert_asset(asset_data)

            ai_payload = None
            ai_job_id = None
            ai_error = None
            if DEMO_AI_ON_UPLOAD:
                demo_case = _make_demo_ai_case(asset_id, file_obj.name)
                asset_manager.update_asset(
                    asset_id,
                    {
                        'status': 'checked',
                        'ai_case_status': demo_case['status'],
                        'ai_case_id': demo_case['case_id'],
                        'ai_score': demo_case['score'],
                        'ai_action': demo_case['action'],
                        'ai_job_id': demo_case['job_id'],
                        'ai_enqueued_at': datetime.utcnow(),
                    },
                )
                _insert_demo_violation(file_obj.name, file_hash, str(request.user.id))
                ai_payload = {'enqueued': True, 'job_id': demo_case['job_id'], 'case': demo_case}
            else:
                try:
                    enqueue_body = {
                        'platform': 'youtube',
                        'post_id': str(asset_id),
                        'account_id': str(request.user.id),
                        'timestamp': time.time(),
                        'media_type': _infer_media_type(file_obj),
                        'media_url': file_path,
                        'caption': f"Uploaded asset: {file_obj.name}",
                        'hashtags': [],
                    }
                    ai_response = _ai_request('POST', '/ingest/post', body=enqueue_body) or {}
                    if ai_response.get('enqueued'):
                        ai_job_id = ai_response.get('job_id')
                        ai_payload = {'enqueued': True, 'job_id': ai_job_id}
                        asset_manager.update_asset(
                            asset_id,
                            {
                                'status': 'checking',
                                'ai_job_id': ai_job_id,
                                'ai_enqueued_at': datetime.utcnow(),
                            },
                        )
                    else:
                        ai_error = ai_response.get('message') or 'AI pipeline did not accept the job.'
                except Exception as exc:  # noqa: BLE001
                    ai_error = str(exc)
                if ai_error:
                    asset_manager.update_asset(asset_id, {'status': 'pending', 'ai_error': ai_error})
                    ai_payload = {'enqueued': False, 'error': ai_error}

            blockchain_payload = None
            try:
                org_name = (
                    getattr(request.user, 'organization_name', None)
                    or getattr(request.user, 'org_name', None)
                    or getattr(request.user, 'full_name', None)
                    or request.user.email
                )
                record = blockchain_service.register_asset(
                    phash=file_hash,
                    asset_name=file_obj.name,
                    org_name=str(org_name),
                    user_id=str(request.user.id),
                )
                blockchain_payload = {
                    'mode': record.get('mode'),
                    'network': record.get('network'),
                    'tx_hash': record.get('tx_hash'),
                    'block_number': record.get('block_number') or record.get('blockNumber'),
                    'blockNumber': record.get('block_number') or record.get('blockNumber'),
                    'explorer_url': record.get('explorer_url'),
                    'status': record.get('status'),
                    'id': record.get('id'),
                }
            except Exception:
                # Keep upload successful even if demo chain write fails.
                blockchain_payload = None
            
            live_payload = None
            if LIVE_INGEST_ON_UPLOAD:
                live_payload = _trigger_live_ingest()

            return Response(
                {
                    'message': 'Upload successful',
                    'asset_id': asset_id,
                    'file_hash': file_hash,
                    'file_path': asset_data['file_path'],
                    'metadata': asset_data['metadata'],
                    'status': 'checked' if DEMO_AI_ON_UPLOAD else ('checking' if ai_job_id else 'pending'),
                    'ai': ai_payload,
                    'live_ingest': live_payload,
                    'blockchain': blockchain_payload,
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {'error': f'Upload failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _validate_file(self, file_obj: UploadedFile) -> dict:
        """
        Validate uploaded file
        
        Returns:
            Error dict if validation fails, None if valid
        """
        # Check file size
        max_size = getattr(settings, 'MAX_FILE_SIZE', 50 * 1024 * 1024)  # 50MB
        if file_obj.size > max_size:
            return {
                'error': 'File too large',
                'max_size': f"{max_size // (1024 * 1024)}MB",
                'file_size': f"{file_obj.size // (1024 * 1024)}MB"
            }
        
        # Check file type
        allowed_types = getattr(settings, 'ALLOWED_FILE_TYPES', ['mp4', 'jpg', 'jpeg', 'png'])
        file_extension = os.path.splitext(file_obj.name)[1].lower().lstrip('.')
        
        if file_extension not in allowed_types:
            return {
                'error': 'File type not allowed',
                'allowed_types': allowed_types,
                'file_type': file_extension
            }
        
        return None


class AssetListView(APIView):
    """List user's uploaded assets"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get list of assets for the authenticated user
        """
        try:
            # Get query parameters
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            skip = (page - 1) * limit
            
            # Fetch assets
            asset_manager = get_asset_manager()
            assets = asset_manager.get_assets(
                user_id=str(request.user.id),
                limit=limit,
                skip=skip
            )

            job_ids = [
                asset.get('ai_job_id')
                for asset in assets
                if asset.get('ai_job_id') and str(asset.get('status') or '').lower() in {'checking', 'pending', 'processing'}
            ]
            if job_ids:
                cases_payload = _ai_request('GET', '/cases', query={'limit': 500}) or {}
                cases = cases_payload.get('items') if isinstance(cases_payload, dict) else []
                if isinstance(cases, list) and cases:
                    case_by_job = {case.get('job_id'): case for case in cases if isinstance(case, dict)}
                    for asset in assets:
                        job_id = asset.get('ai_job_id')
                        if not job_id:
                            continue
                        case = case_by_job.get(job_id)
                        if not case:
                            continue
                        mapped_status = _map_ai_case_status(case.get('status'))
                        update_data = {
                            'status': mapped_status,
                            'ai_case_status': case.get('status'),
                            'ai_case_id': case.get('case_id'),
                            'ai_score': case.get('score'),
                            'ai_action': case.get('action'),
                        }
                        asset_manager.update_asset(asset['_id'], update_data)
                        asset.update(update_data)
            
            return Response(
                {
                    'assets': assets,
                    'page': page,
                    'limit': limit,
                    'total': len(assets)
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch assets: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AssetDetailView(APIView):
    """Get details of a specific asset"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, asset_id: str):
        """
        Get asset details by ID
        """
        try:
            asset_manager = get_asset_manager()
            asset = asset_manager.get_asset_by_id(asset_id)
            
            if not asset:
                return Response(
                    {'error': 'Asset not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if asset belongs to the user
            if asset['user_id'] != str(request.user.id):
                return Response(
                    {'error': 'Access denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return Response(asset, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch asset: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, asset_id: str):
        """
        Delete an asset
        """
        try:
            asset_manager = get_asset_manager()
            asset = asset_manager.get_asset_by_id(asset_id)
            
            if not asset:
                return Response(
                    {'error': 'Asset not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if asset belongs to the user
            if asset['user_id'] != str(request.user.id):
                return Response(
                    {'error': 'Access denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Delete file from filesystem
            file_path = os.path.join(settings.MEDIA_ROOT, asset['file_path'].lstrip('/media/'))
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete from MongoDB
            success = asset_manager.delete_asset(asset_id)
            
            if success:
                return Response(
                    {'message': 'Asset deleted successfully'}, 
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': 'Failed to delete asset'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            return Response(
                {'error': f'Failed to delete asset: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
