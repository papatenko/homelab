"""Small OpenAI-compatible HTTP wrapper around CPU-first NeuTTS-2E."""

from __future__ import annotations

import asyncio
import io
import os
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass

import numpy as np
import soundfile as sf
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from neutts import NeuTTS2E


@dataclass(frozen=True)
class Settings:
    api_key: str
    backbone_repo: str
    codec_repo: str
    default_speaker: str
    default_emotion: str
    max_text_chars: int


    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            api_key=os.environ.get("NEUTTS_API_KEY", ""),
            backbone_repo=os.environ.get("NEUTTS_BACKBONE_REPO", "neuphonic/neutts-2e-q4-gguf"),
            codec_repo=os.environ.get("NEUTTS_CODEC_REPO", "neuphonic/neucodec-onnx-decoder-int8"),
            default_speaker=os.environ.get("NEUTTS_SPEAKER", "emily"),
            default_emotion=os.environ.get("NEUTTS_EMOTION", "neutral"),
            max_text_chars=int(os.environ.get("NEUTTS_MAX_TEXT_CHARS", "2000")),
        )


settings = Settings.from_environment()
model: NeuTTS2E | None = None
inference_lock = asyncio.Lock()


class SpeechRequest(BaseModel):
    model: str = Field(default="neutts-2e")
    input: str = Field(min_length=1)
    voice: str | None = None
    response_format: str = Field(default="wav")
    emotion: str | None = None


def require_authorization(authorization: str | None) -> None:
    if not settings.api_key:
        return
    expected = f"Bearer {settings.api_key}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")


def get_voice_name(request: SpeechRequest) -> str:
    voice = request.voice or settings.default_speaker
    if voice not in NeuTTS2E.SPEAKERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown voice '{voice}'. Available voices: {', '.join(NeuTTS2E.SPEAKERS)}",
        )
    return voice


def get_emotion_name(request: SpeechRequest) -> str:
    emotion = request.emotion or settings.default_emotion
    if emotion not in NeuTTS2E.EMOTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown emotion '{emotion}'. Available emotions: {', '.join(NeuTTS2E.EMOTIONS)}",
        )
    return emotion


def synthesize(text: str, speaker: str, emotion: str) -> bytes:
    if model is None:
        raise RuntimeError("NeuTTS model is not initialized")
    waveform: np.ndarray = model.infer(text, speaker=speaker, emotion=emotion)
    output = io.BytesIO()
    sf.write(output, waveform, 24000, format="WAV", subtype="PCM_16")
    return output.getvalue()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global model
    model = NeuTTS2E(
        backbone_repo=settings.backbone_repo,
        backbone_device="cpu",
        codec_repo=settings.codec_repo,
        codec_device="cpu",
    )
    model.warmup()
    yield
    model = None


app = FastAPI(title="NeuTTS API", version="1.4.1", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, object]:
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "backbone": settings.backbone_repo,
        "codec": settings.codec_repo,
        "device": "cpu",
    }


@app.get("/v1/models")
def list_models(authorization: str | None = Header(default=None)) -> dict[str, object]:
    require_authorization(authorization)
    return {"object": "list", "data": [{"id": "neutts-2e", "object": "model"}]}


@app.post("/v1/audio/speech")
async def create_speech(
    request: SpeechRequest,
    authorization: str | None = Header(default=None),
) -> Response:
    require_authorization(authorization)
    if request.model != "neutts-2e":
        raise HTTPException(status_code=400, detail="Only model 'neutts-2e' is available")
    if request.response_format != "wav":
        raise HTTPException(status_code=400, detail="Only response_format 'wav' is supported")
    if len(request.input) > settings.max_text_chars:
        raise HTTPException(status_code=400, detail="Input exceeds NEUTTS_MAX_TEXT_CHARS")
    speaker = get_voice_name(request)
    emotion = get_emotion_name(request)
    async with inference_lock:
        audio = await asyncio.to_thread(synthesize, request.input, speaker, emotion)
    return Response(content=audio, media_type="audio/wav")
