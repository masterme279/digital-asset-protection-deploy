import cv2
import ffmpeg
import numpy as np
from pathlib import Path
from typing import Union
from PIL import Image

from ai_pipeline.utils.config import config
from ai_pipeline.utils.logger import get_logger
from ai_pipeline.utils.helpers import timeit

logger = get_logger(__name__)


class FrameExtractor:
    """
    Extracts frames from video using two strategies:
    1. Uniform sampling  — every N seconds (fast, good for long videos)
    2. Scene-change      — only on scene cuts (smart, catches key moments)
    """

    def __init__(self):
        self.max_frames = config.pipeline.max_frames_per_video
        self.target_size = config.pipeline.image_size

    @timeit
    def extract_uniform(self, video_path: Union[str, Path],
                         fps: float = 1.0) -> list[dict]:
        """
        Extract 1 frame per second (default).
        Returns list of {frame_idx, timestamp_sec, image}.
        """
        video_path = str(video_path)
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        video_fps    = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / video_fps if video_fps > 0 else 0
        interval     = max(1, int(video_fps / fps))

        logger.info(
            f"Video: {Path(video_path).name} | "
            f"FPS: {video_fps:.1f} | Duration: {duration_sec:.1f}s | "
            f"Extracting every {interval} frames"
        )

        frames = []
        frame_idx = 0

        while len(frames) < self.max_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            pil_image = self._cv2_to_pil(frame)
            frames.append({
                "frame_idx":     frame_idx,
                "timestamp_sec": round(frame_idx / video_fps, 3),
                "image":         pil_image,
            })
            frame_idx += interval

        cap.release()
        logger.info(f"Extracted {len(frames)} uniform frames")
        return frames

    @timeit
    def extract_scene_changes(self, video_path: Union[str, Path],
                               threshold: float = 30.0) -> list[dict]:
        """
        Extract frames only at scene changes using histogram difference.
        Much more efficient — captures only meaningful content transitions.
        threshold: pixel difference sensitivity (lower = more sensitive)
        """
        video_path = str(video_path)
        cap        = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        video_fps = cap.get(cv2.CAP_PROP_FPS)
        frames    = []
        prev_hist = None
        frame_idx = 0

        while len(frames) < self.max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            # Compute grayscale histogram for scene change detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()

            if prev_hist is not None:
                diff = cv2.compareHist(prev_hist,
                                       hist,
                                       cv2.HISTCMP_CHISQR)
                if diff > threshold:
                    pil_image = self._cv2_to_pil(frame)
                    frames.append({
                        "frame_idx":     frame_idx,
                        "timestamp_sec": round(frame_idx / video_fps, 3),
                        "image":         pil_image,
                        "scene_diff":    round(float(diff), 2),
                    })
                    logger.debug(
                        f"Scene change at frame {frame_idx} "
                        f"({frame_idx/video_fps:.1f}s) diff={diff:.1f}"
                    )

            prev_hist  = hist
            frame_idx += 1

        cap.release()
        logger.info(f"Extracted {len(frames)} scene-change frames")
        return frames

    def extract_keyframes(self, video_path: Union[str, Path]) -> list[dict]:
        """
        Smart extraction: scene changes first, fallback to uniform
        if too few scene changes detected.
        """
        scene_frames = self.extract_scene_changes(video_path)

        if len(scene_frames) < 5:
            logger.info(
                f"Only {len(scene_frames)} scene frames found — "
                f"falling back to uniform sampling"
            )
            return self.extract_uniform(video_path, fps=0.5)

        return scene_frames

    def get_video_metadata(self, video_path: Union[str, Path]) -> dict:
        """Extract video metadata using ffprobe."""
        try:
            probe = ffmpeg.probe(str(video_path))
            video_stream = next(
                (s for s in probe["streams"] if s["codec_type"] == "video"),
                None
            )
            audio_stream = next(
                (s for s in probe["streams"] if s["codec_type"] == "audio"),
                None
            )
            return {
                "duration_sec":  float(probe["format"].get("duration", 0)),
                "size_bytes":    int(probe["format"].get("size", 0)),
                "format":        probe["format"].get("format_name", "unknown"),
                "video_codec":   video_stream.get("codec_name") if video_stream else None,
                "width":         video_stream.get("width")       if video_stream else None,
                "height":        video_stream.get("height")      if video_stream else None,
                "fps":           eval(video_stream.get("r_frame_rate", "0/1")) if video_stream else None,
                "audio_codec":   audio_stream.get("codec_name")  if audio_stream else None,
                "audio_sample_rate": audio_stream.get("sample_rate") if audio_stream else None,
            }
        except Exception as e:
            logger.error(f"Failed to get metadata for {video_path}: {e}")
            return {}

    def _cv2_to_pil(self, frame: np.ndarray) -> Image.Image:
        """Convert OpenCV BGR frame to PIL RGB image, resized to target."""
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb).resize(self.target_size)
        return image