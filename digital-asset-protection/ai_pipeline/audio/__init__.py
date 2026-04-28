"""
Audio AI Module — Digital Asset Protection System
Next-Level Stack: Chromaprint + Wav2Vec2 (facebook/wav2vec2-large-960h)

Components:
    - AudioProcessor  : Load, resample, chunk, augment audio
    - AudioAnalyzer   : Fingerprinting (Chromaprint) + Deep embedding (Wav2Vec2)
"""

from .processor import AudioProcessor
from .analyzer import AudioAnalyzer

__all__ = ["AudioProcessor", "AudioAnalyzer"]