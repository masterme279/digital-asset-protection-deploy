from __future__ import annotations

import os
import threading
from typing import Annotated

import numpy as np
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

import open_clip


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _normalize(vec: np.ndarray) -> np.ndarray:
    denom = float(np.linalg.norm(vec) + 1e-12)
    return (vec / denom).astype(np.float32)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    a_n = _normalize(a)
    b_n = _normalize(b)
    return float(np.dot(a_n, b_n))


def _load_image(upload: UploadFile) -> Image.Image:
    if not upload.content_type or not upload.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")
    try:
        img = Image.open(upload.file)
        return img.convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}")


class Models:
    def __init__(self) -> None:
        self.device = "cpu"

        # Keep CPU use predictable (Render RAM/CPU is limited)
        torch.set_grad_enabled(False)
        torch.set_num_threads(_env_int("TORCH_NUM_THREADS", 1))
        try:
            torch.set_num_interop_threads(_env_int("TORCH_NUM_INTEROP_THREADS", 1))
        except Exception:
            pass

        # NOTE: Render free (512MB) will often OOM with ViT-B/32 + DINOv2 in fp32.
        # RN50 is smaller; you can still override via env.
        clip_arch = _env_str("CLIP_ARCH", "RN50")
        clip_pretrained = _env_str("CLIP_PRETRAINED", "openai")
        self.load_clip = _env_bool("LOAD_CLIP", True)
        self.load_dinov2 = _env_bool("LOAD_DINOV2", True)
        self.quantize_int8 = _env_bool("MODEL_QUANTIZE_INT8", True)

        self.clip_model = None
        self.clip_preprocess = None
        self.clip_tokenizer = None

        if self.load_clip:
            self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
                clip_arch,
                pretrained=clip_pretrained,
                force_quick_gelu=True,
            )
            self.clip_tokenizer = open_clip.get_tokenizer(clip_arch)
            self.clip_model = self.clip_model.to(self.device)
            self.clip_model.eval()

            if self.quantize_int8:
                # Dynamic quantization reduces RAM a lot on CPU. Inference becomes slower (OK for hackathon deploy).
                try:
                    self.clip_model = torch.quantization.quantize_dynamic(
                        self.clip_model,
                        {torch.nn.Linear},
                        dtype=torch.qint8,
                    )
                except Exception:
                    # If quantization fails for any reason, continue with fp32.
                    pass

        self.dino_processor = None
        self.dino_model = None
        dinov2_model_id = _env_str("DINOV2_MODEL", "facebook/dinov2-vits14")
        if self.load_dinov2:
            self.dino_processor = AutoImageProcessor.from_pretrained(dinov2_model_id)
            self.dino_model = AutoModel.from_pretrained(dinov2_model_id, low_cpu_mem_usage=True)
            self.dino_model = self.dino_model.to(self.device)
            self.dino_model.eval()

            if self.quantize_int8:
                try:
                    self.dino_model = torch.quantization.quantize_dynamic(
                        self.dino_model,
                        {torch.nn.Linear},
                        dtype=torch.qint8,
                    )
                except Exception:
                    pass

        self.clip_arch = clip_arch
        self.clip_pretrained = clip_pretrained
        self.dinov2_model_id = dinov2_model_id

    def clip_image_embedding(self, image: Image.Image) -> np.ndarray:
        if self.clip_model is None or self.clip_preprocess is None:
            raise RuntimeError("CLIP is disabled (LOAD_CLIP=0)")
        tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)
        with torch.inference_mode():
            emb = self.clip_model.encode_image(tensor)
        return emb.detach().cpu().numpy().flatten().astype(np.float32)

    def clip_text_embedding(self, text: str) -> np.ndarray:
        if self.clip_model is None or self.clip_tokenizer is None:
            raise RuntimeError("CLIP is disabled (LOAD_CLIP=0)")
        tokens = self.clip_tokenizer([text]).to(self.device)
        with torch.inference_mode():
            emb = self.clip_model.encode_text(tokens)
        return emb.detach().cpu().numpy().flatten().astype(np.float32)

    def dinov2_embedding(self, image: Image.Image) -> np.ndarray:
        if self.dino_model is None or self.dino_processor is None:
            raise RuntimeError("DINOv2 is disabled (LOAD_DINOV2=0)")
        inputs = self.dino_processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.inference_mode():
            outputs = self.dino_model(**inputs)
        cls = outputs.last_hidden_state[:, 0, :]
        return cls.detach().cpu().numpy().flatten().astype(np.float32)


_models: Models | None = None
_models_error: str | None = None
_models_loading: bool = False


def _load_models_once() -> None:
    global _models, _models_error, _models_loading
    if _models is not None or _models_loading:
        return
    _models_loading = True
    try:
        _models = Models()
        _models_error = None
    except Exception as exc:  # noqa: BLE001
        _models = None
        _models_error = f"{type(exc).__name__}: {exc}"
    finally:
        _models_loading = False


app = FastAPI(title="Sentinel ML API (CLIP + DINOv2)")


@app.on_event("startup")
def _startup() -> None:
    # Load in background so the server boots fast on Render.
    threading.Thread(target=_load_models_once, daemon=True).start()

cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"] ,
)


@app.get("/health")
def health() -> dict:
    loaded = _models is not None
    return {
        "status": "ok",
        "models_loaded": loaded,
        "models_loading": _models_loading,
        "models_error": _models_error,
        "device": "cpu",
        "clip": {
            "arch": getattr(_models, "clip_arch", None),
            "pretrained": getattr(_models, "clip_pretrained", None),
            "enabled": getattr(_models, "load_clip", None),
        },
        "dinov2": {
            "model": getattr(_models, "dinov2_model_id", None),
            "enabled": getattr(_models, "load_dinov2", None),
        },
        "quantize_int8": getattr(_models, "quantize_int8", None),
    }


@app.post("/infer/text-image")
async def infer_text_image(
    image: Annotated[UploadFile, File(...)],
    text: Annotated[str, Form(...)],
) -> dict:
    if _models is None:
        raise HTTPException(status_code=503, detail="Models not loaded yet")

    img = _load_image(image)

    with torch.inference_mode():
        img_emb = _models.clip_image_embedding(img)
        txt_emb = _models.clip_text_embedding(text)

    sim = _cosine(img_emb, txt_emb)
    return {
        "clip_similarity": sim,
        "clip_embedding_dim": int(img_emb.shape[0]),
    }


@app.post("/infer/image-pair")
async def infer_image_pair(
    image_a: Annotated[UploadFile, File(...)],
    image_b: Annotated[UploadFile, File(...)],
) -> dict:
    if _models is None:
        raise HTTPException(status_code=503, detail="Models not loaded yet")

    a = _load_image(image_a)
    b = _load_image(image_b)

    with torch.inference_mode():
        a_clip = _models.clip_image_embedding(a)
        b_clip = _models.clip_image_embedding(b)
        a_dino = _models.dinov2_embedding(a)
        b_dino = _models.dinov2_embedding(b)

    clip_sim = _cosine(a_clip, b_clip)
    dino_sim = _cosine(a_dino, b_dino)
    combined = float((clip_sim + dino_sim) / 2.0)

    return {
        "clip_similarity": clip_sim,
        "dinov2_similarity": dino_sim,
        "combined_similarity": combined,
        "dims": {
            "clip": int(a_clip.shape[0]),
            "dinov2": int(a_dino.shape[0]),
        },
    }
