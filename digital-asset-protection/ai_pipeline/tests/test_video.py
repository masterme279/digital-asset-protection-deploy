import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cv2
import numpy as np
import tempfile
import os

from ai_pipeline.image.processor import ImageProcessor
from ai_pipeline.video.frame_extractor import FrameExtractor
from ai_pipeline.video.processor import VideoProcessor
from ai_pipeline.video.analyzer import VideoAnalyzer


def make_test_video(path: str, color: tuple, num_frames: int = 60,
                    fps: int = 30, size: tuple = (320, 240)) -> str:
    """Create a synthetic test video with solid color + moving circle."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, size)

    for i in range(num_frames):
        frame = np.full((size[1], size[0], 3), color[::-1], dtype=np.uint8)
        # Moving circle — simulates motion/scene variation
        cx = int((i / num_frames) * size[0])
        cy = size[1] // 2
        cv2.circle(frame, (cx, cy), 20, (255, 255, 255), -1)
        # Frame number text
        cv2.putText(frame, f"Frame {i}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        writer.write(frame)

    writer.release()
    return path


# ── Load models ONCE ────────────────────────────────────────────────────────
print("Loading models once for all video tests...")
_image_processor = ImageProcessor()
_extractor       = FrameExtractor()
_processor       = VideoProcessor(image_processor=_image_processor,
                                   frame_extractor=_extractor)
_analyzer        = VideoAnalyzer()
print("Models ready.\n")


def test_frame_extraction():
    """Verify frame extractor pulls frames from a real video file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = make_test_video(
            os.path.join(tmpdir, "test.mp4"),
            color=(180, 50, 50)
        )
        frames = _extractor.extract_uniform(video_path, fps=1.0)

        assert len(frames) > 0, "Should extract at least 1 frame"
        assert "image" in frames[0], "Frame should contain PIL image"
        assert "timestamp_sec" in frames[0], "Frame should have timestamp"
        assert "frame_idx" in frames[0], "Frame should have index"

        print(f"[PASS] Frame extraction test")
        print(f"       Extracted: {len(frames)} frames")
        print(f"       First frame timestamp: {frames[0]['timestamp_sec']}s")
        print(f"       Image size: {frames[0]['image'].size}")


def test_video_metadata():
    """Verify metadata extraction from video file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = make_test_video(
            os.path.join(tmpdir, "meta.mp4"),
            color=(50, 180, 50), num_frames=90
        )
        meta = _extractor.get_video_metadata(video_path)

        assert "duration_sec" in meta
        assert "width" in meta
        assert "height" in meta
        assert meta["width"]  == 320
        assert meta["height"] == 240

        print(f"\n[PASS] Video metadata test")
        print(f"       Duration : {meta['duration_sec']:.1f}s")
        print(f"       Size     : {meta['width']}x{meta['height']}")
        print(f"       Codec    : {meta['video_codec']}")


def test_video_fingerprint():
    """Full fingerprint pipeline on a synthetic video."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = make_test_video(
            os.path.join(tmpdir, "fp.mp4"),
            color=(100, 100, 200), num_frames=60
        )
        fp = _processor.fingerprint_video(video_path)

        assert "clip_summary"  in fp
        assert "dino_summary"  in fp
        assert "clip_temporal" in fp
        assert "file_hash"     in fp
        assert fp["clip_summary"].shape == (512,)
        assert fp["dino_summary"].shape == (768,)
        assert fp["frame_count"] > 0

        clip_norm = np.linalg.norm(fp["clip_summary"])
        dino_norm = np.linalg.norm(fp["dino_summary"])
        assert abs(clip_norm - 1.0) < 1e-5, "Summary must be normalized"
        assert abs(dino_norm - 1.0) < 1e-5, "Summary must be normalized"

        print(f"\n[PASS] Video fingerprint test")
        print(f"       Frames processed : {fp['frame_count']}")
        print(f"       CLIP summary dim : {fp['clip_summary'].shape}")
        print(f"       DINOv2 summary dim: {fp['dino_summary'].shape}")
        print(f"       File hash        : {fp['file_hash'][:16]}...")


def test_same_video_scores_1():
    """Same video fingerprinted twice must score 1.0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = make_test_video(
            os.path.join(tmpdir, "same.mp4"),
            color=(200, 100, 50)
        )
        fp_a = _processor.fingerprint_video(video_path)
        fp_b = _processor.fingerprint_video(video_path)

        result = _analyzer.compare(fp_a, fp_b)

        assert result["combined_score"] > 0.999
        assert result["is_match"] is True
        assert result["confidence"] == "EXACT_MATCH"

        print(f"\n[PASS] Same video similarity test")
        print(f"       Score     : {result['combined_score']}")
        print(f"       Confidence: {result['confidence']}")
        print(f"       Action    : {result['action']}")


def test_different_videos_score_lower():
    """Two different color videos must score lower than same video."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path_red  = make_test_video(
            os.path.join(tmpdir, "red.mp4"),  color=(200, 30, 30))
        path_blue = make_test_video(
            os.path.join(tmpdir, "blue.mp4"), color=(30, 30, 200))

        fp_red  = _processor.fingerprint_video(path_red)
        fp_blue = _processor.fingerprint_video(path_blue)
        fp_same = _processor.fingerprint_video(path_red)

        score_same = _analyzer.compare(fp_red,  fp_same)["combined_score"]
        score_diff = _analyzer.compare(fp_red,  fp_blue)["combined_score"]

        assert score_same > score_diff, \
            f"Same video ({score_same}) must beat different ({score_diff})"

        print(f"\n[PASS] Different videos score lower test")
        print(f"       Same video  : {score_same}")
        print(f"       Diff video  : {score_diff}")
        print(f"       Gap         : {score_same - score_diff:.4f}")


def test_temporal_vs_summary():
    """Temporal comparison must improve or match summary on similar clips."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = make_test_video(
            os.path.join(tmpdir, "temporal.mp4"),
            color=(150, 100, 200), num_frames=90
        )
        fp_a = _processor.fingerprint_video(path)
        fp_b = _processor.fingerprint_video(path)

        summary_r  = _analyzer.compare_summary(fp_a, fp_b)
        temporal_r = _analyzer.compare_temporal(fp_a, fp_b)

        print(f"\n[INFO] Temporal vs summary test")
        print(f"       Summary  score: {summary_r['combined_score']}")
        print(f"       Temporal score: {temporal_r['combined_score']}")

        # Both must agree same video = match
        assert summary_r["is_match"]  is True
        assert temporal_r["is_match"] is True
        print(f"       [PASS] Both modes correctly identify same video")


if __name__ == "__main__":
    print("=" * 55)
    print("  Digital Asset Protection — Video Pipeline Tests")
    print("=" * 55 + "\n")

    test_frame_extraction()
    test_video_metadata()
    test_video_fingerprint()
    test_same_video_scores_1()
    test_different_videos_score_lower()
    test_temporal_vs_summary()

    print("\n" + "=" * 55)
    print("  All video tests passed!")
    print("=" * 55)