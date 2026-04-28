"""
audio/processor.py
──────────────────────────────────────────────────────────────
Next-Level Stack : Chromaprint + Wav2Vec2
Role             : Raw audio ingestion → clean, normalised tensors

Responsibilities
────────────────
  • Load any audio format (mp3 / mp4 / wav / flac / ogg / aac)
    via  librosa  (backend: soundfile / audioread)
  • Resample to target SR (default 16 000 Hz — Wav2Vec2 requirement)
  • Mono-downmix  stereo / multi-channel inputs
  • Amplitude normalisation  (peak or RMS)
  • Silence trimming  (configurable threshold)
  • Fixed-length chunking  with overlap  (sliding window)
  • Augmentation pipeline  (noise, pitch-shift, time-stretch, reverb)
    for robustness testing
  • Batch processing  across a directory  (glob / recursive)
  • Returns  numpy arrays  *and*  metadata dicts  used by AudioAnalyzer
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator, List, Optional, Tuple

import librosa
import numpy as np
import soundfile as sf

logger = logging.getLogger("audio.processor")


# ──────────────────────────────────────────────────────────────
# Data containers
# ──────────────────────────────────────────────────────────────

@dataclass
class AudioChunk:
    """One fixed-length segment of a loaded audio file."""

    waveform: np.ndarray          # shape (samples,)  float32, normalised
    sample_rate: int
    start_sec: float
    end_sec: float
    chunk_index: int
    source_path: str

    @property
    def duration(self) -> float:
        return self.end_sec - self.start_sec

    @property
    def num_samples(self) -> int:
        return len(self.waveform)


@dataclass
class AudioMeta:
    """Metadata extracted during loading."""

    path: str
    file_hash: str                # SHA-256 of raw bytes
    original_sr: int
    original_duration: float      # seconds
    original_channels: int
    target_sr: int
    processed_duration: float     # after trim
    num_chunks: int
    processed_at: float = field(default_factory=time.time)


# ──────────────────────────────────────────────────────────────
# Processor
# ──────────────────────────────────────────────────────────────

class AudioProcessor:
    """
    High-fidelity audio pre-processing pipeline.

    Parameters
    ----------
    target_sr       : int   – resample target (16000 for Wav2Vec2)
    chunk_duration  : float – window length in seconds  (default 30 s)
    chunk_overlap   : float – overlap fraction [0, 1)   (default 0.5)
    normalize       : str   – "peak" | "rms" | None
    trim_silence    : bool  – strip leading/trailing silence
    trim_top_db     : float – silence threshold in dB   (default 40)
    augment         : bool  – apply augmentation during chunking
    """

    SUPPORTED_EXT = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a", ".mp4", ".opus", ".webm"}

    def __init__(
        self,
        target_sr: int = 16_000,
        chunk_duration: float = 30.0,
        chunk_overlap: float = 0.5,
        normalize: Optional[str] = "peak",
        trim_silence: bool = True,
        trim_top_db: float = 40.0,
        augment: bool = False,
    ) -> None:
        self.target_sr = target_sr
        self.chunk_duration = chunk_duration
        self.chunk_overlap = chunk_overlap
        self.normalize = normalize
        self.trim_silence = trim_silence
        self.trim_top_db = trim_top_db
        self.augment = augment

        self._chunk_samples = int(chunk_duration * target_sr)
        self._hop_samples = int(self._chunk_samples * (1 - chunk_overlap))

        logger.info(
            "AudioProcessor ready | SR=%d | chunk=%.1fs | overlap=%.0f%% | norm=%s | aug=%s",
            target_sr, chunk_duration, chunk_overlap * 100, normalize, augment,
        )

    # ── public API ──────────────────────────────────────────────

    def process_file(self, audio_path: str | Path) -> Tuple[List[AudioChunk], AudioMeta]:
        """
        Full pipeline for a single file.

        Returns
        -------
        chunks : list of AudioChunk
        meta   : AudioMeta
        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")
        if path.suffix.lower() not in self.SUPPORTED_EXT:
            raise ValueError(f"Unsupported format: {path.suffix}")

        logger.debug("Loading %s", path.name)

        # ── 1. raw load  ──────────────────────────────────────
        raw_bytes = path.read_bytes()
        file_hash = hashlib.sha256(raw_bytes).hexdigest()

        waveform, orig_sr = librosa.load(
            str(path),
            sr=None,          # load at native SR first
            mono=False,       # preserve channels for meta
        )

        orig_channels = 1 if waveform.ndim == 1 else waveform.shape[0]
        orig_duration = waveform.shape[-1] / orig_sr

        # ── 2. downmix → mono ─────────────────────────────────
        if waveform.ndim > 1:
            waveform = librosa.to_mono(waveform)

        # ── 3. resample ───────────────────────────────────────
        if orig_sr != self.target_sr:
            waveform = librosa.resample(waveform, orig_sr=orig_sr, target_sr=self.target_sr)

        waveform = waveform.astype(np.float32)

        # ── 4. silence trim ───────────────────────────────────
        if self.trim_silence:
            waveform, _ = librosa.effects.trim(waveform, top_db=self.trim_top_db)

        processed_duration = len(waveform) / self.target_sr

        # ── 5. normalise ──────────────────────────────────────
        waveform = self._normalise(waveform)

        # ── 6. chunk ──────────────────────────────────────────
        chunks = list(self._sliding_chunks(waveform, str(path)))

        meta = AudioMeta(
            path=str(path),
            file_hash=file_hash,
            original_sr=orig_sr,
            original_duration=orig_duration,
            original_channels=orig_channels,
            target_sr=self.target_sr,
            processed_duration=processed_duration,
            num_chunks=len(chunks),
        )

        logger.info(
            "Processed '%s' → %.1f s → %d chunk(s)",
            path.name, processed_duration, len(chunks),
        )
        return chunks, meta

    def process_directory(
        self,
        dir_path: str | Path,
        recursive: bool = True,
    ) -> Generator[Tuple[List[AudioChunk], AudioMeta], None, None]:
        """
        Yield (chunks, meta) for every audio file found under dir_path.
        Skips unsupported formats with a warning.
        """
        dir_path = Path(dir_path)
        pattern = "**/*" if recursive else "*"
        files = [f for f in dir_path.glob(pattern) if f.suffix.lower() in self.SUPPORTED_EXT]
        logger.info("Found %d audio file(s) in '%s'", len(files), dir_path)

        for f in files:
            try:
                yield self.process_file(f)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping '%s': %s", f.name, exc)

    def save_chunk(self, chunk: AudioChunk, output_path: str | Path) -> None:
        """Write a single chunk back to disk as 16-bit WAV."""
        sf.write(str(output_path), chunk.waveform, chunk.sample_rate, subtype="PCM_16")

    # ── internal helpers ────────────────────────────────────────

    def _normalise(self, waveform: np.ndarray) -> np.ndarray:
        if self.normalize == "peak":
            peak = np.abs(waveform).max()
            if peak > 1e-8:
                waveform = waveform / peak
        elif self.normalize == "rms":
            # Normalize before chunking — compute RMS on actual signal only
            # (ignores zero-padding that happens later in _sliding_chunks)
            nonzero = waveform[np.abs(waveform) > 1e-8]
            signal = nonzero if len(nonzero) > 0 else waveform
            rms = np.sqrt(np.mean(signal.astype(np.float64) ** 2))
            if rms > 1e-8:
                waveform = (waveform.astype(np.float64) / rms * 0.1).astype(np.float32)
        return waveform

    def _sliding_chunks(
        self, waveform: np.ndarray, source_path: str
    ) -> Generator[AudioChunk, None, None]:
        total_samples = len(waveform)
        idx = 0
        chunk_i = 0

        while idx < total_samples:
            end = min(idx + self._chunk_samples, total_samples)
            segment = waveform[idx:end]

            # Zero-pad last chunk if shorter
            if len(segment) < self._chunk_samples:
                pad = np.zeros(self._chunk_samples - len(segment), dtype=np.float32)
                segment = np.concatenate([segment, pad])

            if self.augment:
                segment = self._augment(segment)

            yield AudioChunk(
                waveform=segment,
                sample_rate=self.target_sr,
                start_sec=idx / self.target_sr,
                end_sec=end / self.target_sr,
                chunk_index=chunk_i,
                source_path=source_path,
            )

            idx += self._hop_samples
            chunk_i += 1

    def _augment(self, waveform: np.ndarray) -> np.ndarray:
        """
        Lightweight augmentation: additive white noise + optional time-stretch.
        Keeps it CPU-only (no torch dependency here).
        """
        # Additive Gaussian noise  (SNR ~ 30 dB)
        noise_amp = 0.001 * np.random.randn(*waveform.shape).astype(np.float32)
        waveform = waveform + noise_amp

        # Random time-stretch  [0.95, 1.05]
        rate = np.random.uniform(0.95, 1.05)
        try:
            stretched = librosa.effects.time_stretch(waveform, rate=rate)
            # Re-align to original length
            if len(stretched) >= len(waveform):
                waveform = stretched[: len(waveform)]
            else:
                pad = np.zeros(len(waveform) - len(stretched), dtype=np.float32)
                waveform = np.concatenate([stretched, pad])
        except Exception:  # noqa: BLE001
            pass  # fall back to un-stretched on any error

        return waveform