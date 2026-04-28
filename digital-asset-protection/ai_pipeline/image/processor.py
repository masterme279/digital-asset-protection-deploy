import torch
import numpy as np
import open_clip
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
from typing import Union
from pathlib import Path

from ai_pipeline.utils.config import config
from ai_pipeline.utils.logger import get_logger
from ai_pipeline.utils.helpers import normalize_embedding, load_image_safe, timeit

logger = get_logger(__name__)


class ImageProcessor:
    """
    Dual-embedding fingerprinter using CLIP + DINOv2.
    CLIP   → semantic understanding (what the image means)
    DINOv2 → fine-grained visual features (pixel-level similarity)
    Combined → catches re-encoded, cropped, and edited copies.
    """

    def __init__(self):
        self.device = config.model.device
        logger.info(f"Loading image models on device: {self.device}")
        self._load_clip()
        self._load_dinov2()
        logger.info("Image models loaded successfully")

    def _load_clip(self):
        self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="openai", force_quick_gelu=True
        )
        self.clip_model = self.clip_model.to(self.device)
        self.clip_model.eval()
        logger.debug("CLIP ViT-B/32 loaded")

    def _load_dinov2(self):
        self.dino_processor = AutoImageProcessor.from_pretrained(config.model.dinov2_model)
        self.dino_model = AutoModel.from_pretrained(config.model.dinov2_model)
        self.dino_model = self.dino_model.to(self.device)
        self.dino_model.eval()
        logger.debug("DINOv2 loaded")

    @timeit
    def get_clip_embedding(self, image: Image.Image) -> np.ndarray:
        """Extract CLIP semantic embedding — 512-dim vector."""
        tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            embedding = self.clip_model.encode_image(tensor)
        return normalize_embedding(embedding.cpu().numpy().flatten())

    @timeit
    def get_dinov2_embedding(self, image: Image.Image) -> np.ndarray:
        """Extract DINOv2 fine-grained embedding — 768-dim vector."""
        inputs = self.dino_processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.dino_model(**inputs)
        embedding = outputs.last_hidden_state[:, 0, :]
        return normalize_embedding(embedding.cpu().numpy().flatten())

    @timeit
    def get_combined_fingerprint(self, image: Union[Image.Image, str, Path]) -> dict:
        """
        Full fingerprint: both embeddings + metadata.
        This is what gets stored in Milvus.
        """
        if not isinstance(image, Image.Image):
            image = load_image_safe(image)

        clip_emb = self.get_clip_embedding(image)
        dino_emb = self.get_dinov2_embedding(image)

        return {
            "clip_embedding":      clip_emb,
            "dinov2_embedding":    dino_emb,
            "image_size":          image.size,
            "embedding_dim_clip":  len(clip_emb),
            "embedding_dim_dino":  len(dino_emb),
        }

    def batch_fingerprint(self, image_paths: list) -> list:
        """Process multiple images — returns list of fingerprints."""
        results = []
        for i, path in enumerate(image_paths):
            try:
                fp = self.get_combined_fingerprint(path)
                fp["source_path"] = str(path)
                results.append(fp)
                logger.info(f"Fingerprinted {i+1}/{len(image_paths)}: {path}")
            except Exception as e:
                logger.error(f"Failed on {path}: {e}")
                results.append({"source_path": str(path), "error": str(e)})
        return results