# Speaches

Self-hosted multilingual speech-to-text for private dictation, using the official Speaches CUDA image and the NVIDIA GPU exposed by Docker Desktop.

## Deployment shape

- Image: `ghcr.io/speaches-ai/speaches:latest-cuda-12.6.3`
- API port: `8000`
- GPU: NVIDIA CUDA through Docker Compose device reservations
- Preferred model: `deepdml/faster-whisper-large-v3-turbo-ct2`
- Model cache: `${DATA_DIR}/huggingface`
- Access boundary: Tailscale only, with no public reverse proxy in the initial deployment
- Web UI: disabled

The model is preloaded at startup. This keeps dictation latency predictable and keeps the model resident in the 8 GB RTX 2070 VRAM while the service is running.

## Portainer variables

Create the Git-backed stack with the values from `example.env`. For the Windows Docker Desktop endpoint, set `DATA_DIR` to a durable Windows path that is included in the desktop backup plan, using Docker Compose path syntax such as `D:/DockerData/speaches`.

Keep `SPEACHES_API_KEY` in Portainer only. Do not commit it or place it in this repository. The API key is recommended even though the initial route is Tailscale-only.

## Model fallback

Start with `deepdml/faster-whisper-large-v3-turbo-ct2`. If startup logs show CUDA out-of-memory or unacceptable latency, change `PRELOAD_MODELS` to a smaller multilingual CTranslate2 model, such as:

```text
Systran/faster-whisper-small
```

Keep `WHISPER__INFERENCE_DEVICE=cuda` and use `float16` unless the live GPU test shows otherwise.

## Validation

After deployment, verify all layers:

1. Portainer reports the stack as Git-backed and the container is healthy.
2. The container logs show CUDA initialization and the preloaded model.
3. `GET /health` returns HTTP 200 over the Tailscale address.
4. An authenticated `GET /v1/models` returns the loaded model.
5. A short English dictation sample and a short non-English sample complete successfully.
6. GPU memory remains stable during repeated dictation requests.

The OpenAI-compatible base URL for OpenWhispr is:

```text
http://<desktop-tailscale-host>:8000/v1
```

Use model `whisper-1` if the client requires the OpenAI alias. Configure the API key from Portainer in OpenWhispr. Do not expose port 8000 through Nginx Proxy Manager until the private route has been validated and a specific public-access need exists.

## Upstream sources

- Speaches: https://github.com/speaches-ai/speaches
- Installation: https://speaches.ai/installation/
- CUDA Compose reference: https://github.com/speaches-ai/speaches/blob/master/compose.cuda.yaml
- Model discovery: https://github.com/speaches-ai/speaches/blob/master/docs/usage/model-discovery.md
