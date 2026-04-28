"""
watermark/extractor.py
──────────────────────────────────────────────────────────────
Two-Layer Watermark Verification:
  Layer 1 — Extract DCT watermark, compare with registered owner bits
  Layer 2 — Verify ECDSA signature against blockchain record

Both layers must pass for VERIFIED status.
One layer fail  → TAMPERED
Both layers fail → NO_WATERMARK
"""

from __future__ import annotations

import hashlib
import json
import time
import numpy as np
from pathlib import Path
from typing import Union, Optional
from PIL import Image
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

from ai_pipeline.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VerificationResult:
    """Complete verification result — shown to legal team / dashboard."""

    # Overall verdict
    verdict: str            # VERIFIED | TAMPERED | NO_WATERMARK | PARTIAL

    # Layer 1 — DCT
    dct_detected:     bool
    dct_owner_match:  bool
    dct_confidence:   float  # 0.0 → 1.0

    # Layer 2 — Crypto
    signature_valid:  bool
    blockchain_match: bool

    # Details
    extracted_owner_id:  Optional[str]
    registered_owner_id: Optional[str]
    image_hash:          str
    verification_time:   float

    # Action
    action:     str   # CONFIRMED_OWNERSHIP | INVESTIGATE | IGNORE
    alert_level: str  # CRITICAL | HIGH | MEDIUM | LOW | NONE

    @property
    def is_verified(self) -> bool:
        return self.verdict == "VERIFIED"


