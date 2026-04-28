"""
vector_db/db_client.py
──────────────────────────────────────────────────────────────
Production Milvus client — manages all collections for
image, video, and audio fingerprint storage and search.

Collections:
  image_fingerprints  — CLIP (512) + DINOv2 (768) embeddings
  video_fingerprints  — CLIP summary (512) + DINOv2 summary (768)
  audio_fingerprints  — Wav2Vec2 (1024) embeddings

All collections use HNSW index — O(log N) search,
handles billions of vectors, sub-10ms query time.
"""

from __future__ import annotations

import time
from typing import Optional
from pymilvus import (
    connections, utility,
    Collection, CollectionSchema, FieldSchema, DataType,
)

from ai_pipeline.utils.logger import get_logger
from ai_pipeline.utils.config import config

logger = get_logger(__name__)


# ── Collection names ────────────────────────────────────────
IMAGE_COLLECTION  = "image_fingerprints"
VIDEO_COLLECTION  = "video_fingerprints"
AUDIO_COLLECTION  = "audio_fingerprints"

# ── Embedding dimensions ─────────────────────────────────────
DIM_CLIP    = 512
DIM_DINOV2  = 768
DIM_WAV2VEC = 1024

# ── HNSW index params ────────────────────────────────────────
# M=16: connections per node (higher = better recall, more memory)
# efConstruction=256: build-time search depth (higher = better index)
HNSW_INDEX = {
    "metric_type": "COSINE",
    "index_type":  "HNSW",
    "params":      {"M": 16, "efConstruction": 256},
}

SEARCH_PARAMS = {"metric_type": "COSINE", "params": {"ef": 64}}


