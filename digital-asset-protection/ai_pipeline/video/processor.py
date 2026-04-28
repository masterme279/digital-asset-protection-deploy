import numpy as np
from pathlib import Path
from typing import Union

from ai_pipeline.video.frame_extractor import FrameExtractor
from ai_pipeline.image.processor import ImageProcessor
from ai_pipeline.utils.config import config
from ai_pipeline.utils.helpers import compute_file_hash, timeit
from ai_pipeline.utils.media_fetch import ensure_local_media
from ai_pipeline.utils.logger import get_logger

logger = get_logger(__name__)


class VideoProcessor:
    """
    Video fingerprinting pipeline.

    Strategy:
    1. Extract keyframes (scene changes or uniform)
    2. Run CLIP + DINOv2 on each frame
    3. Build a temporal fingerprint = ordered sequence of frame embeddings
    4. Also build a summary fingerprint = mean pooled across all frames

    Two videos match if their temporal sequence aligns OR
    their summary embeddings are similar enough.
    """

    def __init__(self,
                 image_processor: ImageProcessor = None,
                 frame_extractor: FrameExtractor = None):
        self.image_processor = image_processor or ImageProcessor()
        self.frame_extractor = frame_extractor or FrameExtractor()

    @timeit
    def fingerprint_video(self, video_path: Union[str, Path]) -> dict:
        """
        Full video fingerprint pipeline.
        Returns temporal + summary embeddings + metadata.
        """
        video_path = ensure_local_media(video_path, kind="video").local_path
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        logger.info(f"Fingerprinting video: {video_path.name}")

        # Step 1: metadata
        metadata = self.frame_extractor.get_video_metadata(video_path)
        file_hash = compute_file_hash(video_path)

        # Step 2: extract keyframes
        frames = self.frame_extractor.extract_keyframes(video_path)
        if not frames:
            raise ValueError(f"No frames extracted from {video_path}")

        logger.info(f"Processing {len(frames)} keyframes...")

        # Step 3: fingerprint each frame
        clip_embeddings  = []
        dino_embeddings  = []
        frame_results    = []

        for i, frame_data in enumerate(frames):
            try:
                fp = self.image_processor.get_combined_fingerprint(
                    frame_data["image"]
                )
                clip_embeddings.append(fp["clip_embedding"])
                dino_embeddings.append(fp["dinov2_embedding"])
                frame_results.append({
                    "frame_idx":     frame_data["frame_idx"],
                    "timestamp_sec": frame_data["timestamp_sec"],
                    "clip_embedding": fp["clip_embedding"],
                    "dino_embedding": fp["dinov2_embedding"],
                })
                logger.debug(f"Frame {i+1}/{len(frames)} fingerprinted")
            except Exception as e:
                logger.error(f"Frame {i} failed: {e}")

        if not clip_embeddings:
            raise ValueError("All frames failed fingerprinting")

        # Step 4: summary embedding = mean pool across all frames
        clip_matrix  = np.stack(clip_embeddings)   # (N, 512)
        dino_matrix  = np.stack(dino_embeddings)   # (N, 768)
        clip_summary = clip_matrix.mean(axis=0)    # (512,)
        dino_summary = dino_matrix.mean(axis=0)    # (768,)

        # Normalize summary embeddings
        clip_summary = clip_summary / np.linalg.norm(clip_summary)
        dino_summary = dino_summary / np.linalg.norm(dino_summary)

        result = {
            "file_hash":         file_hash,
            "source_path":       str(video_path),
            "metadata":          metadata,
            "frame_count":       len(frame_results),
            "frames":            frame_results,
            "clip_summary":      clip_summary,       # use for fast DB lookup
            "dino_summary":      dino_summary,
            "clip_temporal":     clip_matrix,        # use for temporal alignment
            "dino_temporal":     dino_matrix,
            "embedding_dim_clip": clip_summary.shape[0],
            "embedding_dim_dino": dino_summary.shape[0],
        }

        logger.info(
            f"Video fingerprinted: {len(frame_results)} frames | "
            f"CLIP: {clip_summary.shape} | DINOv2: {dino_summary.shape}"
        )
        return result

    def batch_fingerprint(self, video_paths: list) -> list[dict]:
        """Fingerprint multiple videos."""
        results = []
        for i, path in enumerate(video_paths):
            try:
                fp = self.fingerprint_video(path)
                results.append(fp)
                logger.info(f"Done {i+1}/{len(video_paths)}: {path}")
            except Exception as e:
                logger.error(f"Failed {path}: {e}")
                results.append({"source_path": str(path), "error": str(e)})
        return results