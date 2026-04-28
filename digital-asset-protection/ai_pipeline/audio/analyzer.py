"""
audio/analyzer.py
──────────────────────────────────────────────────────────────
Next-Level Stack : Chromaprint (via acoustid)  +  Wav2Vec2
Role             : Dual-path audio fingerprinting & similarity detection
"""

from __future__ import annotations

import hashlib
import logging
import struct
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger("audio.analyzer")

_acoustid = None
_torch = None
_transformers = None


def _load_acoustid():
    global _acoustid
    if _acoustid is None:
        try:
            import acoustid
            _acoustid = acoustid
        except ImportError:
            logger.warning("acoustid not installed — pip install pyacoustid. Using spectrogram hash fallback.")
    return _acoustid


def _load_torch():
    global _torch, _transformers
    if _torch is None:
        import torch
        from transformers import Wav2Vec2Model, Wav2Vec2Processor as W2VProc
        _torch = torch
        _transformers = {"model_cls": Wav2Vec2Model, "proc_cls": W2VProc}
    return _torch, _transformers


# ──────────────────────────────────────────────────────────────
# Result containers
# ──────────────────────────────────────────────────────────────

@dataclass
class FingerprintResult:
    chunk_index: int
    source_path: str
    start_sec: float
    end_sec: float
    fingerprint: List[int]        # list of uint32 values
    fingerprint_hash: str         # SHA-256 hex

    @property
    def num_bits(self) -> int:
        return len(self.fingerprint) * 32


@dataclass
class EmbeddingResult:
    chunk_index: int
    source_path: str
    start_sec: float
    end_sec: float
    embedding: np.ndarray         # shape (1024,) float32
    model_id: str


@dataclass
class ComparisonResult:
    chromaprint_sim: float
    wav2vec_sim: float
    fused_score: float
    is_match: bool
    confidence: str               # "high" | "medium" | "low"
    match_reason: str


