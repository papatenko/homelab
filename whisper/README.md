# Whisper

Self-hosted, OpenAI-compatible Whisper speech-to-text API with one GitOps stack that can run in CPU or NVIDIA CUDA mode.

## Runtime modes

Select exactly one Compose profile through the Portainer stack environment:

```text
COMPOSE_PROFILES=cpu
```

or:

```text
COMPOSE_PROFILES=gpu
```

The CPU profile runs `hwdsl2/whisper-server:latest`. The GPU profile runs `hwdsl2/whisper-server:cuda` with an NVIDIA device reservation. Both profiles use the same container name, port, API contract, persistent data path, and environment variables, so switching modes does not require changing Hermes or OpenWhispr endpoints.

## GPU requirements

The GPU profile requires:

- Docker Desktop with the WSL2 backend
- A working NVIDIA driver
- Docker GPU support verified with `docker run --rm --gpus all ... nvidia-smi`
- An NVIDIA-capable host

Use `WHISPER_MODEL=large-v3-turbo` for the preferred multilingual dictation model on the RTX 2070. If that model does not fit or has unacceptable latency, use `medium` or `small`.

## Portainer variables

Required or recommended values:

```env
DATA_DIR=/opt/stacks/whisper
COMPOSE_PROFILES=gpu
WHISPER_IMAGE=hwdsl2/whisper-server:latest
WHISPER_GPU_IMAGE=hwdsl2/whisper-server:cuda
WHISPER_MODEL=large-v3-turbo
WHISPER_LANGUAGE=auto
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
WHISPER_THREADS=2
WHISPER_LOG_LEVEL=INFO
WHISPER_DISABLE_USAGE_COUNTS=1
WHISPER_API_KEY=TOKEN_HERE
COMPOSE_PORT_HTTP=9000
```

For CPU mode, use `COMPOSE_PROFILES=cpu`, `WHISPER_DEVICE=cpu`, and `WHISPER_COMPUTE_TYPE=int8`.

Keep the real API key in Portainer only. Do not commit it or place it in this repository. Leave it blank only for a deliberately trusted VPN-only deployment.

## API

- Internal HTTP port: `9000`
- OpenAI-compatible base URL: `http://<host>:9000/v1`
- Transcription: `POST /v1/audio/transcriptions`
- Translation: `POST /v1/audio/translations`
- Models: `GET /v1/models`

The model is downloaded into `${DATA_DIR}/data` on first startup, so initial deployment can take longer.

## Hermes and OpenWhispr

Both CPU and GPU profiles preserve the same OpenAI-compatible endpoint. Clients should use model `whisper-1` unless the client specifically supports the server's model name.

Do not expose this upload-capable API directly to the public internet. Use Tailscale or another private network boundary, and keep any public reverse-proxy exposure separately approved.
