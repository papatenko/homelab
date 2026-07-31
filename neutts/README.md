# NeuTTS API

A GPU-backed, on-device HTTP service for [NeuTTS](https://github.com/neuphonic/neutts). The stack keeps the model loaded after startup and exposes a narrow OpenAI-compatible speech route for trusted local integrations.

This stack uses the English **NeuTTS-2E** model. It offers four built-in speakers (`emily`, `paul`, `sophie`, `steven`) and seven emotions. It does not expose arbitrary voice cloning through the HTTP API.

## Upstream

- [NeuTTS source and model documentation](https://github.com/neuphonic/neutts)
- [NeuTTS-2E model](https://huggingface.co/neuphonic/neutts-2e)
- [NeuCodec model](https://huggingface.co/neuphonic/neucodec)

## Requirements

- Linux `amd64` host with an NVIDIA GPU.
- NVIDIA driver and NVIDIA Container Toolkit configured for Docker.
- Enough GPU memory for the model plus any other GPU workloads.
- Docker BuildKit access from the Portainer Git stack, because this service image is built from `Dockerfile`.

The container intentionally fails at startup when CUDA is unavailable. Set `NEUTTS_REQUIRE_GPU=0` only for a deliberate CPU fallback.

## Configuration

Copy `example.env` into Portainer stack variables. Do not commit a real `.env` file.

- `DATA_DIR`: persistent Hugging Face model cache, default `/opt/stacks/neutts`.
- `COMPOSE_PORT_HTTP`: published HTTP port, default `8055`.
- `NEUTTS_API_KEY`: optional bearer token for API requests. Leave unset only on a trusted LAN or VPN path.
- `NEUTTS_SPEAKER`: default voice, one of `emily`, `paul`, `sophie`, or `steven`.
- `NEUTTS_EMOTION`: default emotion, one of `angry`, `disgusted`, `fearful`, `happy`, `neutral`, `sad`, or `surprised`.
- `NEUTTS_MAX_TEXT_CHARS`: input guardrail, default `2000`.

The first launch downloads the model into `${DATA_DIR}/data/huggingface`. It will take longer than later restarts.

## API

The service provides:

- `GET /healthz`, no authentication, returns model and CUDA readiness.
- `GET /v1/models`, bearer authentication if `NEUTTS_API_KEY` is set.
- `POST /v1/audio/speech`, bearer authentication if `NEUTTS_API_KEY` is set.

`POST /v1/audio/speech` accepts the OpenAI request shape below. This implementation currently returns PCM WAV only.

```json
{
  "model": "neutts-2e",
  "input": "Hello from local speech synthesis.",
  "voice": "emily",
  "emotion": "happy",
  "response_format": "wav"
}
```

For protected deployments, send a bearer token that matches `NEUTTS_API_KEY`.

## Portainer deployment

Create a Git-backed stack using `neutts/docker-compose.yml` after this PR is merged. Enable Git updates only after the stack variables have been supplied. Keep the API LAN or VPN-only unless a separately approved reverse-proxy and authentication design is in place.

## Validation and rollback

Before deployment, validate the Compose file and review the diff for secrets. After deployment, confirm the container is healthy, `GET /healthz` reports `cuda: true`, and a short authenticated or trusted-network WAV request succeeds.

To roll back, stop and remove the stack. Keep `${DATA_DIR}` until a replacement has been tested, so model cache downloads are recoverable.
