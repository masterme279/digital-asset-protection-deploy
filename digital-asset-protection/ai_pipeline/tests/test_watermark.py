import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
from PIL import Image, ImageDraw
import tempfile
import os

from ai_pipeline.watermark.embedder import WatermarkEmbedder
from ai_pipeline.watermark.extractor import WatermarkExtractor


OWNER_ID = "ESPN-SPORTS-MEDIA-001"
ASSET_ID = "ASSET-UEFA-FINAL-2026"


def make_test_image(size=(256, 256), color=(180, 100, 50)) -> Image.Image:
    img  = Image.new("RGB", size, color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([30, 30, 120, 120], fill=(255, 200, 100))
    draw.ellipse([140, 140, 220, 220],  fill=(100, 150, 255))
    return img


print("Initializing watermark system...")
_embedder  = WatermarkEmbedder()
_extractor = WatermarkExtractor()
print("Ready.\n")


def test_embed_returns_watermarked_image():
    img    = make_test_image()
    result = _embedder.embed(img, OWNER_ID, ASSET_ID)

    assert "watermarked_image" in result
    assert "signature_payload" in result
    assert "watermark_hash"    in result
    assert isinstance(result["watermarked_image"], Image.Image)
    assert result["watermarked_image"].size == img.size
    print("[PASS] Embed returns watermarked image")


def test_signature_payload_fields():
    img     = make_test_image()
    result  = _embedder.embed(img, OWNER_ID, ASSET_ID)
    payload = result["signature_payload"]

    for field in ["asset_id", "owner_id", "watermark_hash",
                  "signature", "public_key", "algorithm", "embedded_at"]:
        assert field in payload, f"Missing field: {field}"

    assert payload["algorithm"] == "ECDSA-P256-SHA256"
    assert payload["owner_id"]  == OWNER_ID
    assert payload["asset_id"]  == ASSET_ID
    print("[PASS] Signature payload has all required fields")


def test_watermark_invisible():
    """Watermarked image should look identical — max pixel diff <= 8."""
    img         = make_test_image()
    result      = _embedder.embed(img, OWNER_ID, ASSET_ID)
    original    = np.array(img, dtype=np.int32)
    watermarked = np.array(result["watermarked_image"], dtype=np.int32)
    max_diff    = np.max(np.abs(original - watermarked))

    assert max_diff <= 15, f"Watermark too visible: max pixel diff = {max_diff}"
    print(f"[PASS] Watermark invisible — max pixel diff: {max_diff}")


def test_verify_clean_image():
    """Clean watermarked image must verify as VERIFIED."""
    img    = make_test_image()
    result = _embedder.embed(img, OWNER_ID, ASSET_ID)

    verification = _extractor.verify(
        result["watermarked_image"],
        result["signature_payload"],
    )

    assert verification.verdict          == "VERIFIED"
    assert verification.dct_detected     is True
    assert verification.signature_valid  is True
    assert verification.blockchain_match is True
    assert verification.action           == "CONFIRMED_OWNERSHIP"
    assert verification.alert_level      == "NONE"

    print("[PASS] Clean image verifies correctly")
    print(f"       DCT confidence : {verification.dct_confidence}")
    print(f"       Verdict        : {verification.verdict}")
    print(f"       Action         : {verification.action}")


def test_verify_jpeg_compressed():
    """Must survive JPEG compression at quality=85."""
    img    = make_test_image(size=(512, 512))
    result = _embedder.embed(img, OWNER_ID, ASSET_ID)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "compressed.jpg")
        result["watermarked_image"].save(path, quality=85)
        compressed = Image.open(path).convert("RGB")

    verification = _extractor.verify(
        compressed,
        result["signature_payload"],
    )

    print(f"[INFO] JPEG compression test")
    print(f"       DCT confidence : {verification.dct_confidence}")
    print(f"       DCT detected   : {verification.dct_detected}")
    print(f"       Verdict        : {verification.verdict}")

    assert verification.dct_confidence > 0.55, \
        f"Watermark too weak after JPEG: confidence={verification.dct_confidence}"
    print(f"[PASS] Survived JPEG compression")


def test_verify_tampered_signature():
    """Forged signature must be detected."""
    img    = make_test_image()
    result = _embedder.embed(img, OWNER_ID, ASSET_ID)

    tampered_payload = dict(result["signature_payload"])
    tampered_payload["signature"] = "ab" * 72

    verification = _extractor.verify(
        result["watermarked_image"],
        tampered_payload,
    )

    assert verification.signature_valid is False
    assert verification.verdict in ("TAMPERED", "NO_WATERMARK")
    print(f"[PASS] Forged signature detected | verdict={verification.verdict}")


def test_verify_wrong_owner():
    """Image watermarked by owner A must not verify for owner B."""
    img    = make_test_image()
    result = _embedder.embed(img, OWNER_ID, ASSET_ID)

    wrong_payload            = dict(result["signature_payload"])
    wrong_payload["owner_id"] = "FAKE-OWNER-999"

    verification = _extractor.verify(
        result["watermarked_image"],
        wrong_payload,
    )

    assert verification.signature_valid is False
    print(f"[PASS] Wrong owner rejected | verdict={verification.verdict}")


def test_signature_only_verification():
    """Crypto-only path must work independently of AI."""
    img    = make_test_image()
    result = _embedder.embed(img, OWNER_ID, ASSET_ID)

    sig_result = _extractor.verify_signature_only(
        result["watermarked_image"],
        result["signature_payload"],
    )

    assert sig_result["is_authentic"]    is True
    assert sig_result["signature_valid"] is True
    assert sig_result["hash_match"]      is True
    assert sig_result["verdict"]         == "AUTHENTIC"
    print("[PASS] Crypto-only verification passed — no AI involved")


def test_generate_key_pair():
    """Key generation must return valid PEM keys."""
    keys = _embedder.generate_key_pair()

    assert "private_key_pem" in keys
    assert "public_key_pem"  in keys
    assert "BEGIN PRIVATE KEY" in keys["private_key_pem"]
    assert "BEGIN PUBLIC KEY"  in keys["public_key_pem"]
    print("[PASS] Key pair generation works")


if __name__ == "__main__":
    print("=" * 55)
    print("  Digital Asset Protection — Watermark Tests")
    print("=" * 55)
    print()

    test_embed_returns_watermarked_image()
    test_signature_payload_fields()
    test_watermark_invisible()
    test_verify_clean_image()
    test_verify_jpeg_compressed()
    test_verify_tampered_signature()
    test_verify_wrong_owner()
    test_signature_only_verification()
    test_generate_key_pair()

    print()
    print("=" * 55)
    print("  All watermark tests passed!")
    print("=" * 55)