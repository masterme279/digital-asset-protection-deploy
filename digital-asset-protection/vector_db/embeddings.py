"""
vector_db/embeddings.py
──────────────────────────────────────────────────────────────
High-level insert and search operations for all three
fingerprint types — image, video, audio.

Insert: store fingerprint in Milvus
Search: find top-K similar assets by embedding
"""

from __future__ import annotations

import time
import numpy as np
from typing import Optional
from pymilvus import Collection

from vector_db.db_client import (
    MilvusClient,
    IMAGE_COLLECTION, VIDEO_COLLECTION, AUDIO_COLLECTION,
    SEARCH_PARAMS,
)
from ai_pipeline.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingStore:
    """
    Insert and search fingerprints across all three modalities.

    Usage:
        client = MilvusClient()
        client.connect()
        client.setup_all_collections()

        store = EmbeddingStore(client)
        store.insert_image(fingerprint, asset_id, owner_id)
        results = store.search_image(query_clip, query_dino, top_k=5)
    """

    def __init__(self, client: MilvusClient):
        self.client = client

    @staticmethod
    def _normalize(vec: np.ndarray) -> np.ndarray:
        """L2-normalize a vector so COSINE metric works correctly."""
        norm = np.linalg.norm(vec)
        if norm < 1e-9:
            return vec
        return (vec / norm).astype(np.float32)

    # ── IMAGE ─────────────────────────────────────────────────

    def insert_image(
        self,
        fingerprint: dict,
        asset_id: str,
        owner_id: str,
        watermark_hash: str = "",
    ) -> dict:
        """
        Insert image fingerprint into Milvus.

        Parameters
        ----------
        fingerprint  : output from ImageProcessor.get_combined_fingerprint()
        asset_id     : unique asset identifier
        owner_id     : rights holder ID
        watermark_hash: from WatermarkEmbedder (optional)
        """
        col = Collection(IMAGE_COLLECTION)

        clip_emb  = self._normalize(fingerprint["clip_embedding"]).tolist()
        dino_emb  = self._normalize(fingerprint["dinov2_embedding"]).tolist()

        data = [
            [asset_id],
            [owner_id],
            [fingerprint.get("file_hash", "")],
            ["image"],
            [fingerprint.get("source_path", "")],
            [watermark_hash],
            [time.time()],
            [clip_emb],
            [dino_emb],
        ]

        result = col.insert(data)
        col.flush()

        logger.info(
            f"Image inserted | asset={asset_id} | "
            f"id={result.primary_keys[0]}"
        )
        return {
            "inserted_id": result.primary_keys[0],
            "asset_id":    asset_id,
            "collection":  IMAGE_COLLECTION,
        }

    def search_image(
        self,
        clip_embedding:   np.ndarray,
        dinov2_embedding: np.ndarray,
        top_k: int = 5,
        owner_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Search for similar images using CLIP + DINOv2 embeddings.
        Returns top-K matches sorted by combined score.
        """
        col    = Collection(IMAGE_COLLECTION)
        expr   = f'owner_id == "{owner_filter}"' if owner_filter else ""
        output = ["asset_id", "owner_id", "file_hash", "source_path", "watermark_hash"]

        # Search CLIP
        clip_results = col.search(
            data=[self._normalize(clip_embedding).tolist()],
            anns_field="clip_embedding",
            param=SEARCH_PARAMS,
            limit=top_k * 2,
            expr=expr or None,
            output_fields=output,
        )

        # Search DINOv2
        dino_results = col.search(
            data=[self._normalize(dinov2_embedding).tolist()],
            anns_field="dinov2_embedding",
            param=SEARCH_PARAMS,
            limit=top_k * 2,
            expr=expr or None,
            output_fields=output,
        )

        # Fuse results — weighted combination
        return self._fuse_results(
            clip_results[0], dino_results[0],
            clip_weight=0.4, dino_weight=0.6,
            top_k=top_k,
        )

    # ── VIDEO ─────────────────────────────────────────────────

    def insert_video(
        self,
        fingerprint: dict,
        asset_id: str,
        owner_id: str,
    ) -> dict:
        """Insert video fingerprint into Milvus."""
        col = Collection(VIDEO_COLLECTION)

        meta = fingerprint.get("metadata", {})
        data = [
            [asset_id],
            [owner_id],
            [fingerprint.get("file_hash", "")],
            [fingerprint.get("source_path", "")],
            [float(meta.get("duration_sec", 0))],
            [int(fingerprint.get("frame_count", 0))],
            [time.time()],
            [self._normalize(fingerprint["clip_summary"]).tolist()],
            [self._normalize(fingerprint["dino_summary"]).tolist()],
        ]

        result = col.insert(data)
        col.flush()

        logger.info(
            f"Video inserted | asset={asset_id} | "
            f"frames={fingerprint.get('frame_count', 0)}"
        )
        return {
            "inserted_id": result.primary_keys[0],
            "asset_id":    asset_id,
            "collection":  VIDEO_COLLECTION,
        }

    def search_video(
        self,
        clip_summary:   np.ndarray,
        dinov2_summary: np.ndarray,
        top_k: int = 5,
    ) -> list[dict]:
        """Search for similar videos using summary embeddings."""
        col    = Collection(VIDEO_COLLECTION)
        output = ["asset_id", "owner_id", "file_hash",
                  "source_path", "duration_sec", "frame_count"]

        clip_results = col.search(
            data=[self._normalize(clip_summary).tolist()],
            anns_field="clip_summary",
            param=SEARCH_PARAMS,
            limit=top_k * 2,
            output_fields=output,
        )

        dino_results = col.search(
            data=[self._normalize(dinov2_summary).tolist()],
            anns_field="dinov2_summary",
            param=SEARCH_PARAMS,
            limit=top_k * 2,
            output_fields=output,
        )

        return self._fuse_results(
            clip_results[0], dino_results[0],
            clip_weight=0.4, dino_weight=0.6,
            top_k=top_k,
        )

    # ── AUDIO ─────────────────────────────────────────────────

    def insert_audio(
        self,
        embedding_result,
        asset_id: str,
        owner_id: str,
        file_hash: str = "",
        source_path: str = "",
    ) -> dict:
        """Insert audio chunk embedding into Milvus."""
        col = Collection(AUDIO_COLLECTION)

        data = [
            [asset_id],
            [owner_id],
            [file_hash],
            [source_path],
            [int(embedding_result.chunk_index)],
            [float(embedding_result.start_sec)],
            [float(embedding_result.end_sec)],
            [time.time()],
            [embedding_result.embedding.tolist()],
        ]

        result = col.insert(data)
        col.flush()

        logger.info(
            f"Audio chunk inserted | asset={asset_id} | "
            f"chunk={embedding_result.chunk_index}"
        )
        return {
            "inserted_id": result.primary_keys[0],
            "asset_id":    asset_id,
            "collection":  AUDIO_COLLECTION,
        }

    def search_audio(
        self,
        wav2vec_embedding: np.ndarray,
        top_k: int = 5,
        owner_filter: Optional[str] = None,
    ) -> list[dict]:
        """Search for similar audio chunks."""
        col    = Collection(AUDIO_COLLECTION)
        expr   = f'owner_id == "{owner_filter}"' if owner_filter else ""
        output = ["asset_id", "owner_id", "file_hash",
                  "source_path", "chunk_index", "start_sec", "end_sec"]

        results = col.search(
            data=[wav2vec_embedding.tolist()],
            anns_field="wav2vec_embedding",
            param=SEARCH_PARAMS,
            limit=top_k,
            expr=expr or None,
            output_fields=output,
        )

        matches = []
        for hit in results[0]:
            score = round(float(hit.score), 4)
            matches.append({
                "score":          score,
                "combined_score": score,          # ← add this line
                "asset_id":       hit.entity.get("asset_id"),
                "owner_id":       hit.entity.get("owner_id"),
                "file_hash":      hit.entity.get("file_hash"),
                "source_path":    hit.entity.get("source_path"),
                "chunk_index":    hit.entity.get("chunk_index"),
                "start_sec":      hit.entity.get("start_sec"),
                "end_sec":        hit.entity.get("end_sec"),
                "collection":     AUDIO_COLLECTION,
            })

        logger.info(f"Audio search | top_k={top_k} | found={len(matches)}")
        return matches

    # ── fusion ────────────────────────────────────────────────

    @staticmethod
    def _fuse_results(
        clip_hits,
        dino_hits,
        clip_weight: float,
        dino_weight: float,
        top_k: int,
    ) -> list[dict]:
        """
        Fuse CLIP and DINOv2 search results by weighted score combination.
        Assets appearing in both result sets get boosted scores.
        """
        scores: dict[str, dict] = {}

        for hit in clip_hits:
            asset_id = hit.entity.get("asset_id", str(hit.id))
            if asset_id not in scores:
                scores[asset_id] = {
                    "clip_score":  0.0,
                    "dino_score":  0.0,
                    "entity":      hit.entity,
                    "id":          hit.id,
                }
            scores[asset_id]["clip_score"] = float(hit.score)

        for hit in dino_hits:
            asset_id = hit.entity.get("asset_id", str(hit.id))
            if asset_id not in scores:
                scores[asset_id] = {
                    "clip_score":  0.0,
                    "dino_score":  0.0,
                    "entity":      hit.entity,
                    "id":          hit.id,
                }
            scores[asset_id]["dino_score"] = float(hit.score)

        # Compute fused score
        results = []
        for asset_id, data in scores.items():
            fused = (clip_weight  * data["clip_score"] +
                     dino_weight * data["dino_score"])
            entity = data["entity"]
            results.append({
                "asset_id":      asset_id,
                "owner_id":      entity.get("owner_id", ""),
                "file_hash":     entity.get("file_hash", ""),
                "source_path":   entity.get("source_path", ""),
                "watermark_hash":entity.get("watermark_hash", ""),
                "clip_score":    round(data["clip_score"],  4),
                "dino_score":    round(data["dino_score"],  4),
                "combined_score":round(fused, 4),
                "milvus_id":     data["id"],
            })

        return sorted(results, key=lambda x: x["combined_score"], reverse=True)[:top_k]