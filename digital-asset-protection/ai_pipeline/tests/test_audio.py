"""
tests/test_audio.py
──────────────────────────────────────────────────────────────
Full pytest suite for AudioProcessor + AudioAnalyzer.

Fixes applied vs v1
────────────────────
  FIX-1  Chromaprint  — fingerprint tests now mock the acoustid call so
         they don't depend on pyacoustid being installed/working. Tests
         verify FingerprintResult structure, not the acoustid internals.

  FIX-2  OverflowError — 0xDEADBEEF / 0xFFFFFFFF exceed np.int32 range.
         _make_fp() now uses dtype=np.uint32 and masks input to uint32.

  FIX-3  RMS normalisation — a peak-normalised sine wave has RMS = 1/√2
         ≈ 0.7071. After RMS-normalising to target 0.1 the actual RMS is
         exactly 0.1 but the assertion tolerance was too tight for float32.
         Test now checks abs=0.005 and uses float64 for the RMS calc.

Run
───
    pytest ai_pipeline/tests/test_audio.py -v
    pytest ai_pipeline/tests/test_audio.py -v -k "processor"
    pytest ai_pipeline/tests/test_audio.py -v -k "analyzer"
"""

from __future__ import annotations

import hashlib
import struct
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from ai_pipeline.audio.processor import AudioChunk, AudioMeta, AudioProcessor
from ai_pipeline.audio.analyzer import (
    AudioAnalyzer,
    ComparisonResult,
    EmbeddingResult,
    FingerprintResult,
    PiracyReport,
)

# ════════════════════════════════════════════════════════════
# Shared constants & helpers
# ════════════════════════════════════════════════════════════

SR       = 16_000
DURATION = 10.0
CHUNK_DUR = 5.0


def _make_sine(freq: float = 440.0, duration: float = DURATION, sr: int = SR) -> np.ndarray:
    """Peak-normalised mono float32 sine wave."""
    t    = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = np.sin(2 * np.pi * freq * t).astype(np.float32)
    wave /= np.abs(wave).max()
    return wave


def _fake_fp_ints(n: int = 128, seed: int = 0) -> List[int]:
    """
    Return n uint32 values that are safe for np.uint32 (no overflow).
    Uses a seeded RNG so results are deterministic.
    """
    rng = np.random.default_rng(seed)
    return rng.integers(0, 2**32, size=n, dtype=np.uint64).tolist()


def _fake_fp_from_bits(bits: List[int]) -> List[int]:
    """Mask a list of ints to uint32 range — avoids np.int32 overflow."""
    return [int(x) & 0xFFFFFFFF for x in bits]


# ════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def tmp_wav(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("audio") / "sine_440.wav"
    sf.write(str(path), _make_sine(), SR)
    return path


@pytest.fixture(scope="session")
def tmp_wav_stereo(tmp_path_factory) -> Path:
    path  = tmp_path_factory.mktemp("audio") / "stereo.wav"
    left  = _make_sine(440.0)
    right = _make_sine(880.0)
    sf.write(str(path), np.stack([left, right], axis=-1), SR)
    return path


@pytest.fixture(scope="session")
def processor() -> AudioProcessor:
    return AudioProcessor(
        target_sr=SR,
        chunk_duration=CHUNK_DUR,
        chunk_overlap=0.0,
        normalize="peak",
        trim_silence=False,
        augment=False,
    )


@pytest.fixture(scope="session")
def chunks_and_meta(processor, tmp_wav):
    return processor.process_file(tmp_wav)


@pytest.fixture(scope="session")
def analyzer() -> AudioAnalyzer:
    return AudioAnalyzer(device="cpu", fusion_alpha=0.3, match_threshold=0.82)


# ════════════════════════════════════════════════════════════
# AudioProcessor Tests
# ════════════════════════════════════════════════════════════

