# Parakeet-TDT 0.6B v3 CPU pilot

A private, CPU-only side-by-side speech-to-text pilot using NVIDIA's Parakeet-TDT 0.6B v3 through NeMo-Speech.cpp.

## Scope

- It does **not** replace or disable the current Whisper service.
- The API is loopback-only by default and uses the existing OpenAI-compatible multipart route: `POST /v1/audio/transcriptions` with `model` and `file`, returning JSON with `text`.
- It runs one bounded HTTP worker, capped at 2 CPUs, 2 GiB RAM, and 256 PIDs.
- Persistent runtime binaries and the Q8 model cache are at `${DATA_DIR}`, outside the Portainer Git checkout. Set it to the approved durable NAS path in Portainer.
- The Q8 model artifact is approximately 714 MB. NeMo-Speech.cpp and the model are downloaded once into persistent storage, validated by the runtime, then reused.

## Deployment

Create a Git-backed Portainer stack from `parakeet/docker-compose.yml`. Enter values from `example.env` as Portainer environment variables. Keep the listener on loopback until an explicitly approved private integration path is available. Do not add a public proxy.

## Validation

Verify all layers before considering a client switch:

1. The Portainer stack is Git-backed and the container is healthy.
2. `GET /health` or `GET /v1/models` succeeds locally in the container.
3. A real multipart `POST /v1/audio/transcriptions` returns non-empty JSON `text`.
4. The persistent data directory includes both the release binary and Parakeet model artifact.
5. Measure cold/warm latency, CPU, resident memory, available RAM, and swap impact while Kokoro remains healthy.
6. Compare representative private recordings with the existing Whisper endpoint before changing Hermes.

## Rollback

Stop and remove the Git-backed Portainer stack. The existing Whisper endpoint is unchanged. Retain `${DATA_DIR}` for a later restart, or remove it only after an explicit decision to discard the downloaded runtime and model.
