"""Authenticated, consent-gated NeuTTS-Air reference-voice API.

Raw reference audio is decoded only for enrollment and is never persisted.
Derived reference codes and the matching transcript are stored locally so an
approved voice can be selected by its opaque server-generated identifier.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import re
import secrets
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from neutts import NeuTTS


VOICE_ID_PATTERN = re.compile(r"^voice_[A-Za-z0-9_-]{16,64}$")
VOICE_FILE_SUFFIX = ".pt"
METADATA_FILE_SUFFIX = ".json"


@dataclass(frozen=True)
class Settings:
    admin_api_key: str
    synthesis_api_key: str
    backbone_repo: str
    codec_repo: str
    voices_dir: Path
    max_text_chars: int
    max_reference_bytes: int
    min_reference_seconds: float
    max_reference_seconds: float

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            admin_api_key=os.environ.get("NEUTTS_AIR_ADMIN_API_KEY", ""),
            synthesis_api_key=os.environ.get("NEUTTS_AIR_SYNTHESIS_API_KEY", ""),
            backbone_repo=os.environ.get("NEUTTS_AIR_BACKBONE_REPO", "neuphonic/neutts-air"),
            codec_repo=os.environ.get("NEUTTS_AIR_CODEC_REPO", "neuphonic/neucodec"),
            voices_dir=Path(os.environ.get("NEUTTS_AIR_VOICES_DIR", "/data/voices")),
            max_text_chars=int(os.environ.get("NEUTTS_AIR_MAX_TEXT_CHARS", "600")),
            max_reference_bytes=int(os.environ.get("NEUTTS_AIR_MAX_REFERENCE_BYTES", "10485760")),
            min_reference_seconds=float(os.environ.get("NEUTTS_AIR_MIN_REFERENCE_SECONDS", "3")),
            max_reference_seconds=float(os.environ.get("NEUTTS_AIR_MAX_REFERENCE_SECONDS", "15")),
        )


settings = Settings.from_environment()
model: NeuTTS | None = None
inference_lock = asyncio.Lock()


class SpeechRequest(BaseModel):
    model: str = Field(default="neutts-air")
    input: str = Field(min_length=1)
    voice: str
    response_format: str = Field(default="wav")
    emotion: str | None = None


class VoiceMetadata(BaseModel):
    id: str
    object: str = "voice"
    created_at: str
    model: str = "neutts-air"


def require_key(authorization: str | None, expected_key: str, scope: str) -> None:
    if not expected_key:
        raise HTTPException(status_code=503, detail=f"{scope} API key is not configured")
    expected = f"Bearer {expected_key}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")


def require_admin(authorization: str | None) -> None:
    require_key(authorization, settings.admin_api_key, "Administrator")


def require_synthesis(authorization: str | None) -> None:
    require_key(authorization, settings.synthesis_api_key, "Synthesis")


def voice_path(voice_id: str) -> Path:
    if not VOICE_ID_PATTERN.fullmatch(voice_id):
        raise HTTPException(status_code=400, detail="Invalid voice identifier")
    return settings.voices_dir / f"{voice_id}{VOICE_FILE_SUFFIX}"


def metadata_path(voice_id: str) -> Path:
    return voice_path(voice_id).with_suffix(METADATA_FILE_SUFFIX)


def load_voice(voice_id: str) -> tuple[object, str]:
    encoded_path = voice_path(voice_id)
    metadata_file = metadata_path(voice_id)
    if not encoded_path.is_file() or not metadata_file.is_file():
        raise HTTPException(status_code=404, detail="Voice not found")
    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        stored = torch.load(encoded_path, map_location="cpu", weights_only=True)
        reference_codes = stored["reference_codes"]
        reference_text = stored["reference_text"]
    except (KeyError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Stored voice is unavailable") from exc
    if metadata.get("id") != voice_id or not isinstance(reference_text, str):
        raise HTTPException(status_code=500, detail="Stored voice is invalid")
    return reference_codes, reference_text


def validate_reference(path: Path) -> None:
    try:
        info = sf.info(path)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail="Reference audio must be a valid WAV file") from exc
    if info.format != "WAV":
        raise HTTPException(status_code=400, detail="Reference audio must be WAV")
    if info.channels != 1:
        raise HTTPException(status_code=400, detail="Reference audio must be mono")
    if not 16_000 <= info.samplerate <= 44_100:
        raise HTTPException(status_code=400, detail="Reference sample rate must be 16 to 44.1 kHz")
    duration = info.frames / info.samplerate
    if not settings.min_reference_seconds <= duration <= settings.max_reference_seconds:
        raise HTTPException(
            status_code=400,
            detail=(
                "Reference duration must be between "
                f"{settings.min_reference_seconds:g} and {settings.max_reference_seconds:g} seconds"
            ),
        )


def persist_voice(reference_codes: object, reference_text: str, consent_record_id: str) -> VoiceMetadata:
    voice_id = f"voice_{secrets.token_urlsafe(18)}"
    encoded_path = voice_path(voice_id)
    metadata_file = metadata_path(voice_id)
    created_at = datetime.now(UTC).isoformat()
    metadata = VoiceMetadata(id=voice_id, created_at=created_at)
    payload = {"reference_codes": reference_codes, "reference_text": reference_text}
    try:
        torch.save(payload, encoded_path)
        os.chmod(encoded_path, 0o600)
        metadata_file.write_text(
            json.dumps(
                {
                    **metadata.model_dump(),
                    "consent_record_id": consent_record_id,
                },
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        os.chmod(metadata_file, 0o600)
    except OSError as exc:
        encoded_path.unlink(missing_ok=True)
        metadata_file.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not persist enrolled voice") from exc
    return metadata


def synthesize(text: str, voice_id: str, emotion: str | None) -> bytes:
    if model is None:
        raise RuntimeError("NeuTTS-Air model is not initialized")
    if emotion is not None:
        raise HTTPException(status_code=400, detail="NeuTTS-Air does not support emotion controls")
    reference_codes, reference_text = load_voice(voice_id)
    prompt_ids = model._apply_chat_template(reference_codes, reference_text, text)
    if len(prompt_ids) + 50 > model.max_context:
        raise HTTPException(status_code=400, detail="Input and enrolled reference exceed the NeuTTS-Air context limit")
    waveform: np.ndarray = model.infer(text, reference_codes, reference_text)
    output = io.BytesIO()
    sf.write(output, waveform, 24_000, format="WAV", subtype="PCM_16")
    return output.getvalue()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global model
    settings.voices_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(settings.voices_dir, 0o700)
    model = NeuTTS(
        backbone_repo=settings.backbone_repo,
        backbone_device="cpu",
        codec_repo=settings.codec_repo,
        codec_device="cpu",
    )
    yield
    model = None


app = FastAPI(title="NeuTTS-Air Custom Voice API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def protect_enrollment_ingress(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/v1/voices":
        # This runs before FastAPI parses multipart data, preventing an
        # unauthorized or oversized body from being spooled by Starlette.
        expected = f"Bearer {settings.admin_api_key}"
        if not settings.admin_api_key or not secrets.compare_digest(request.headers.get("authorization", ""), expected):
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
        content_length = request.headers.get("content-length")
        max_body_bytes = settings.max_reference_bytes + 16_384
        if content_length is None or not content_length.isdigit() or int(content_length) > max_body_bytes:
            return JSONResponse(status_code=413, content={"detail": "Reference request exceeds size limit"})
    return await call_next(request)


@app.get("/healthz")
def healthz() -> dict[str, object]:
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "backbone": settings.backbone_repo,
        "codec": settings.codec_repo,
        "device": "cpu",
        "raw_reference_audio_persisted": False,
    }


@app.get("/v1/models")
def list_models(authorization: str | None = Header(default=None)) -> dict[str, object]:
    require_admin(authorization)
    return {"object": "list", "data": [{"id": "neutts-air", "object": "model"}]}


@app.get("/v1/voices")
def list_voices(authorization: str | None = Header(default=None)) -> dict[str, object]:
    require_admin(authorization)
    voices: list[dict[str, object]] = []
    for metadata_file in sorted(settings.voices_dir.glob(f"*{METADATA_FILE_SUFFIX}")):
        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            voice_id = metadata.get("id")
            if isinstance(voice_id, str) and voice_path(voice_id).is_file():
                voices.append(VoiceMetadata.model_validate(metadata).model_dump())
        except (OSError, ValueError, json.JSONDecodeError, HTTPException):
            continue
    return {"object": "list", "data": voices}


@app.post("/v1/voices", status_code=status.HTTP_201_CREATED)
async def enroll_voice(
    reference_audio: UploadFile = File(...),
    reference_text: str = Form(..., min_length=1, max_length=1000),
    consent_record_id: str = Form(..., min_length=6, max_length=200),
    authorization: str | None = Header(default=None),
) -> VoiceMetadata:
    require_admin(authorization)
    if reference_audio.content_type not in {"audio/wav", "audio/x-wav", "audio/wave"}:
        raise HTTPException(status_code=415, detail="Reference audio must have a WAV content type")
    if model is None:
        raise HTTPException(status_code=503, detail="NeuTTS-Air model is not initialized")

    suffix = ".wav"
    total = 0
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            while chunk := await reference_audio.read(65_536):
                total += len(chunk)
                if total > settings.max_reference_bytes:
                    raise HTTPException(status_code=413, detail="Reference audio exceeds size limit")
                temporary.write(chunk)
        validate_reference(temporary_path)
        async with inference_lock:
            reference_codes = await asyncio.to_thread(model.encode_reference, str(temporary_path))
            return await asyncio.to_thread(persist_voice, reference_codes, reference_text, consent_record_id)
    finally:
        await reference_audio.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@app.delete("/v1/voices/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_voice(voice_id: str, authorization: str | None = Header(default=None)) -> Response:
    require_admin(authorization)
    encoded_path = voice_path(voice_id)
    metadata_file = metadata_path(voice_id)
    if not encoded_path.exists() and not metadata_file.exists():
        raise HTTPException(status_code=404, detail="Voice not found")
    encoded_path.unlink(missing_ok=True)
    metadata_file.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/v1/audio/speech")
async def create_speech(
    request: SpeechRequest,
    authorization: str | None = Header(default=None),
) -> Response:
    require_synthesis(authorization)
    if request.model != "neutts-air":
        raise HTTPException(status_code=400, detail="Only model 'neutts-air' is available")
    if request.response_format != "wav":
        raise HTTPException(status_code=400, detail="Only response_format 'wav' is supported")
    if len(request.input) > settings.max_text_chars:
        raise HTTPException(status_code=400, detail="Input exceeds NEUTTS_AIR_MAX_TEXT_CHARS")
    async with inference_lock:
        audio = await asyncio.to_thread(synthesize, request.input, request.voice, request.emotion)
    return Response(content=audio, media_type="audio/wav")