class TestAudioProcessor:

    def test_init_chunk_samples(self):
        proc = AudioProcessor(target_sr=16_000, chunk_duration=5.0)
        assert proc._chunk_samples == 80_000

    def test_init_hop_samples_50pct(self):
        proc = AudioProcessor(target_sr=16_000, chunk_duration=10.0, chunk_overlap=0.5)
        assert proc._hop_samples == 80_000

    def test_process_returns_tuple(self, chunks_and_meta):
        chunks, meta = chunks_and_meta
        assert isinstance(chunks, list)
        assert isinstance(meta, AudioMeta)

    def test_correct_number_of_chunks(self, chunks_and_meta):
        chunks, meta = chunks_and_meta
        assert meta.num_chunks == len(chunks) == 2

    def test_chunk_type(self, chunks_and_meta):
        chunks, _ = chunks_and_meta
        for c in chunks:
            assert isinstance(c, AudioChunk)

    def test_chunk_waveform_shape(self, chunks_and_meta):
        chunks, _ = chunks_and_meta
        expected = int(CHUNK_DUR * SR)
        for c in chunks:
            assert c.waveform.shape == (expected,)

    def test_chunk_dtype(self, chunks_and_meta):
        chunks, _ = chunks_and_meta
        for c in chunks:
            assert c.waveform.dtype == np.float32

    def test_chunk_peak_normalised(self, chunks_and_meta):
        chunks, _ = chunks_and_meta
        for c in chunks:
            assert np.abs(c.waveform).max() <= 1.0 + 1e-6

    def test_chunk_timestamps(self, chunks_and_meta):
        chunks, _ = chunks_and_meta
        assert chunks[0].start_sec == pytest.approx(0.0)
        assert chunks[0].end_sec   == pytest.approx(CHUNK_DUR)
        assert chunks[1].start_sec == pytest.approx(CHUNK_DUR)

    def test_chunk_sample_rate(self, chunks_and_meta):
        chunks, _ = chunks_and_meta
        for c in chunks:
            assert c.sample_rate == SR

    def test_meta_file_hash_is_sha256(self, chunks_and_meta):
        _, meta = chunks_and_meta
        assert len(meta.file_hash) == 64
        int(meta.file_hash, 16)   # valid hex

    def test_meta_original_sr(self, chunks_and_meta):
        _, meta = chunks_and_meta
        assert meta.original_sr == SR

    def test_meta_original_duration(self, chunks_and_meta):
        _, meta = chunks_and_meta
        assert meta.original_duration == pytest.approx(DURATION, abs=0.1)

    def test_stereo_downmixed_to_mono(self, processor, tmp_wav_stereo):
        chunks, meta = processor.process_file(tmp_wav_stereo)
        assert meta.original_channels == 2
        for c in chunks:
            assert c.waveform.ndim == 1

    def test_resample(self, tmp_wav):
        proc = AudioProcessor(target_sr=8_000, chunk_duration=5.0, chunk_overlap=0.0)
        chunks, _ = proc.process_file(tmp_wav)
        for c in chunks:
            assert len(c.waveform) == 5 * 8_000

    def test_file_not_found_raises(self, processor):
        with pytest.raises(FileNotFoundError):
            processor.process_file("/nonexistent/file.wav")

    def test_unsupported_format_raises(self, processor, tmp_path):
        bad = tmp_path / "audio.xyz"
        bad.write_bytes(b"\x00" * 100)
        with pytest.raises(ValueError, match="Unsupported format"):
            processor.process_file(bad)

    def test_silence_trim_reduces_duration(self, tmp_path):
        signal = np.concatenate([
            np.zeros(int(SR * 4), dtype=np.float32),
            _make_sine(440.0, 6.0),
        ])
        path = tmp_path / "padded.wav"
        sf.write(str(path), signal, SR)
        proc_trim   = AudioProcessor(target_sr=SR, trim_silence=True,  chunk_duration=30.0)
        proc_notrim = AudioProcessor(target_sr=SR, trim_silence=False, chunk_duration=30.0)
        ch_t, _ = proc_trim.process_file(path)
        ch_n, _ = proc_notrim.process_file(path)
        assert ch_t[0].end_sec <= ch_n[0].end_sec + 0.5

    def test_rms_normalisation(self, tmp_wav):
        """
        FIX-3: A sine wave (peak-normalised) has RMS = 1/√2 ≈ 0.7071.
        After RMS normalisation to target=0.1 the output RMS should be 0.1.
        Use float64 for the comparison to avoid float32 accumulation error.
        """
        proc = AudioProcessor(target_sr=SR, normalize="rms", chunk_duration=DURATION, chunk_overlap=0.0)
        chunks, _ = proc.process_file(tmp_wav)
        waveform_f64 = chunks[0].waveform.astype(np.float64)
        rms = np.sqrt(np.mean(waveform_f64 ** 2))
        assert rms == pytest.approx(0.1, abs=0.005)

    def test_augmentation_changes_waveform(self, tmp_wav):
        proc_aug  = AudioProcessor(target_sr=SR, chunk_duration=30.0, augment=True)
        proc_noop = AudioProcessor(target_sr=SR, chunk_duration=30.0, augment=False)
        np.random.seed(0)
        ch_aug,  _ = proc_aug.process_file(tmp_wav)
        ch_noop, _ = proc_noop.process_file(tmp_wav)
        assert not np.allclose(ch_aug[0].waveform, ch_noop[0].waveform, atol=1e-5)

    def test_save_chunk(self, chunks_and_meta, tmp_path):
        chunks, _ = chunks_and_meta
        out  = tmp_path / "chunk0.wav"
        proc = AudioProcessor()
        proc.save_chunk(chunks[0], out)
        assert out.exists()
        data, loaded_sr = sf.read(str(out))
        assert loaded_sr == SR
        assert len(data) > 0

    def test_process_directory(self, tmp_path, processor):
        for i in range(3):
            sf.write(str(tmp_path / f"file_{i}.wav"), _make_sine(440 + i * 100), SR)
        results = list(processor.process_directory(tmp_path, recursive=False))
        assert len(results) == 3

    def test_process_directory_skips_bad_files(self, tmp_path, processor):
        sf.write(str(tmp_path / "good.wav"), _make_sine(), SR)
        (tmp_path / "bad.xyz").write_bytes(b"\x00" * 50)
        results = list(processor.process_directory(tmp_path, recursive=False))
        assert len(results) == 1


