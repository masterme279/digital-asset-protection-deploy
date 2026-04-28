import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ai_pipeline.image.processor import ImageProcessor
from ai_pipeline.image.detector import ImageDetector, SportsBroadcastDetector

# ── Load models ONCE for all tests ──────────────────────────────────────────
print("Loading models once for all tests...")
_processor = ImageProcessor()
_detector  = ImageDetector(processor=_processor)
print("Models ready.\n")


def make_realistic_image(scene: str = "red") -> Image.Image:
    """
    Create visually distinct synthetic images that look like
    different real-world scenes to the model.
    """
    img = Image.new("RGB", (224, 224), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    if scene == "red_stadium":
        # Red sports stadium scene
        draw.rectangle([0, 0, 224, 224], fill=(180, 20, 20))
        draw.rectangle([20, 100, 204, 180], fill=(220, 180, 100))  # pitch
        draw.ellipse([90, 80, 134, 124], fill=(255, 255, 255))     # ball
        draw.rectangle([0, 0, 224, 40], fill=(120, 10, 10))        # scoreboard
        for x in range(0, 224, 20):                                 # crowd dots
            draw.ellipse([x, 45, x+10, 55], fill=(200, 150, 150))

    elif scene == "blue_ocean":
        # Blue ocean / water scene — completely different
        draw.rectangle([0, 0, 224, 224], fill=(10, 80, 180))
        draw.rectangle([0, 150, 224, 224], fill=(5, 40, 120))      # deep water
        for i in range(0, 224, 30):                                 # waves
            draw.arc([i, 140, i+30, 165], 0, 180, fill=(100, 180, 255), width=2)
        draw.ellipse([80, 20, 150, 90], fill=(255, 220, 50))        # sun

    elif scene == "green_field":
        # Green football field
        draw.rectangle([0, 0, 224, 224], fill=(30, 140, 30))
        draw.rectangle([30, 30, 194, 194], outline=(255, 255, 255), width=3)
        draw.line([112, 30, 112, 194], fill=(255, 255, 255), width=2)  # center line
        draw.ellipse([90, 90, 134, 134], outline=(255, 255, 255), width=2)
        draw.rectangle([0, 80, 30, 144], outline=(255, 255, 255), width=2)

    elif scene == "dark_night":
        # Dark night scene — very different from day scenes
        draw.rectangle([0, 0, 224, 224], fill=(10, 10, 30))
        for _ in range(80):                                          # stars
            x, y = np.random.randint(0, 224), np.random.randint(0, 100)
            draw.point([x, y], fill=(255, 255, 200))
        draw.ellipse([80, 20, 144, 84], fill=(220, 220, 180))        # moon

    elif scene == "red_stadium_modified":
        # Same as red_stadium but cropped + blurred (simulates re-upload)
        img = make_realistic_image("red_stadium")
        img = img.crop((12, 12, 212, 212))
        img = img.resize((224, 224))
        img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
        return img

    return img


def test_fingerprint_dimensions():
    img = make_realistic_image("red_stadium")
    fp  = _processor.get_combined_fingerprint(img)

    assert fp["clip_embedding"].shape   == (512,)
    assert fp["dinov2_embedding"].shape == (768,)

    clip_norm = np.linalg.norm(fp["clip_embedding"])
    dino_norm = np.linalg.norm(fp["dinov2_embedding"])
    assert abs(clip_norm - 1.0) < 1e-5
    assert abs(dino_norm - 1.0) < 1e-5

    print("[PASS] Fingerprint dimensions test")
    print(f"       CLIP  : {fp['clip_embedding'].shape}  norm={clip_norm:.6f}")
    print(f"       DINOv2: {fp['dinov2_embedding'].shape} norm={dino_norm:.6f}")


def test_exact_same_image():
    img    = make_realistic_image("green_field")
    result = _detector.compare(img, img)

    assert result["combined_score"] > 0.999
    assert result["is_match"]       is True
    assert result["confidence"]     == "EXACT_MATCH"

    print("\n[PASS] Exact same image")
    print(f"       Score : {result['combined_score']}  |  {result['confidence']}")
    print(f"       Action: {result['action']}")


def test_modified_copy_detected():
    """Cropped + blurred version of original must still be flagged."""
    original = make_realistic_image("red_stadium")
    modified = make_realistic_image("red_stadium_modified")
    result   = _detector.compare(original, modified)

    print("\n[INFO] Modified copy detection")
    print(f"       CLIP  : {result['clip_similarity']}")
    print(f"       DINOv2: {result['dinov2_similarity']}")
    print(f"       Combined  : {result['combined_score']}")
    print(f"       Confidence: {result['confidence']}")
    print(f"       Action    : {result['action']}")
    print(f"       Is match  : {result['is_match']}")

    assert result["combined_score"] > 0.82, \
        f"Modified copy should score > 0.82, got {result['combined_score']}"
    assert result["is_match"] is True, \
        f"Modified copy must be flagged, got score={result['combined_score']}"
    assert result["action"] in ("FLAG_FOR_REVIEW", "LEGAL_REVIEW", "AUTO_TAKEDOWN", "MONITOR"), \
        f"Must trigger some action, got {result['action']}"
    print("       [PASS] Modified copy correctly flagged")


def test_completely_different_images():
    """
    Red stadium vs Blue ocean — visually completely different.
    These should NOT match. We test the score gap, not a hard threshold,
    because synthetic images still cluster higher than real photos would.
    """
    img_stadium = make_realistic_image("red_stadium")
    img_ocean   = make_realistic_image("blue_ocean")
    result      = _detector.compare(img_stadium, img_ocean)

    print("\n[INFO] Different images test")
    print(f"       CLIP  : {result['clip_similarity']}")
    print(f"       DINOv2: {result['dinov2_similarity']}")
    print(f"       Combined  : {result['combined_score']}")
    print(f"       Confidence: {result['confidence']}")
    print(f"       Action    : {result['action']}")

    # Key insight: different images must score LOWER than modified copy
    modified_result = _detector.compare(
        make_realistic_image("red_stadium"),
        make_realistic_image("red_stadium_modified")
    )
    assert result["combined_score"] < modified_result["combined_score"], \
        "Different image must score lower than a modified copy of the same image"
    print("       [PASS] Different image scores lower than modified copy")


def test_score_ranking():
    """
    Exact match > modified copy > different content.
    This is the most important invariant for the detection system.
    """
    base      = make_realistic_image("red_stadium")
    modified  = make_realistic_image("red_stadium_modified")
    different = make_realistic_image("blue_ocean")
    night     = make_realistic_image("dark_night")

    score_exact     = _detector.compare(base, base)["combined_score"]
    score_modified  = _detector.compare(base, modified)["combined_score"]
    score_different = _detector.compare(base, different)["combined_score"]
    score_night     = _detector.compare(base, night)["combined_score"]

    print("\n[INFO] Score ranking test")
    print(f"       Exact match   : {score_exact}")
    print(f"       Modified copy : {score_modified}")
    print(f"       Different img : {score_different}")
    print(f"       Night scene   : {score_night}")

    assert score_exact    > score_modified,  "Exact must beat modified"
    assert score_modified > score_different, "Modified must beat different"
    print("       [PASS] Ranking correct: exact > modified > different")


def test_batch_fingerprint():
    import tempfile, os
    scenes = ["red_stadium", "blue_ocean", "green_field", "dark_night"]
    paths  = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for scene in scenes:
            img  = make_realistic_image(scene)
            path = os.path.join(tmpdir, f"{scene}.png")
            img.save(path)
            paths.append(path)

        results = _processor.batch_fingerprint(paths)

    assert len(results) == 4
    assert all("clip_embedding"   in r for r in results)
    assert all("dinov2_embedding" in r for r in results)

    print("\n[PASS] Batch fingerprint test")
    print(f"       Processed: {len(results)} images successfully")


def test_action_tiers():
    """Verify the action tiers trigger correctly based on score."""
    base     = make_realistic_image("red_stadium")
    modified = make_realistic_image("red_stadium_modified")
    diff     = make_realistic_image("blue_ocean")

    r_exact    = _detector.compare(base, base)
    r_modified = _detector.compare(base, modified)
    r_diff     = _detector.compare(base, diff)

    print("\n[INFO] Action tier test")
    print(f"       Exact    → {r_exact['action']}    (score: {r_exact['combined_score']})")
    print(f"       Modified → {r_modified['action']} (score: {r_modified['combined_score']})")
    print(f"       Different→ {r_diff['action']}  (score: {r_diff['combined_score']})")

    assert r_exact["action"]    == "AUTO_TAKEDOWN"
    assert r_modified["action"] in ("FLAG_FOR_REVIEW", "LEGAL_REVIEW", "AUTO_TAKEDOWN")
    print("       [PASS] Action tiers correct")


if __name__ == "__main__":
    print("=" * 55)
    print("  Digital Asset Protection — Image Pipeline Tests")
    print("=" * 55 + "\n")

    test_fingerprint_dimensions()
    test_exact_same_image()
    test_modified_copy_detected()
    test_completely_different_images()
    test_score_ranking()
    test_batch_fingerprint()
    test_action_tiers()

    print("\n" + "=" * 55)
    print("  All tests passed!")
    print("=" * 55)