import hashlib
import importlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from django.conf import settings


def _get_mongo_connection():
    module = importlib.import_module('core.mongodb')
    return module.get_mongo_connection()


class BlockchainService:
    def __init__(self) -> None:
        self.mode = str(getattr(settings, 'BLOCKCHAIN_MODE', 'demo')).lower()
        self.network = str(getattr(settings, 'BLOCKCHAIN_NETWORK_LABEL', 'Polygon Amoy (Simulated)'))
        self.explorer = str(getattr(settings, 'BLOCKCHAIN_EXPLORER_BASE', 'https://amoy.polygonscan.com/tx/')).rstrip('/') + '/'
        self.contract = str(getattr(settings, 'BLOCKCHAIN_CONTRACT_ADDRESS', '0xDEMO_CONTRACT'))
        self._counter_key = 'blockchain_demo_counter'

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _next_block_number(self) -> int:
        conn = _get_mongo_connection()
        col = conn.get_collection('system_counters')
        doc = col.find_one_and_update(
            {'_id': self._counter_key},
            {'$inc': {'seq': 1}},
            upsert=True,
            return_document=True,
        )
        seq = int((doc or {}).get('seq', 1))
        return 50000000 + seq

    def _demo_tx_hash(self, seed: str) -> str:
        digest = hashlib.sha256(seed.encode('utf-8')).hexdigest()
        return '0x' + digest[:64]

    def register_asset(
        self,
        *,
        phash: str,
        asset_name: str,
        org_name: str,
        user_id: str,
        ipfs_cid: Optional[str] = None,
    ) -> Dict[str, Any]:
        block_number = self._next_block_number()
        seed = f"{phash}|{asset_name}|{org_name}|{user_id}|{block_number}|{time.time_ns()}"
        tx_hash = self._demo_tx_hash(seed)
        record = {
            'id': f'BLK-{block_number}',
            'hash': tx_hash,
            'tx_hash': tx_hash,
            'block_number': block_number,
            'blockNumber': block_number,
            'asset': asset_name,
            'phash': phash,
            'org_name': org_name,
            'user_id': user_id,
            'ipfs_cid': ipfs_cid,
            'contract_address': self.contract,
            'network': self.network,
            'status': 'CONFIRMED (DEMO)',
            'explorer_url': f'{self.explorer}{tx_hash}',
            'time': self._now_iso(),
            'created_at': datetime.now(timezone.utc),
            'mode': self.mode,
            'kind': 'asset_registration',
        }
        conn = _get_mongo_connection()
        conn.get_collection('blockchain_records').insert_one(record)
        return record

    def log_violation(
        self,
        *,
        phash: str,
        violation_url: str,
        platform: str,
        risk_score: float,
        user_id: str,
        evidence_cid: Optional[str] = None,
    ) -> Dict[str, Any]:
        block_number = self._next_block_number()
        seed = f"violation|{phash}|{violation_url}|{platform}|{block_number}|{time.time_ns()}"
        tx_hash = self._demo_tx_hash(seed)
        record = {
            'id': f'VIO-{block_number}',
            'hash': tx_hash,
            'tx_hash': tx_hash,
            'block_number': block_number,
            'blockNumber': block_number,
            'asset': phash,
            'phash': phash,
            'violation_url': violation_url,
            'platform': platform,
            'risk_score': risk_score,
            'evidence_cid': evidence_cid,
            'user_id': user_id,
            'contract_address': self.contract,
            'network': self.network,
            'status': 'CONFIRMED (DEMO)',
            'explorer_url': f'{self.explorer}{tx_hash}',
            'time': self._now_iso(),
            'created_at': datetime.now(timezone.utc),
            'mode': self.mode,
            'kind': 'violation_log',
        }
        conn = _get_mongo_connection()
        conn.get_collection('blockchain_records').insert_one(record)
        return record

    def verify_asset(self, phash: str) -> Dict[str, Any]:
        conn = _get_mongo_connection()
        col = conn.get_collection('blockchain_records')
        doc = col.find_one({'phash': phash, 'kind': 'asset_registration'})
        if not doc:
            return {
                'registered': False,
                'phash': phash,
                'network': self.network,
                'mode': self.mode,
            }
        return {
            'registered': True,
            'phash': phash,
            'tx_hash': doc.get('tx_hash') or doc.get('hash'),
            'block_number': doc.get('block_number'),
            'blockNumber': doc.get('block_number') or doc.get('blockNumber'),
            'asset': doc.get('asset'),
            'org_name': doc.get('org_name'),
            'time': doc.get('time'),
            'network': doc.get('network'),
            'status': doc.get('status'),
            'explorer_url': doc.get('explorer_url'),
            'mode': doc.get('mode'),
        }


blockchain_service = BlockchainService()