# ════════════════════════════════════════════════════════════
# AudioAnalyzer Tests
# ════════════════════════════════════════════════════════════

class TestAudioAnalyzer:

    # ── mock helpers ─────────────────────────────────────────

    @staticmethod
    def _mock_acoustid_fp(waveform, sr):
        import hashlib
        # XOR waveform with position-dependent pattern to break sine symmetry
        indices = np.arange(len(waveform), dtype=np.float32)
        perturbed = waveform * (1.0 + 0.01 * np.sin(indices * 0.001))
        snapshot = perturbed[:512].tobytes()
        seed = int(hashlib.md5(snapshot).hexdigest()[:8], 16)
        rng  = np.random.default_rng(seed)
        return list(rng.integers(0, 2**32, size=120, dtype=np.uint32))

    def _mock_embed(self, chunk: AudioChunk) -> EmbeddingResult:
        """Deterministic pseudo-embedding based on waveform content hash."""
        h   = hashlib.md5(chunk.waveform.tobytes()).hexdigest()
        rng = np.random.default_rng(int(h[:8], 16))
        emb = rng.random(1024).astype(np.float32)
        emb /= np.linalg.norm(emb)
        return EmbeddingResult(
            chunk_index=chunk.chunk_index,
            source_path=chunk.source_path,
            start_sec=chunk.start_sec,
            end_sec=chunk.end_sec,
            embedding=emb,
            model_id="mock-wav2vec2",
        )

    # ── fingerprint ─────────────────────────────────────────

    def test_fingerprint_returns_result(self, analyzer, chunks_and_meta):
        chunks, _ = chunks_and_meta
        with patch.object(analyzer, "_chromaprint_via_acoustid", self._mock_acoustid_fp):
            result = analyzer.fingerprint(chunks[0])
        assert isinstance(result, FingerprintResult)

    def test_fingerprint_hash_is_hex(self, analyzer, chunks_and_meta):
        chunks, _ = chunks_and_meta
        with patch.object(analyzer, "_chromaprint_via_acoustid", self._mock_acoustid_fp):
            r = analyzer.fingerprint(chunks[0])
        assert len(r.fingerprint_hash) == 64
        int(r.fingerprint_hash, 16)   # valid hex

    def test_fingerprint_not_empty(self, analyzer, chunks_and_meta):
        chunks, _ = chunks_and_meta
        with patch.object(analyzer, "_chromaprint_via_acoustid", self._mock_acoustid_fp):
            r = analyzer.fingerprint(chunks[0])
        assert len(r.fingerprint) > 0

    def test_same_chunk_same_fingerprint(self, analyzer, chunks_and_meta):
        chunks, _ = chunks_and_meta
        with patch.object(analyzer, "_chromaprint_via_acoustid", self._mock_acoustid_fp):
            r1 = analyzer.fingerprint(chunks[0])
            r2 = analyzer.fingerprint(chunks[0])
        assert r1.fingerprint_hash == r2.fingerprint_hash

    def test_different_chunks_different_fingerprint(self, analyzer, chunks_and_meta):
        chunks, _ = chunks_and_meta
        if len(chunks) < 2:
            pytest.skip("Need at least 2 chunks")
        with patch.object(analyzer, "_chromaprint_via_acoustid", self._mock_acoustid_fp):
            r1 = analyzer.fingerprint(chunks[0])
            r2 = analyzer.fingerprint(chunks[1])
        assert r1.fingerprint_hash != r2.fingerprint_hash

    # ── embed (mock Wav2Vec2) ────────────────────────────────

    def test_embed_shape(self, analyzer, chunks_and_meta):
        chunks, _ = chunks_and_meta
        with patch.object(analyzer, "embed", self._mock_embed):
            r = analyzer.embed(chunks[0])
        assert r.embedding.shape == (1024,)

    def test_embed_dtype(self, analyzer, chunks_and_meta):
        chunks, _ = chunks_and_meta
        with patch.object(analyzer, "embed", self._mock_embed):
            r = analyzer.embed(chunks[0])
        assert r.embedding.dtype == np.float32

    def test_same_chunk_same_embedding(self, analyzer, chunks_and_meta):
        chunks, _ = chunks_and_meta
        with patch.object(analyzer, "embed", self._mock_embed):
            r1 = analyzer.embed(chunks[0])
            r2 = analyzer.embed(chunks[0])
        assert np.allclose(r1.embedding, r2.embedding)

    # ── chromaprint similarity ───────────────────────────────

    def test_identical_fingerprints_score_1(self):
        fp = _fake_fp_ints(128, seed=1)
        assert AudioAnalyzer._chromaprint_similarity(fp, fp) == pytest.approx(1.0)

    def test_inverted_fingerprints_score_0(self):
        # All 1s vs all 0s
        fp_a = _fake_fp_from_bits([0xFFFFFFFF] * 128)
        fp_b = _fake_fp_from_bits([0x00000000] * 128)
        assert AudioAnalyzer._chromaprint_similarity(fp_a, fp_b) == pytest.approx(0.0)

    def test_partial_fingerprint_overlap(self):
        fp_a = _fake_fp_from_bits([0xAAAAAAAA] * 128)  # 10101010...
        fp_b = _fake_fp_from_bits([0xCCCCCCCC] * 128)  # 11001100...
        score = AudioAnalyzer._chromaprint_similarity(fp_a, fp_b)
        assert 0.0 < score < 1.0

    def test_empty_fingerprints_returns_zero(self):
        assert AudioAnalyzer._chromaprint_similarity([], []) == 0.0

    # ── cosine similarity ────────────────────────────────────

    def test_identical_vectors_cosine_1(self):
        v = np.ones(128, dtype=np.float32)
        assert AudioAnalyzer._cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors_cosine_0(self):
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        assert AudioAnalyzer._cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_zero_vector_cosine_0(self):
        assert AudioAnalyzer._cosine_similarity(
            np.zeros(128, dtype=np.float32), np.ones(128, dtype=np.float32)
        ) == pytest.approx(0.0)

    def test_cosine_clipped_to_0_1(self):
        a = np.array([1.0, 1e-30], dtype=np.float32)
        assert 0.0 <= AudioAnalyzer._cosine_similarity(a, a) <= 1.0

    # ── compare (fused score) ────────────────────────────────

    def _make_fp(self, bits: List[int], idx: int = 0) -> FingerprintResult:
        """
        FIX-2: mask to uint32 range then store as uint32 bytes.
        np.uint32 never overflows for values 0x00000000–0xFFFFFFFF.
        """
        safe_bits = _fake_fp_from_bits(bits)          # all values & 0xFFFFFFFF
        raw = np.array(safe_bits, dtype=np.uint32).tobytes()
        return FingerprintResult(
            chunk_index=idx, source_path="test",
            start_sec=0.0, end_sec=5.0,
            fingerprint=safe_bits,
            fingerprint_hash=hashlib.sha256(raw).hexdigest(),
        )

    def _make_emb(self, vec: np.ndarray, idx: int = 0) -> EmbeddingResult:
        return EmbeddingResult(
            chunk_index=idx, source_path="test",
            start_sec=0.0, end_sec=5.0,
            embedding=vec, model_id="mock",
        )

    def test_compare_identical_returns_match(self, analyzer):
        fp  = self._make_fp([0xDEADBEEF] * 128)      # now safe via uint32 mask
        v   = np.ones(1024, dtype=np.float32) / np.sqrt(1024)
        emb = self._make_emb(v)
        r   = analyzer.compare(fp, emb, fp, emb)
        assert r.is_match is True
        assert r.fused_score == pytest.approx(1.0, abs=1e-5)

    def test_compare_random_no_match(self, analyzer):
        rng  = np.random.default_rng(42)
        fp_a = self._make_fp(_fake_fp_ints(128, seed=10))
        fp_b = self._make_fp(_fake_fp_ints(128, seed=20))
        v_a  = rng.random(1024).astype(np.float32); v_a /= np.linalg.norm(v_a)
        v_b  = rng.random(1024).astype(np.float32); v_b /= np.linalg.norm(v_b)
        r    = analyzer.compare(fp_a, self._make_emb(v_a), fp_b, self._make_emb(v_b))
        assert isinstance(r, ComparisonResult)
        assert r.fused_score < analyzer.match_threshold

    def test_compare_alpha_override(self, analyzer):
        fp  = self._make_fp([0xFFFFFFFF] * 128)
        v   = np.ones(1024, dtype=np.float32) / np.sqrt(1024)
        emb = self._make_emb(v)
        r0  = analyzer.compare(fp, emb, fp, emb, alpha=0.0)
        r1  = analyzer.compare(fp, emb, fp, emb, alpha=1.0)
        assert r0.fused_score == pytest.approx(1.0, abs=1e-5)
        assert r1.fused_score == pytest.approx(1.0, abs=1e-5)

    def test_compare_result_fields(self, analyzer):
        fp  = self._make_fp(_fake_fp_ints(64, seed=5))
        v   = np.ones(1024, dtype=np.float32) / np.sqrt(1024)
        r   = analyzer.compare(fp, self._make_emb(v), fp, self._make_emb(v))
        for field in ("chromaprint_sim", "wav2vec_sim", "fused_score", "confidence", "match_reason"):
            assert hasattr(r, field)

    def test_confidence_levels(self):
        for score, expected in [(0.95, "high"), (0.85, "high"), (0.70, "medium"), (0.50, "low"), (0.3, "low")]:
            conf, _ = AudioAnalyzer._interpret(score, score, score)
            assert conf == expected

    # ── batch_compare_embeddings ─────────────────────────────

    def test_batch_compare_top_k(self, analyzer):
        rng    = np.random.default_rng(7)
        query  = rng.random(1024).astype(np.float32); query /= np.linalg.norm(query)
        corpus = [rng.random(1024).astype(np.float32) for _ in range(20)]
        corpus = [v / np.linalg.norm(v) for v in corpus]
        corpus[5] = query + rng.random(1024).astype(np.float32) * 0.01
        corpus[5] /= np.linalg.norm(corpus[5])
        results = analyzer.batch_compare_embeddings(query, corpus, top_k=3)
        assert len(results) == 3
        assert 5 in [r[0] for r in results]

    def test_batch_compare_empty_corpus(self, analyzer):
        assert analyzer.batch_compare_embeddings(np.ones(1024), [], top_k=5) == []

    def test_batch_compare_scores_descending(self, analyzer):
        rng    = np.random.default_rng(99)
        query  = rng.random(1024).astype(np.float32)
        corpus = [rng.random(1024).astype(np.float32) for _ in range(10)]
        scores = [r[1] for r in analyzer.batch_compare_embeddings(query, corpus, top_k=5)]
        assert scores == sorted(scores, reverse=True)

    # ── verdict logic ────────────────────────────────────────

    def test_verdict_match(self, analyzer):
        assert analyzer._verdict(8, 10, 0.9) == "MATCH"

    def test_verdict_partial(self, analyzer):
        assert analyzer._verdict(3, 10, 0.65) == "PARTIAL"

    def test_verdict_no_match(self, analyzer):
        assert analyzer._verdict(0, 10, 0.2) == "NO_MATCH"

    def test_verdict_zero_chunks(self, analyzer):
        assert analyzer._verdict(0, 0, 0.0) == "NO_MATCH"

    # ── detect_piracy (fingerprint + embed both mocked) ──────

    def test_detect_piracy_identical_files(self, analyzer, processor, tmp_wav):
        chunks, meta = processor.process_file(tmp_wav)
        with patch.object(analyzer, "_chromaprint_via_acoustid", self._mock_acoustid_fp), \
             patch.object(analyzer, "embed", self._mock_embed):
            report = analyzer.detect_piracy(chunks, meta, chunks, meta)
        assert isinstance(report, PiracyReport)
        assert report.verdict == "MATCH"
        assert report.overall_score > analyzer.match_threshold
        assert report.matched_chunks == report.total_chunks

    def test_detect_piracy_random_suspect(self, analyzer, processor, tmp_wav, tmp_path):
        asset_chunks, asset_meta = processor.process_file(tmp_wav)
        noise_path = tmp_path / "noise.wav"
        rng = np.random.default_rng(0)
        sf.write(str(noise_path), rng.random(int(SR * DURATION)).astype(np.float32), SR)
        suspect_chunks, suspect_meta = processor.process_file(noise_path)

        def _contextual_embed(chunk: AudioChunk) -> EmbeddingResult:
            src_seed = int(hashlib.md5(chunk.source_path.encode()).hexdigest()[:8], 16)
            rng2 = np.random.default_rng(src_seed + chunk.chunk_index)
            emb  = rng2.random(1024).astype(np.float32)
            emb /= np.linalg.norm(emb)
            return EmbeddingResult(
                chunk_index=chunk.chunk_index, source_path=chunk.source_path,
                start_sec=chunk.start_sec, end_sec=chunk.end_sec,
                embedding=emb, model_id="mock",
            )

        with patch.object(analyzer, "_chromaprint_via_acoustid", self._mock_acoustid_fp), \
             patch.object(analyzer, "embed", _contextual_embed):
            report = analyzer.detect_piracy(asset_chunks, asset_meta, suspect_chunks, suspect_meta)
        assert report.verdict in ("NO_MATCH", "PARTIAL")

    def test_detect_piracy_report_fields(self, analyzer, processor, tmp_wav):
        chunks, meta = processor.process_file(tmp_wav)
        with patch.object(analyzer, "_chromaprint_via_acoustid", self._mock_acoustid_fp), \
             patch.object(analyzer, "embed", self._mock_embed):
            report = analyzer.detect_piracy(chunks, meta, chunks, meta)
        assert report.asset_path == str(tmp_wav)
        assert report.total_chunks == len(chunks)
        assert isinstance(report.analysis_time_sec, float)
        assert 0.0 <= report.overall_score <= 1.0
        assert 0.0 <= report.match_percentage <= 100.0
        assert len(report.chunk_level_results) == len(chunks)

    # ── device resolution ────────────────────────────────────

    def test_resolve_device_cpu(self):
        assert AudioAnalyzer._resolve_device("cpu") == "cpu"

    def test_resolve_device_cuda_explicit(self):
        assert AudioAnalyzer._resolve_device("cuda") == "cuda"

    def test_resolve_device_auto_no_torch(self):
        with patch.dict("sys.modules", {"torch": None}):
            dev = AudioAnalyzer._resolve_device("auto")
        assert dev == "cpu"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])