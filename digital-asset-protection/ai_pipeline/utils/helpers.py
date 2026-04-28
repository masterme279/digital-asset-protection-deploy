import hashlib
import time
import numpy as np
from pathlib import Path
from functools import wraps
from typing import Union
from PIL import Image
from ai_pipeline.utils.logger import get_logger
from ai_pipeline.utils.media_fetch import ensure_local_media

logger = get_logger(__name__)

def compute_file_hash(file_path: Union[str, Path]) -> str:
    """SHA-256 hash of a file — used as unique asset ID."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """L2-normalize an embedding vector for cosine similarity search."""
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two normalized vectors."""
    return float(np.dot(normalize_embedding(a), normalize_embedding(b)))

def load_image_safe(path: Union[str, Path]) -> Image.Image:
    """Load image and convert to RGB safely."""
    try:
        local = ensure_local_media(path, kind="image").local_path
        img = Image.open(local).convert("RGB")
        return img
    except Exception as e:
        logger.error(f"Failed to load image {path}: {e}")
        raise

def timeit(func):
    """Decorator to log function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__name__} completed in {elapsed:.3f}s")
        return result
    return wrapper

def chunk_list(lst: list, size: int) -> list:
    """Split list into chunks of given size for batch processing."""
    return [lst[i:i + size] for i in range(0, len(lst), size)]