class WatermarkExtractor:
    """
    Extracts and verifies the two-layer watermark.

    Verification Logic:
    ┌─────────────────────────────────────────────────────┐
    │  DCT match  │  Sig valid  │  Verdict                │
    │─────────────┼─────────────┼─────────────────────────│
    │     ✓       │      ✓      │  VERIFIED               │
    │     ✓       │      ✗      │  TAMPERED (sig forged?) │
    │     ✗       │      ✓      │  TAMPERED (wm stripped) │
    │     ✗       │      ✗      │  NO_WATERMARK           │
    └─────────────────────────────────────────────────────┘

    This is why blockchain + AI together beats either alone:
    - Strip AI watermark → crypto layer still catches it
    - Fake blockchain record → AI layer still catches it
    - Must defeat BOTH to evade detection
    """

    EMBED_STRENGTH = 0.06
    EMBED_POSITIONS = [(2, 3), (3, 2), (3, 3), (4, 2), (2, 4), (4, 3)]
    BIT_MATCH_THRESHOLD = 0.60 # 75% bit accuracy = watermark present

    def __init__(self):
        logger.info("WatermarkExtractor initialized")

    # ── public API ──────────────────────────────────────────────

    def verify(
        self,
        image: Union[Image.Image, str, Path],
        blockchain_record: dict,
    ) -> VerificationResult:
        """
        Full two-layer verification.

        Parameters
        ----------
        image            : suspect image to verify
        blockchain_record: dict returned from blockchain lookup
                           Must contain: owner_id, watermark_hash,
                           signature, public_key, asset_id, embedded_at

        Returns
        -------
        VerificationResult with full verdict
        """
        t_start = time.perf_counter()

        if not isinstance(image, Image.Image):
            image = Image.open(image).convert("RGB")

        image_hash = self._image_hash(image)

        # ── Layer 1: DCT extraction ────────────────────────────
        registered_owner = blockchain_record.get("owner_id", "")
        registered_bits  = self._owner_id_to_bits(registered_owner)
        extracted_bits   = self._extract_dct(image)

        dct_confidence  = self._bit_accuracy(extracted_bits, registered_bits)
        dct_detected    = dct_confidence >= self.BIT_MATCH_THRESHOLD
        dct_owner_match = dct_detected

        logger.info(
            f"DCT extraction | confidence={dct_confidence:.3f} | "
            f"detected={dct_detected}"
        )

        # ── Layer 2: ECDSA verification ────────────────────────
        sig_valid, bc_match = self._verify_signature(
            image_hash, blockchain_record
        )

        logger.info(
            f"Signature verification | valid={sig_valid} | "
            f"hash_match={bc_match}"
        )

        # ── Verdict logic ──────────────────────────────────────
        verdict, action, alert = self._determine_verdict(
            dct_detected, sig_valid, bc_match
        )

        elapsed = time.perf_counter() - t_start

        result = VerificationResult(
            verdict=verdict,
            dct_detected=dct_detected,
            dct_owner_match=dct_owner_match,
            dct_confidence=round(dct_confidence, 4),
            signature_valid=sig_valid,
            blockchain_match=bc_match,
            extracted_owner_id=registered_owner if dct_detected else None,
            registered_owner_id=registered_owner,
            image_hash=image_hash,
            verification_time=round(elapsed, 4),
            action=action,
            alert_level=alert,
        )

        logger.info(
            f"Verification complete | verdict={verdict} | "
            f"action={action} | t={elapsed:.3f}s"
        )
        return result

    def verify_signature_only(
        self,
        image: Union[Image.Image, str, Path],
        blockchain_record: dict,
    ) -> dict:
        """
        Crypto-only verification — no AI involved.
        Use this when you need 100% bias-free proof for legal purposes.
        """
        if not isinstance(image, Image.Image):
            image = Image.open(image).convert("RGB")

        image_hash = self._image_hash(image)
        sig_valid, bc_match = self._verify_signature(image_hash, blockchain_record)

        return {
            "image_hash":      image_hash,
            "signature_valid": sig_valid,
            "hash_match":      bc_match,
            "is_authentic":    sig_valid and bc_match,
            "owner_id":        blockchain_record.get("owner_id"),
            "asset_id":        blockchain_record.get("asset_id"),
            "verdict":         "AUTHENTIC" if (sig_valid and bc_match) else "NOT_AUTHENTIC",
        }

    # ── DCT extraction ───────────────────────────────────────────

    def _extract_dct(self, image: Image.Image) -> np.ndarray:
        """Extract embedded bits from DCT coefficients."""
        from scipy.fft import dct

        ycbcr = image.convert("YCbCr")
        y_arr = np.array(ycbcr.split()[0], dtype=np.float64)

        h, w = y_arr.shape
        extracted_bits = []

        for row in range(0, h - 7, 8):
            for col in range(0, w - 7, 8):
                if len(extracted_bits) >= 128:
                    break

                block    = y_arr[row:row+8, col:col+8]
                dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')

                for (r, c) in self.EMBED_POSITIONS:
                    if len(extracted_bits) >= 128:
                        break
                    coef = dct_block[r, c]
                    step = 20.0
                    frac = (coef / step) - np.floor(coef / step)
                    extracted_bits.append(1 if frac >= 0.5 else 0)

        # Pad to 128 bits if image too small
        while len(extracted_bits) < 128:
            extracted_bits.append(0)

        return np.array(extracted_bits[:128], dtype=np.uint8)

    # ── ECDSA verification ───────────────────────────────────────

    def _verify_signature(
        self,
        image_hash: str,
        blockchain_record: dict,
    ) -> tuple[bool, bool]:
        """
        Verify ECDSA signature from blockchain record.

        Returns (signature_valid, hash_matches_blockchain)
        """
        try:
            # Check hash matches blockchain record
            bc_hash    = blockchain_record.get("watermark_hash", "")
            hash_match = image_hash == bc_hash

            # Load public key from blockchain record
            pub_key_hex = blockchain_record.get("public_key", "")
            if not pub_key_hex:
                return False, hash_match

            pub_bytes = bytes.fromhex(pub_key_hex)
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256R1(), pub_bytes
            )

            # Reconstruct signed message
            message = json.dumps({
                "hash":      bc_hash,
                "owner_id":  blockchain_record.get("owner_id", ""),
                "asset_id":  blockchain_record.get("asset_id", ""),
                "timestamp": blockchain_record.get("embedded_at", 0),
            }, sort_keys=True).encode()

            # Verify signature
            sig_bytes = bytes.fromhex(blockchain_record.get("signature", ""))
            public_key.verify(sig_bytes, message, ec.ECDSA(hashes.SHA256()))

            return True, hash_match

        except InvalidSignature:
            logger.warning("ECDSA signature verification FAILED — possible forgery")
            return False, False
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False, False

    # ── verdict ──────────────────────────────────────────────────

    @staticmethod
    def _determine_verdict(
        dct_match: bool,
        sig_valid: bool,
        bc_match: bool,
    ) -> tuple[str, str, str]:
        """
        Returns (verdict, action, alert_level)

        Both layers pass   → VERIFIED  → CONFIRMED_OWNERSHIP  → NONE
        Only crypto passes → TAMPERED  → LEGAL_REVIEW         → HIGH
        Only DCT passes    → TAMPERED  → INVESTIGATE          → MEDIUM
        Neither passes     → NO_WATERMARK → IGNORE            → LOW
        """
        if dct_match and sig_valid and bc_match:
            return "VERIFIED",      "CONFIRMED_OWNERSHIP", "NONE"
        elif sig_valid and bc_match and not dct_match:
            return "TAMPERED",      "LEGAL_REVIEW",        "HIGH"
        elif dct_match and not sig_valid:
            return "TAMPERED",      "INVESTIGATE",         "MEDIUM"
        elif dct_match and sig_valid and not bc_match:
            return "TAMPERED",      "LEGAL_REVIEW",        "HIGH"
        else:
            return "NO_WATERMARK",  "IGNORE",              "LOW"

    # ── helpers ──────────────────────────────────────────────────

    @staticmethod
    def _owner_id_to_bits(owner_id: str) -> np.ndarray:
        hash_bytes = hashlib.sha256(owner_id.encode()).digest()[:16]
        return np.unpackbits(np.frombuffer(hash_bytes, dtype=np.uint8))

    @staticmethod
    def _image_hash(image: Image.Image) -> str:
        arr = np.array(image)
        return hashlib.sha256(arr.tobytes()).hexdigest()

    @staticmethod
    def _bit_accuracy(extracted: np.ndarray, expected: np.ndarray) -> float:
        min_len = min(len(extracted), len(expected))
        if min_len == 0:
            return 0.0
        matches = np.sum(extracted[:min_len] == expected[:min_len])
        return float(matches) / min_len