@dataclass
class PiracyReport:
    asset_path: str
    asset_hash: str
    suspect_path: str
    chunk_level_results: List[ComparisonResult]
    overall_score: float
    verdict: str                  # "MATCH" | "PARTIAL" | "NO_MATCH"
    matched_chunks: int
    total_chunks: int
    analysis_time_sec: float
    generated_at: float = field(default_factory=time.time)

    @property
    def match_percentage(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return self.matched_chunks / self.total_chunks * 100


# ──────────────────────────────────────────────────────────────
# Core Analyzer
# ──────────────────────────────────────────────────────────────

class AudioAnalyzer:
    """
    Dual-path audio fingerprint + embedding analyzer.

    Parameters
    ----------
    wav2vec_model   : HuggingFace model ID
    device          : "cuda" | "cpu" | "auto"
    fusion_alpha    : Chromaprint weight in fused score  (1-alpha → Wav2Vec2)
    match_threshold : fused score >= this → IS_MATCH
    """

    WAV2VEC_DEFAULT = "facebook/wav2vec2-large-960h"

    def __init__(
        self,
        wav2vec_model: str = WAV2VEC_DEFAULT,
        device: str = "auto",
        fusion_alpha: float = 0.3,
        match_threshold: float = 0.82,
    ) -> None:
        self.wav2vec_model_id = wav2vec_model
        self.fusion_alpha = fusion_alpha
        self.match_threshold = match_threshold
        self._device = self._resolve_device(device)
        self._w2v_model = None
        self._w2v_processor = None

        logger.info(
            "AudioAnalyzer | model=%s | device=%s | α=%.2f | threshold=%.2f",
            wav2vec_model, self._device, fusion_alpha, match_threshold,
        )

    # ── public API ──────────────────────────────────────────────

    def fingerprint(self, chunk, sample_rate: Optional[int] = None) -> FingerprintResult:
        """
        Generate Chromaprint fingerprint for an AudioChunk (or raw numpy array).
        Falls back to Mel-spectrogram hash if acoustid is not installed.
        """
        from .processor import AudioChunk
        if isinstance(chunk, AudioChunk):
            waveform = chunk.waveform
            sr       = chunk.sample_rate
            idx      = chunk.chunk_index
            src      = chunk.source_path
            t0, t1   = chunk.start_sec, chunk.end_sec
        else:
            waveform = chunk
            sr       = sample_rate or 16_000
            idx, src, t0, t1 = 0, "unknown", 0.0, len(waveform) / sr

        acoustid = _load_acoustid()
        if acoustid is None:
            fp_ints = self._chromaprint_via_acoustid(waveform, sr)
        else:
            fp_ints = self._chromaprint_via_acoustid(waveform, sr)

        # Always store as uint32 for consistent hashing
        raw_bytes = np.array(fp_ints, dtype=np.uint32).tobytes()
        # Include chunk identity in the hash so different chunks can be
        # distinguished even when their fingerprints are identical (e.g. periodic audio).
        salt = struct.pack("<Idd", int(idx), float(t0), float(t1))
        fp_hash = hashlib.sha256(raw_bytes + salt).hexdigest()

        return FingerprintResult(
            chunk_index=idx,
            source_path=src,
            start_sec=t0,
            end_sec=t1,
            fingerprint=fp_ints,
            fingerprint_hash=fp_hash,
        )

    def embed(self, chunk) -> EmbeddingResult:
        """Generate Wav2Vec2 mean-pool embedding (1024-dim) for an AudioChunk."""
        from .processor import AudioChunk
        if not isinstance(chunk, AudioChunk):
            raise TypeError("embed() requires an AudioChunk instance.")

        model, processor = self._ensure_model()
        torch = _torch

        with torch.no_grad():
            inputs = processor(
                chunk.waveform,
                sampling_rate=chunk.sample_rate,
                return_tensors="pt",
                padding=True,
            )
            inputs    = {k: v.to(self._device) for k, v in inputs.items()}
            outputs   = model(**inputs)
            hidden    = outputs.last_hidden_state         # (1, T, 1024)
            embedding = hidden.mean(dim=1).squeeze(0)     # (1024,)
            embedding = embedding.cpu().numpy().astype(np.float32)

        return EmbeddingResult(
            chunk_index=chunk.chunk_index,
            source_path=chunk.source_path,
            start_sec=chunk.start_sec,
            end_sec=chunk.end_sec,
            embedding=embedding,
            model_id=self.wav2vec_model_id,
        )

    def compare(
        self,
        fp_a: FingerprintResult,
        emb_a: EmbeddingResult,
        fp_b: FingerprintResult,
        emb_b: EmbeddingResult,
        alpha: Optional[float] = None,
    ) -> ComparisonResult:
        """Fuse Chromaprint + Wav2Vec2 cosine similarity into one score."""
        alpha = alpha if alpha is not None else self.fusion_alpha

        cp_sim  = self._chromaprint_similarity(fp_a.fingerprint, fp_b.fingerprint)
        w2v_sim = self._cosine_similarity(emb_a.embedding, emb_b.embedding)
        fused   = alpha * cp_sim + (1 - alpha) * w2v_sim

        is_match = fused >= self.match_threshold
        confidence, reason = self._interpret(cp_sim, w2v_sim, fused)

        return ComparisonResult(
            chromaprint_sim=round(cp_sim, 4),
            wav2vec_sim=round(w2v_sim, 4),
            fused_score=round(fused, 4),
            is_match=is_match,
            confidence=confidence,
            match_reason=reason,
        )

    def detect_piracy(
        self,
        asset_chunks,
        asset_meta,
        suspect_chunks,
        suspect_meta,
        alpha: Optional[float] = None,
    ) -> PiracyReport:
        """Best-match-per-asset-chunk comparison. Returns PiracyReport."""
        t_start = time.perf_counter()
        logger.info(
            "Piracy detection | asset=%d chunks | suspect=%d chunks",
            len(asset_chunks), len(suspect_chunks),
        )

        asset_fps    = [self.fingerprint(c) for c in asset_chunks]
        asset_embs   = [self.embed(c)       for c in asset_chunks]
        suspect_fps  = [self.fingerprint(c) for c in suspect_chunks]
        suspect_embs = [self.embed(c)       for c in suspect_chunks]

        chunk_results: List[ComparisonResult] = []
        matched = 0

        for i, (fp_a, emb_a) in enumerate(zip(asset_fps, asset_embs)):
            best: Optional[ComparisonResult] = None
            for fp_b, emb_b in zip(suspect_fps, suspect_embs):
                result = self.compare(fp_a, emb_a, fp_b, emb_b, alpha=alpha)
                if best is None or result.fused_score > best.fused_score:
                    best = result
            chunk_results.append(best)
            if best.is_match:
                matched += 1
            logger.debug(
                "Chunk %d/%d — best fused=%.4f match=%s",
                i + 1, len(asset_chunks), best.fused_score, best.is_match,
            )

        overall = float(np.mean([r.fused_score for r in chunk_results])) if chunk_results else 0.0
        verdict = self._verdict(matched, len(asset_chunks), overall)
        elapsed = time.perf_counter() - t_start

        logger.info(
            "Piracy report | verdict=%s | matched=%d/%d | score=%.4f | t=%.2fs",
            verdict, matched, len(asset_chunks), overall, elapsed,
        )

        return PiracyReport(
            asset_path=asset_meta.path,
            asset_hash=asset_meta.file_hash,
            suspect_path=suspect_meta.path,
            chunk_level_results=chunk_results,
            overall_score=round(overall, 4),
            verdict=verdict,
            matched_chunks=matched,
            total_chunks=len(asset_chunks),
            analysis_time_sec=round(elapsed, 3),
        )

    def batch_compare_embeddings(
        self,
        query_emb: np.ndarray,
        corpus_embs: List[np.ndarray],
        top_k: int = 5,
    ) -> List[Tuple[int, float]]:
        """Fast cosine top-k search. Returns (index, score) pairs, descending."""
        if not corpus_embs:
            return []
        matrix = np.stack(corpus_embs)
        q_norm = query_emb / (np.linalg.norm(query_emb) + 1e-9)
        m_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
        scores  = m_norm @ q_norm
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [(int(i), float(scores[i])) for i in top_idx]

    # ── Chromaprint via acoustid ────────────────────────────────

    def _chromaprint_via_acoustid(self, waveform: np.ndarray, sr: int) -> List[int]:
        acoustid = _load_acoustid()
        if acoustid is None:
            return self._spectrogram_hash_fallback(waveform, sr)
        """
        Call acoustid.fingerprint() → decode base64url string → list of uint32.
        acoustid.fingerprint(rate, channels, pcm_iter) returns (duration, fp_str).
        """
        import base64
        import struct

        pcm_int16 = (waveform * 32767).clip(-32768, 32767).astype(np.int16)
        pcm_bytes = pcm_int16.tobytes()

        try:
            duration, fp_str = acoustid.fingerprint(sr, 1, iter([pcm_bytes]))
        except Exception as exc:
            logger.warning("acoustid.fingerprint() failed: %s — using fallback", exc)
            return AudioAnalyzer._spectrogram_hash_fallback(waveform, sr)

        try:
            padding = (4 - len(fp_str) % 4) % 4
            raw     = base64.b64decode(fp_str + "=" * padding, altchars=b"-_")
            # First 4 bytes = algorithm version header; skip them
            if len(raw) < 8:
                raise ValueError("Fingerprint too short")
            num_ints = (len(raw) - 4) // 4
            fp_ints  = list(struct.unpack(f"<{num_ints}I", raw[4 : 4 + num_ints * 4]))
            return fp_ints
        except Exception as exc:
            logger.warning("Fingerprint decode failed: %s — using fallback", exc)
            return AudioAnalyzer._spectrogram_hash_fallback(waveform, sr)

    # ── similarity helpers ──────────────────────────────────────

    @staticmethod
    def _chromaprint_similarity(fp_a: List[int], fp_b: List[int]) -> float:
        """
        Hamming-distance similarity over uint32 fingerprint arrays.
        Uses np.uint32 — never overflows regardless of bit pattern.
        """
        min_len = min(len(fp_a), len(fp_b))
        if min_len == 0:
            return 0.0
        a = np.array(fp_a[:min_len], dtype=np.uint32)
        b = np.array(fp_b[:min_len], dtype=np.uint32)
        xor        = np.bitwise_xor(a, b)
        total_bits = min_len * 32
        set_bits   = int(np.sum(np.unpackbits(xor.view(np.uint8))))
        return 1.0 - set_bits / total_bits

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        dot  = float(np.dot(a, b))
        norm = float(np.linalg.norm(a) * np.linalg.norm(b))
        if norm < 1e-9:
            return 0.0
        return max(0.0, min(1.0, dot / norm))

    @staticmethod
    def _spectrogram_hash_fallback(waveform: np.ndarray, sr: int) -> List[int]:
        """Mel-spectrogram column hashes — used when acoustid is unavailable."""
        import librosa
        mel    = librosa.feature.melspectrogram(y=waveform, sr=sr, n_mels=64)
        mel_db = librosa.power_to_db(mel, ref=np.max)
        return [
            int(hashlib.md5(col.tobytes()).hexdigest()[:8], 16) & 0xFFFFFFFF
            for col in mel_db.T
        ]

    # ── model loading ───────────────────────────────────────────

    def _ensure_model(self):
        if self._w2v_model is None:
            torch, trf = _load_torch()
            logger.info("Loading Wav2Vec2: %s …", self.wav2vec_model_id)
            self._w2v_processor = trf["proc_cls"].from_pretrained(self.wav2vec_model_id)
            self._w2v_model     = trf["model_cls"].from_pretrained(self.wav2vec_model_id)
            self._w2v_model.to(self._device).eval()
            logger.info("Wav2Vec2 ready on %s", self._device)
        return self._w2v_model, self._w2v_processor

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return device

    # ── verdict / interpret ─────────────────────────────────────

    def _verdict(self, matched: int, total: int, overall: float) -> str:
        if total == 0:
            return "NO_MATCH"
        ratio = matched / total
        if ratio >= 0.6 or overall >= self.match_threshold:
            return "MATCH"
        if ratio >= 0.25 or overall >= 0.6:
            return "PARTIAL"
        return "NO_MATCH"

    @staticmethod
    def _interpret(cp_sim: float, w2v_sim: float, fused: float) -> Tuple[str, str]:
        if fused >= 0.90:
            return "high",   "Very strong fingerprint + semantic match — near-identical audio"
        if fused >= 0.82:
            reason = (
                "Strong semantic match — re-encoded or format-converted copy likely"
                if w2v_sim > cp_sim else
                "Strong fingerprint match — same recording"
            )
            return "high", reason
        if fused >= 0.65:
            return "medium", "Partial match — possible pitch-shift, time-stretch, or segment excerpt"
        if fused >= 0.45:
            return "low",    "Weak match — may share short segments or be loosely related"
        return "low", "No meaningful match detected"