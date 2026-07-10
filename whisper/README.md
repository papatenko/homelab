# Whisper ASR

Self-hosted OpenAI Whisper speech-to-text API using the `small` model by default.

## What it runs

- Image: `onerahmet/openai-whisper-asr-webservice`
- Engine: `openai_whisper`
- Model: `small`
- Internal HTTP port: `9000`
- Persistent cache: `${DATA_DIR:-/opt/stacks/whisper}/cache`

The model is downloaded into the cache volume on first startup, so the first boot can take longer.

## Portainer variables

Copy `example.env` into Portainer stack environment variables and adjust as needed:

```env
DATA_DIR=/opt/stacks/whisper
ASR_MODEL=small
COMPOSE_PORT_HTTP=9000
WHISPER_IMAGE=onerahmet/openai-whisper-asr-webservice:latest
```

## Remote access

Publish only the HTTP port internally, then expose it through your reverse proxy for HTTPS remote access. Recommended production shape:

1. Deploy this stack on the chosen Docker host.
2. Point your reverse proxy upstream at `http://<docker-host>:${COMPOSE_PORT_HTTP}`.
3. Add access control in front of the service if the endpoint is reachable from the public internet.

Do not expose this unauthenticated API directly to the public internet. Whisper transcription can be CPU-heavy and accepts file uploads.

## API usage

After deployment:

- API docs: `http://<host>:9000/docs`
- Transcribe endpoint: `POST /asr`

Example:

```bash
curl -X POST 'http://<host>:9000/asr?task=transcribe&language=en&output=json' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'audio_file=@sample.wav'
```
