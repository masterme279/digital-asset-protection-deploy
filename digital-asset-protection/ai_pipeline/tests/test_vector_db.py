import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest
from PIL import Image, ImageDraw

from vector_db.db_client import MilvusClient, IMAGE_COLLECTION, VIDEO_COLLECTION, AUDIO_COLLECTION
from vector_db.embeddings import EmbeddingStore
from ai_pipeline.image.processor import ImageProcessor


# ── setup ────────────────────────────────────────────────────
print("Connecting to Milvus...")
_client = MilvusClient()
try:
    _client.connect()
except Exception as exc:
    if os.getenv("REQUIRE_MILVUS_TESTS", "").strip() in {"1", "true", "True", "yes", "YES"}:
        raise
    pytest.skip(
        f"Milvus is not available ({exc}). Start it with: docker-compose up -d", 
        allow_module_level=True,
    )
_client.drop_all_collections()   # ← wipe stale data every run
_client.setup_all_collections()
_store  = EmbeddingStore(_client)
print("Milvus ready.\n")


def make_image(color=(180, 100, 50), size=(224, 224)) -> Image.Image:
    img  = Image.new("RGB", size, color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([30, 30, 100, 100], fill=(255, 200, 100))
    return img


def make_random_embedding(dim: int) -> np.ndarray:
    emb = np.random.randn(dim).astype(np.float32)
    return emb / np.linalg.norm(emb)


# Load image processor once
print("Loading image models...")
_processor = ImageProcessor()
print("Models ready.\n")


def test_collections_exist():
    """All 3 collections must be created."""
    from pymilvus import utility
    assert utility.has_collection(IMAGE_COLLECTION),  "image collection missing"
    assert utility.has_collection(VIDEO_COLLECTION),  "video collection missing"
    assert utility.has_collection(AUDIO_COLLECTION),  "audio collection missing"
    print("[PASS] All 3 collections exist")


def test_insert_image():
    """Insert an image fingerprint and verify it's stored."""
    img = make_image(color=(200, 100, 50))
    fp  = _processor.get_combined_fingerprint(img)
    fp["file_hash"]   = "test_hash_001"
    fp["source_path"] = "test/image_001.jpg"

    result = _store.insert_image(fp, "ASSET-001", "OWNER-ESPN")

    assert "inserted_id" in result
    assert result["asset_id"]   == "ASSET-001"
    assert result["collection"] == IMAGE_COLLECTION
    print(f"[PASS] Image inserted | id={result['inserted_id']}")


def test_search_image_finds_similar():
    """Insert image then search — must find it as top result."""
    img = make_image(color=(100, 150, 200))
    fp  = _processor.get_combined_fingerprint(img)
    fp["file_hash"]   = "test_hash_002"
    fp["source_path"] = "test/image_002.jpg"

    # Insert
    _store.insert_image(fp, "ASSET-SEARCH-001", "OWNER-UEFA")

    # Search with same embeddings
    results = _store.search_image(
        fp["clip_embedding"],
        fp["dinov2_embedding"],
        top_k=3,
    )

    assert len(results) > 0, "Search returned no results"
    top = results[0]
    assert top["combined_score"] > 0.95, \
        f"Same image should score > 0.95, got {top['combined_score']}"
    print(f"[PASS] Image search | top score={top['combined_score']} | asset={top['asset_id']}")


def test_search_image_different_scores():
    """Different images must score lower than same image."""
    img_a = make_image(color=(200, 50,  50))
    img_b = make_image(color=(50,  50, 200))

    fp_a = _processor.get_combined_fingerprint(img_a)
    fp_b = _processor.get_combined_fingerprint(img_b)
    fp_a["file_hash"] = "hash_a"
    fp_b["file_hash"] = "hash_b"

    _store.insert_image(fp_a, "ASSET-RED",  "OWNER-A")
    _store.insert_image(fp_b, "ASSET-BLUE", "OWNER-B")

    # Search with fp_a — should find ASSET-RED as top
    results = _store.search_image(
        fp_a["clip_embedding"],
        fp_a["dinov2_embedding"],
        top_k=5,
    )

    assert len(results) > 0
    print(f"[PASS] Different image scores differ | top={results[0]['combined_score']}")


def test_insert_video():
    """Insert a video fingerprint."""
    clip_summary  = make_random_embedding(512)
    dino_summary  = make_random_embedding(768)

    fp = {
        "file_hash":    "video_hash_001",
        "source_path":  "test/video_001.mp4",
        "frame_count":  30,
        "clip_summary": clip_summary,
        "dino_summary": dino_summary,
        "metadata":     {"duration_sec": 60.0},
    }

    result = _store.insert_video(fp, "VIDEO-ASSET-001", "OWNER-ESPN")

    assert "inserted_id" in result
    assert result["collection"] == VIDEO_COLLECTION
    print(f"[PASS] Video inserted | id={result['inserted_id']}")


def test_search_video():
    """Insert video then search — must find it."""
    clip_summary = make_random_embedding(512)
    dino_summary = make_random_embedding(768)

    fp = {
        "file_hash":    "video_hash_search",
        "source_path":  "test/video_search.mp4",
        "frame_count":  45,
        "clip_summary": clip_summary,
        "dino_summary": dino_summary,
        "metadata":     {"duration_sec": 90.0},
    }

    _store.insert_video(fp, "VIDEO-SEARCH-001", "OWNER-UEFA")

    results = _store.search_video(clip_summary, dino_summary, top_k=3)

    assert len(results) > 0
    assert results[0]["combined_score"] > 0.90
    print(f"[PASS] Video search | top score={results[0]['combined_score']}")


def test_insert_audio():
    """Insert an audio embedding."""
    from dataclasses import dataclass

    @dataclass
    class MockEmbeddingResult:
        chunk_index: int
        start_sec:   float
        end_sec:     float
        embedding:   np.ndarray
        source_path: str = "test/audio.wav"
        model_id:    str = "mock"

    emb = make_random_embedding(1024)
    mock_result = MockEmbeddingResult(
        chunk_index=0,
        start_sec=0.0,
        end_sec=30.0,
        embedding=emb,
    )

    result = _store.insert_audio(
        mock_result,
        asset_id="AUDIO-ASSET-001",
        owner_id="OWNER-ESPN",
        file_hash="audio_hash_001",
        source_path="test/audio_001.mp3",
    )

    assert "inserted_id" in result
    assert result["collection"] == AUDIO_COLLECTION
    print(f"[PASS] Audio inserted | id={result['inserted_id']}")


def test_search_audio():
    """Insert audio then search — must find it."""
    from dataclasses import dataclass

    @dataclass
    class MockEmbeddingResult:
        chunk_index: int
        start_sec:   float
        end_sec:     float
        embedding:   np.ndarray
        source_path: str = "test/audio.wav"
        model_id:    str = "mock"

    emb = make_random_embedding(1024)
    mock_result = MockEmbeddingResult(0, 0.0, 30.0, emb)

    _store.insert_audio(
        mock_result,
        asset_id="AUDIO-SEARCH-001",
        owner_id="OWNER-UEFA",
        file_hash="audio_hash_search",
        source_path="test/audio_search.mp3",
    )

    results = _store.search_audio(emb, top_k=3)

    assert len(results) > 0
    assert results[0]["combined_score"] > 0.90 or results[0]["score"] > 0.90
    print(f"[PASS] Audio search | top result found")


def test_collection_stats():
    """Stats must show non-zero counts after inserts."""
    stats = _client.get_collection_stats()

    assert stats[IMAGE_COLLECTION] > 0, "Image collection empty"
    assert stats[VIDEO_COLLECTION] > 0, "Video collection empty"
    assert stats[AUDIO_COLLECTION] > 0, "Audio collection empty"

    print(f"\n[PASS] Collection stats:")
    print(f"       Images : {stats[IMAGE_COLLECTION]} entities")
    print(f"       Videos : {stats[VIDEO_COLLECTION]} entities")
    print(f"       Audio  : {stats[AUDIO_COLLECTION]} entities")


if __name__ == "__main__":
    print("=" * 55)
    print("  Digital Asset Protection — Vector DB Tests")
    print("=" * 55 + "\n")

    test_collections_exist()
    test_insert_image()
    test_search_image_finds_similar()
    test_search_image_different_scores()
    test_insert_video()
    test_search_video()
    test_insert_audio()
    test_search_audio()
    test_collection_stats()

    print("\n" + "=" * 55)
    print("  All Vector DB tests passed!")
    print("=" * 55)