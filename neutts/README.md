# NeuTTS API

A CPU-first, on-device HTTP service for [NeuTTS](https://github.com/neuphonic/neutts). The stack keeps the model loaded after startup and exposes a narrow OpenAI-compatible speech route for trusted local integrations.

This stack uses the English **NeuTTS-2E Q4 GGUF** model with the INT8 ONNX codec decoder. It offers four built-in speakers (`emily`, `paul`, `sophie`, `steven`) and seven emotions. It does not expose arbitrary voice cloning through the HTTP API.

## Upstream

- [NeuTTS source and model documentation](https://github.com/neuphonic/neutts)
- [NeuTTS-2E model](https://huggingface.co/neuphonic/neutts-2e)
- [NeuCodec model](https://huggingface.co/neuphonic/neucodec)

## Requirements

- Linux `amd64` host with Docker Compose support.
- Enough RAM for the configured `NEUTTS_MEMORY_LIMIT` and the host's other applications.
- Docker BuildKit access on the NAS for the one-time native image build. Portainer then deploys the prebuilt image without invoking its remote BuildKit integration.

The default CPU path uses the Q4 GGUF backbone, OpenBLAS, and an INT8 ONNX decoder. It does not require NVIDIA tooling or an iGPU. The container's default two-CPU, 2 GB limit prevents speech jobs from consuming an entire host, at the cost of slower synthesis under load.

## Configuration

Copy `example.env` into Portainer stack variables. Do not commit a real `.env` file.

- `DATA_DIR`: persistent Hugging Face model cache, default `/opt/stacks/neutts`.
- `COMPOSE_PORT_HTTP`: published HTTP port, default `8055`.
- `NEUTTS_API_KEY`: optional bearer token for API requests. Leave unset only on a trusted LAN or VPN path.
- `NEUTTS_CPU_LIMIT`, `NEUTTS_MEMORY_LIMIT`, `NEUTTS_PIDS_LIMIT`: Compose resource ceilings, defaulting to `2.0`, `2g`, and `256`.
- `NEUTTS_CPU_THREADS`: OpenMP/OpenBLAS thread limit, default `2`. The Compose CPU quota remains the final limit on total CPU time.
- `NEUTTS_SPEAKER`: default voice, one of `emily`, `paul`, `sophie`, or `steven`.
- `NEUTTS_EMOTION`: default emotion, one of `angry`, `disgusted`, `fearful`, `happy`, `neutral`, `sad`, or `surprised`.
- `NEUTTS_MAX_TEXT_CHARS`: input guardrail, default `2000`.

The first launch downloads the model into `${DATA_DIR}/data/huggingface`. It will take longer than later restarts. Keep the stack separate from a CPU-based speech-to-text workload when either service must remain responsive during concurrent requests.

## API

The service provides:

- `GET /healthz`, no authentication, returns model, codec, and CPU readiness.
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

This stack deliberately separates image construction from service deployment. Portainer CE's remote agent BuildKit path can be unavailable even when native Docker builds work correctly on the target host.

1. On the NAS, build the tagged image from the checked-out repository:

   ```bash
   cd /home/justink/homelab/neutts
   docker compose -f docker-compose.yml -f docker-compose.build.yml build neutts
   ```

2. In Portainer, create a Git-backed stack from `neutts/docker-compose.yml` only. Do **not** add `docker-compose.build.yml` to the stack.
3. Supply the stack variables, especially a strong `NEUTTS_API_KEY`, then deploy. Keep the API LAN or VPN-only unless a separately approved reverse-proxy design is in place.

Git updates can continue to manage Compose configuration. When an update changes `Dockerfile`, `app.py`, or Python dependencies, rebuild the tagged image on NAS before redeploying the stack.

## Validation and rollback

Before deployment, validate the Compose file and review the diff for secrets. After deployment, confirm the container is healthy, `GET /healthz` reports the expected Q4 backbone and CPU device, and a short authenticated or trusted-network WAV request succeeds.

To roll back, stop and remove the stack. Keep `${DATA_DIR}` until a replacement has been tested, so model cache downloads are recoverable.
