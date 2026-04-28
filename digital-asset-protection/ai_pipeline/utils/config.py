import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

@dataclass
class ModelConfig:
    clip_model: str = "ViT-B/32"
    dinov2_model: str = "facebook/dinov2-base"
    wav2vec_model: str = "facebook/wav2vec2-base"
    device: str = "cuda" if os.getenv("USE_GPU", "false").lower() == "true" else "cpu"

@dataclass
class MilvusConfig:
    host: str = os.getenv("MILVUS_HOST", "localhost")
    port: int = int(os.getenv("MILVUS_PORT", "19530"))
    image_collection: str = "image_fingerprints"
    video_collection: str = "video_fingerprints"
    audio_collection: str = "audio_fingerprints"
    dim_clip: int = 512
    dim_dinov2: int = 768
    dim_audio: int = 768

@dataclass
class PipelineConfig:
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
    batch_size: int = 32
    max_frames_per_video: int = 30
    audio_sample_rate: int = 16000
    image_size: tuple = field(default_factory=lambda: (224, 224))
    supported_image_formats: tuple = field(default_factory=lambda: (".jpg", ".jpeg", ".png", ".webp", ".bmp"))
    supported_video_formats: tuple = field(default_factory=lambda: (".mp4", ".avi", ".mov", ".mkv", ".flv"))
    supported_audio_formats: tuple = field(default_factory=lambda: (".mp3", ".wav", ".flac", ".aac", ".ogg"))

@dataclass
class PathConfig:
    raw_data: Path = BASE_DIR / "data" / "raw"
    processed_data: Path = BASE_DIR / "data" / "processed"
    samples: Path = BASE_DIR / "data" / "samples"
    logs: Path = BASE_DIR / "logs"

    def __post_init__(self):
        for p in [self.raw_data, self.processed_data, self.samples, self.logs]:
            p.mkdir(parents=True, exist_ok=True)

@dataclass
class AppConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    milvus: MilvusConfig = field(default_factory=MilvusConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    paths: PathConfig = field(default_factory=PathConfig)

config = AppConfig()