"""
watermark/embedder.py
──────────────────────────────────────────────────────────────
Two-Layer Watermark System:
  Layer 1 — DCT-domain invisible watermark (survives compression/crop/re-encode)
  Layer 2 — ECDSA cryptographic signature  (blockchain-verifiable, bias-free)

Why hybrid?
  AI-only watermarks → model bias, adversarial removal, unavailability
  Crypto-only marks  → no perceptual embedding, easily cropped out
  Combined           → both must agree for verification to pass
"""

from __future__ import annotations

import hashlib
import json
import time
import numpy as np
from pathlib import Path
from typing import Union
from PIL import Image

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature, encode_dss_signature
)
from cryptography.hazmat.backends import default_backend

from ai_pipeline.utils.logger import get_logger
from ai_pipeline.utils.helpers import compute_file_hash

logger = get_logger(__name__)


class WatermarkEmbedder:
    """
    Embeds a two-layer watermark into an image.

    Layer 1 — DCT Watermark (perceptual, survives attacks):
        - Converts image to YCbCr, works on Y (luma) channel
        - Splits into 8x8 DCT blocks (same as JPEG)
        - Embeds owner ID bits into mid-frequency DCT coefficients
        - Survives: JPEG compression, mild crop, color shift, re-encode

    Layer 2 — ECDSA Signature (cryptographic, blockchain-anchored):
        - SHA-256 hash of watermarked image
        - Signed with owner's ECDSA private key (P-256 curve)
        - Signature + metadata stored on Hyperledger Fabric
        - Root hash anchored to Polygon daily
        - Cannot be faked without owner's private key

    Verification requires BOTH layers to pass.
    """

    # DCT embedding strength — higher = more robust but more visible
    # 0.025 is invisible to human eye, survives JPEG quality >= 70
    EMBED_STRENGTH = 0.06

    # Mid-frequency DCT positions to embed bits (avoid DC and high-freq)
    # These survive JPEG compression better than high-frequency coefficients
    EMBED_POSITIONS = [(2, 3), (3, 2), (3, 3), (4, 2), (2, 4), (4, 3)]

    def __init__(self, private_key: ec.EllipticCurvePrivateKey = None):
        """
        Parameters
        ----------
        private_key : ECDSA P-256 private key for signing.
                      If None, generates a new key pair (for testing).
        """
        if private_key is None:
            self._private_key = ec.generate_private_key(
                ec.SECP256R1(), default_backend()
            )
            logger.warning(
                "No private key provided — generated ephemeral key. "
                "In production, load a persistent key from secure storage."
            )
        else:
            self._private_key = private_key

        self._public_key = self._private_key.public_key()
        logger.info("WatermarkEmbedder initialized | curve=P-256")

    # ── public API ──────────────────────────────────────────────

    def embed(
        self,
        image: Union[Image.Image, str, Path],
        owner_id: str,
        asset_id: str,
        timestamp: float = None,
    ) -> dict:
        """
        Full two-layer watermark embedding pipeline.

        Returns
        -------
        dict with keys:
            watermarked_image  : PIL.Image — embed this, store this
            signature_payload  : dict      — send this to blockchain
            watermark_hash     : str       — SHA-256 of watermarked image
            owner_id           : str
            asset_id           : str
            embedded_at        : float
        """
        if not isinstance(image, Image.Image):
            image = Image.open(image).convert("RGB")

        timestamp = timestamp or time.time()

        # ── Layer 1: DCT watermark ─────────────────────────────
        owner_bits = self._owner_id_to_bits(owner_id)
        watermarked = self._embed_dct(image, owner_bits)
        logger.info(f"DCT watermark embedded | owner={owner_id} | asset={asset_id}")

        # ── Layer 2: ECDSA signature ───────────────────────────
        watermark_hash = self._image_hash(watermarked)
        signature_bytes = self._sign(watermark_hash, owner_id, asset_id, timestamp)
        signature_hex   = signature_bytes.hex()

        # Payload for blockchain registration
        signature_payload = {
            "asset_id":       asset_id,
            "owner_id":       owner_id,
            "watermark_hash": watermark_hash,
            "signature":      signature_hex,
            "public_key":     self._public_key_hex(),
            "algorithm":      "ECDSA-P256-SHA256",
            "embedded_at":    timestamp,
            "version":        "1.0",
            # What this image should survive
            "robustness": [
                "jpeg_compression",
                "crop_resize",
                "color_adjustment",
                "re_encoding"
            ],
        }

        logger.info(
            f"ECDSA signature generated | "
            f"hash={watermark_hash[:16]}... | "
            f"sig={signature_hex[:16]}..."
        )

        return {
            "watermarked_image":  watermarked,
            "signature_payload":  signature_payload,
            "watermark_hash":     watermark_hash,
            "owner_id":           owner_id,
            "asset_id":           asset_id,
            "embedded_at":        timestamp,
        }

    def generate_key_pair(self) -> dict:
        """
        Generate a new ECDSA P-256 key pair.
        Private key → secure storage (HSM / vault)
        Public key  → blockchain registration
        """
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key  = private_key.public_key()

        private_pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()

        public_pem = public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        return {
            "private_key_pem": private_pem,   # NEVER store on blockchain
            "public_key_pem":  public_pem,    # register on blockchain
            "algorithm":       "ECDSA-P256",
        }

    def save_watermarked(
        self,
        result: dict,
        output_path: Union[str, Path],
        quality: int = 95,
    ) -> Path:
        """Save watermarked image. Quality >= 85 preserves DCT watermark."""
        output_path = Path(output_path)
        result["watermarked_image"].save(str(output_path), quality=quality)
        logger.info(f"Watermarked image saved: {output_path}")
        return output_path

    # ── DCT embedding ────────────────────────────────────────────

    def _embed_dct(self, image: Image.Image, bits: np.ndarray) -> Image.Image:
        """
        Embed bits into mid-frequency DCT coefficients of 8x8 blocks.
        Works on Y (luma) channel of YCbCr — least visible to human eye.
        """
        from scipy.fft import dct, idct

        # Convert to YCbCr — embed in Y channel only
        ycbcr = image.convert("YCbCr")
        y, cb, cr = ycbcr.split()
        y_arr = np.array(y, dtype=np.float64)

        h, w = y_arr.shape
        bit_idx = 0
        n_bits = len(bits)

        # Process 8x8 blocks
        for row in range(0, h - 7, 8):
            for col in range(0, w - 7, 8):
                if bit_idx >= n_bits:
                    break

                block = y_arr[row:row+8, col:col+8]

                # 2D DCT
                dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')

                # Embed one bit per position
                for (r, c) in self.EMBED_POSITIONS:
                    if bit_idx >= n_bits:
                        break
                    coef = dct_block[r, c]
                    # Fixed absolute step — survives JPEG quantization
                    # JPEG quantization step for mid-freq is ~8-16 at quality=85
                    # Our step=20 is larger, so our signal survives
                    step = 20.0
                    if bits[bit_idx] == 1:
                        dct_block[r, c] = step * (np.floor(coef / step) + 0.75)
                    else:
                        dct_block[r, c] = step * (np.floor(coef / step) + 0.25)
                    bit_idx += 1

                # Inverse 2D DCT
                y_arr[row:row+8, col:col+8] = idct(
                    idct(dct_block.T, norm='ortho').T, norm='ortho'
                )

        # Clip and reconstruct
        y_embedded = Image.fromarray(np.clip(y_arr, 0, 255).astype(np.uint8))
        result = Image.merge("YCbCr", (y_embedded, cb, cr))
        return result.convert("RGB")

    # ── ECDSA signing ────────────────────────────────────────────

    def _sign(
        self,
        image_hash: str,
        owner_id: str,
        asset_id: str,
        timestamp: float,
    ) -> bytes:
        """Sign the image hash + metadata with ECDSA P-256."""
        # Build deterministic message — same inputs always produce same hash
        message = json.dumps({
            "hash":      image_hash,
            "owner_id":  owner_id,
            "asset_id":  asset_id,
            "timestamp": timestamp,
        }, sort_keys=True).encode()

        signature = self._private_key.sign(message, ec.ECDSA(hashes.SHA256()))
        return signature

    # ── helpers ──────────────────────────────────────────────────

    @staticmethod
    def _owner_id_to_bits(owner_id: str) -> np.ndarray:
        """Convert owner ID string to binary array via SHA-256."""
        hash_bytes = hashlib.sha256(owner_id.encode()).digest()[:16]  # 128 bits
        bits = np.unpackbits(np.frombuffer(hash_bytes, dtype=np.uint8))
        return bits  # 128 bits

    @staticmethod
    def _image_hash(image: Image.Image) -> str:
        """SHA-256 of raw image bytes."""
        arr = np.array(image)
        return hashlib.sha256(arr.tobytes()).hexdigest()

    def _public_key_hex(self) -> str:
        """Compressed public key as hex — store on blockchain."""
        pub_bytes = self._public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.CompressedPoint,
        )
        return pub_bytes.hex()