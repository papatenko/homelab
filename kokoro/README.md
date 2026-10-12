# Kokoro-82M CPU pilot

A private, CPU-only pilot of [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) using the upstream [Kokoro-FastAPI](https://github.com/remsky/Kokoro-FastAPI) CPU image.

## Scope and boundary

- Fixed upstream voices only. The default is `am_michael`, a male English voice identifier. It is not represented as Russian-accented.
- The service has no configured application API authentication. Keep it private, with access restricted by the deployment network boundary. Do not publish it through a public proxy.
- One Uvicorn worker processes synthesis requests sequentially. The initial ceiling is 2 CPUs, 4 GiB RAM, and 256 PIDs.
- Model files persist at `${DATA_DIR}/models`, outside the Portainer Git checkout.

## Portainer variables

Create the Git-backed stack from `kokoro/docker-compose.yml` and enter the values from `example.env` in Portainer. Set `DATA_DIR` to a durable NAS path. The listener defaults to loopback. Assign a separately approved private bind address only when an authorized client needs network access. Do not store host details or secrets in Git.

The stack follows the upstream CPU image by default. A tested explicit image version may be entered in Portainer for rollback. The stack uses upstream `GET /health` for container health.

## API smoke test

After Portainer reports a healthy container, verify the private endpoint with an actual synthesis request:

```bash
curl -fsS -X POST http://<private-host>:<port>/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{"model":"kokoro","input":"Hello from the private Kokoro pilot.","voice":"am_michael","response_format":"wav"}' \
  -o kokoro-am-michael.wav
```

Also verify `GET /health`, inspect the container's resource use, and confirm files exist beneath the configured `${DATA_DIR}/models` path. Keep an audio listening review separate from technical validation. Do not claim an accent or a subjective voice quality without listening.

## Rollback

Stop and remove the Git-backed Portainer stack. The persistent model directory is retained so a later redeploy does not need to download it again. Remove it only after an explicit decision to discard the cached model data.