class MilvusClient:
    """
    Production Milvus client.
    Manages connections, collection creation, and health checks.
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        alias: str = "default",
    ):
        self.host  = host or config.milvus.host
        self.port  = port or config.milvus.port
        self.alias = alias
        self._connected = False

    # ── connection ───────────────────────────────────────────

    def connect(self, retries: int = 5, delay: float = 3.0) -> None:
        """Connect to Milvus with retry logic."""
        for attempt in range(1, retries + 1):
            try:
                connections.connect(
                    alias=self.alias,
                    host=self.host,
                    port=self.port,
                )
                self._connected = True
                logger.info(
                    f"Milvus connected | "
                    f"host={self.host}:{self.port} | alias={self.alias}"
                )
                return
            except Exception as e:
                logger.warning(
                    f"Milvus connection attempt {attempt}/{retries} failed: {e}"
                )
                if attempt < retries:
                    time.sleep(delay)

        raise ConnectionError(
            f"Failed to connect to Milvus at {self.host}:{self.port} "
            f"after {retries} attempts"
        )

    def disconnect(self) -> None:
        connections.disconnect(self.alias)
        self._connected = False
        logger.info("Milvus disconnected")

    def is_connected(self) -> bool:
        try:
            connections.get_connection_addr(self.alias)
            return True
        except Exception:
            return False

    # ── collection setup ─────────────────────────────────────

    def setup_all_collections(self) -> None:
        """Create all collections if they don't exist."""
        self._ensure_connected()
        self._setup_image_collection()
        self._setup_video_collection()
        self._setup_audio_collection()
        logger.info("All Milvus collections ready")

    def _setup_image_collection(self) -> Collection:
        if utility.has_collection(IMAGE_COLLECTION):
            logger.info(f"Collection '{IMAGE_COLLECTION}' already exists")
            col = Collection(IMAGE_COLLECTION)
            col.load()
            return col

        fields = [
            FieldSchema("id",            DataType.INT64,         is_primary=True, auto_id=True),
            FieldSchema("asset_id",      DataType.VARCHAR,       max_length=256),
            FieldSchema("owner_id",      DataType.VARCHAR,       max_length=256),
            FieldSchema("file_hash",     DataType.VARCHAR,       max_length=128),
            FieldSchema("asset_type",    DataType.VARCHAR,       max_length=32),
            FieldSchema("source_path",   DataType.VARCHAR,       max_length=512),
            FieldSchema("watermark_hash",DataType.VARCHAR,       max_length=128),
            FieldSchema("registered_at", DataType.DOUBLE),
            # Dual embeddings — both stored per asset
            FieldSchema("clip_embedding",   DataType.FLOAT_VECTOR, dim=DIM_CLIP),
            FieldSchema("dinov2_embedding", DataType.FLOAT_VECTOR, dim=DIM_DINOV2),
        ]

        schema = CollectionSchema(
            fields=fields,
            description="Image fingerprints — CLIP + DINOv2 dual embeddings",
            enable_dynamic_field=True,
        )

        col = Collection(IMAGE_COLLECTION, schema)

        # Create HNSW index on both embedding fields
        col.create_index("clip_embedding",   HNSW_INDEX)
        col.create_index("dinov2_embedding", HNSW_INDEX)
        col.load()

        logger.info(f"Collection '{IMAGE_COLLECTION}' created with HNSW index")
        return col

    def _setup_video_collection(self) -> Collection:
        if utility.has_collection(VIDEO_COLLECTION):
            logger.info(f"Collection '{VIDEO_COLLECTION}' already exists")
            col = Collection(VIDEO_COLLECTION)
            col.load()
            return col

        fields = [
            FieldSchema("id",              DataType.INT64,  is_primary=True, auto_id=True),
            FieldSchema("asset_id",        DataType.VARCHAR, max_length=256),
            FieldSchema("owner_id",        DataType.VARCHAR, max_length=256),
            FieldSchema("file_hash",       DataType.VARCHAR, max_length=128),
            FieldSchema("source_path",     DataType.VARCHAR, max_length=512),
            FieldSchema("duration_sec",    DataType.DOUBLE),
            FieldSchema("frame_count",     DataType.INT64),
            FieldSchema("registered_at",   DataType.DOUBLE),
            # Summary embeddings (mean-pooled across all frames)
            FieldSchema("clip_summary",    DataType.FLOAT_VECTOR, dim=DIM_CLIP),
            FieldSchema("dinov2_summary",  DataType.FLOAT_VECTOR, dim=DIM_DINOV2),
        ]

        schema = CollectionSchema(
            fields=fields,
            description="Video fingerprints — frame-level mean-pooled embeddings",
            enable_dynamic_field=True,
        )

        col = Collection(VIDEO_COLLECTION, schema)
        col.create_index("clip_summary",   HNSW_INDEX)
        col.create_index("dinov2_summary", HNSW_INDEX)
        col.load()

        logger.info(f"Collection '{VIDEO_COLLECTION}' created with HNSW index")
        return col

    def _setup_audio_collection(self) -> Collection:
        if utility.has_collection(AUDIO_COLLECTION):
            logger.info(f"Collection '{AUDIO_COLLECTION}' already exists")
            col = Collection(AUDIO_COLLECTION)
            col.load()
            return col

        fields = [
            FieldSchema("id",            DataType.INT64,  is_primary=True, auto_id=True),
            FieldSchema("asset_id",      DataType.VARCHAR, max_length=256),
            FieldSchema("owner_id",      DataType.VARCHAR, max_length=256),
            FieldSchema("file_hash",     DataType.VARCHAR, max_length=128),
            FieldSchema("source_path",   DataType.VARCHAR, max_length=512),
            FieldSchema("chunk_index",   DataType.INT64),
            FieldSchema("start_sec",     DataType.DOUBLE),
            FieldSchema("end_sec",       DataType.DOUBLE),
            FieldSchema("registered_at", DataType.DOUBLE),
            # Wav2Vec2 embedding
            FieldSchema("wav2vec_embedding", DataType.FLOAT_VECTOR, dim=DIM_WAV2VEC),
        ]

        schema = CollectionSchema(
            fields=fields,
            description="Audio fingerprints — Wav2Vec2 chunk embeddings",
            enable_dynamic_field=True,
        )

        col = Collection(AUDIO_COLLECTION, schema)
        col.create_index("wav2vec_embedding", HNSW_INDEX)
        col.load()

        logger.info(f"Collection '{AUDIO_COLLECTION}' created with HNSW index")
        return col

    # ── utility ──────────────────────────────────────────────

    def get_collection_stats(self) -> dict:
        """Get entity counts for all collections."""
        self._ensure_connected()
        stats = {}
        for name in [IMAGE_COLLECTION, VIDEO_COLLECTION, AUDIO_COLLECTION]:
            if utility.has_collection(name):
                col = Collection(name)
                stats[name] = col.num_entities
            else:
                stats[name] = 0
        return stats

    def drop_all_collections(self) -> None:
        """Drop all collections — use only for testing/reset."""
        self._ensure_connected()
        for name in [IMAGE_COLLECTION, VIDEO_COLLECTION, AUDIO_COLLECTION]:
            if utility.has_collection(name):
                utility.drop_collection(name)
                logger.warning(f"Collection '{name}' dropped")

    def _ensure_connected(self) -> None:
        if not self.is_connected():
            self.connect()