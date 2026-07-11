# Whisper

Self-hosted, OpenAI-compatible Whisper speech-to-text API using the `small` model by default.

## What it runs

- Image: `hwdsl2/whisper-server`
- Runtime: `faster-whisper`
- Model: `small`
- Internal HTTP port: `9000`
- Persistent data/cache: `${DATA_DIR:-/opt/stacks/whisper}/data`
- OpenAI-compatible endpoints:
  - `POST /v1/audio/transcriptions`
  - `POST /v1/audio/translations`
  - `GET /v1/models`

The model is downloaded into the data volume on first startup, so the first boot can take longer.

## Portainer variables

Copy `example.env` into Portainer stack environment variables and adjust as needed:

```env
DATA_DIR=/opt/stacks/whisper
WHISPER_IMAGE=hwdsl2/whisper-server:latest
WHISPER_MODEL=small
WHISPER_LANGUAGE=auto
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_THREADS=2
WHISPER_LOG_LEVEL=INFO
WHISPER_DISABLE_USAGE_COUNTS=1
WHISPER_API_KEY=TOKEN_HERE
COMPOSE_PORT_HTTP=9000
```

## Remote access

Publish only the HTTP port internally, then expose it through your reverse proxy for HTTPS remote access. Recommended production shape:

1. Deploy this stack on the chosen Docker host.
2. Point your reverse proxy upstream at `http://<docker-host>:${COMPOSE_PORT_HTTP}`.
3. Require a bearer token with `WHISPER_API_KEY` if the endpoint is reachable from the public internet.

Do not expose this unauthenticated API directly to the public internet. Whisper transcription can be CPU-heavy and accepts file uploads.

## API usage

After deployment:

- API docs: `http://<host>:9000/docs`
- OpenAI-compatible base URL: `http://<host>:9000/v1`
- Transcribe endpoint: `POST /v1/audio/transcriptions`

Example:

```bash
curl 'http://<host>:9000/v1/audio/transcriptions' \
  -F 'file=@sample.wav' \
  -F 'model=whisper-1' \
  -F 'language=en' \
  -F 'response_format=json'
```

If `WHISPER_API_KEY` is set, include it as a bearer token in the `Authorization` header.

For OpenAI-compatible GUI clients, use:

```text
Base URL: https://<your-whisper-host>/v1
API key: <WHISPER_API_KEY>
Model: whisper-1
```
