# NeuTTS API

A CPU-first, on-device HTTP service for [NeuTTS](https://github.com/neuphonic/neutts). The Git-backed stack keeps model processes warm and exposes narrow authenticated endpoints for trusted LAN or VPN integrations.

It contains two independent services:

- **NeuTTS-2E** on port `8055`: the existing fixed-speaker service, with `emily`, `paul`, `sophie`, and `steven` plus emotion controls.
- **NeuTTS-Air** on port `8056`: reference-audio enrollment and synthesis for authorized custom voices.

The services are deliberately separate. Enabling NeuTTS-Air does not change Hermes' existing Paul configuration or interrupt the fixed-speaker endpoint.

## Requirements

- Linux `amd64` host with Docker Compose support.
- Enough RAM for the configured `NEUTTS_MEMORY_LIMIT` and the host's other applications.
- Docker BuildKit access on the NAS for the one-time native image build. Portainer then deploys the prebuilt image without invoking its remote BuildKit integration.

## Custom-voice consent boundary

Only enroll reference audio where the caller has the right and explicit permission to create the voice model. Enrollment requires an external consent-record ID, which must reference the operator's durable authorization record. The operator remains responsible for ensuring that record is accurate, accessible, and retained for the required period.

Do not use copyrighted performer or character clips without rights and consent.

The server accepts only clean speech reference material meeting these constraints:

- WAV, mono, 16 to 44.1 kHz
- 3 to 15 seconds long
- At most 10 MiB by default
- Accurate matching transcript supplied as `reference_text`

Raw uploaded audio is staged only in a bounded container `tmpfs` while encoding and is deleted on normal completion. It is not written to the persistent service-data mount. The persistent catalog stores derived reference codes, the transcript, and the external consent-record ID. It does not retain raw reference audio. The Air catalog is isolated in its own mounted `/data/voices` directory.

## Configuration

Use `example.env` as the list of Portainer stack variables. Do not commit a real `.env` file.

### Fixed speakers

- `DATA_DIR`: persistent fixed-speaker model cache, default `/opt/stacks/neutts`.
- `COMPOSE_PORT_HTTP`: fixed-speaker host port, default `8055`.
- `NEUTTS_API_KEY`: required bearer token for all protected endpoints.
- `NEUTTS_SPEAKER`, `NEUTTS_EMOTION`, and `NEUTTS_MAX_TEXT_CHARS`: fixed-speaker behavior.
- `NEUTTS_CPU_LIMIT`, `NEUTTS_CPU_THREADS`, `NEUTTS_MEMORY_LIMIT`, and `NEUTTS_PIDS_LIMIT`: fixed-speaker resource limits.

### NeuTTS-Air custom voices

- `NEUTTS_AIR_DATA_DIR`: dedicated persistent Air model cache and derived-voice catalog, default `/opt/stacks/neutts-air`.
- `NEUTTS_AIR_ADMIN_API_KEY`: management credential for voice enrollment, inventory, and deletion. Keep it out of synthesis clients.
- `NEUTTS_AIR_SYNTHESIS_API_KEY`: restricted credential for custom-voice synthesis only.
- `NEUTTS_AIR_TMPFS_SIZE`: bounded transient upload workspace, default `12m`.
- `COMPOSE_PORT_AIR_HTTP`: custom-voice host port, default `8056`.
- `NEUTTS_AIR_BACKBONE_REPO`: defaults to `neuphonic/neutts-air`.
- `NEUTTS_AIR_CODEC_REPO`: defaults to `neuphonic/neucodec`, which can encode new reference audio. Do not substitute the decoder-only ONNX codec for enrollment.
- `NEUTTS_AIR_MAX_REFERENCE_BYTES`, `NEUTTS_AIR_MIN_REFERENCE_SECONDS`, and `NEUTTS_AIR_MAX_REFERENCE_SECONDS`: enrollment guardrails.
- `NEUTTS_AIR_CPU_LIMIT`, `NEUTTS_AIR_CPU_THREADS`, `NEUTTS_AIR_MEMORY_LIMIT`, and `NEUTTS_AIR_PIDS_LIMIT`: Air resource limits.

The first start downloads the Air model into `${DATA_DIR}/data/huggingface` and may take several minutes. The startup health-check grace period is ten minutes. Keep the current fixed-speaker service and its data path until Air passes an authenticated real synthesis test.

## API

`GET /healthz` is deliberately unauthenticated for Docker health checks. Air voice enrollment, inventory, and deletion require `NEUTTS_AIR_ADMIN_API_KEY`. Custom-voice synthesis requires `NEUTTS_AIR_SYNTHESIS_API_KEY`.

### Fixed-speaker service, port 8055

- `GET /v1/models`
- `POST /v1/audio/speech`

```json
{
  "model": "neutts-2e",
  "input": "Hello from local speech synthesis.",
  "voice": "paul",
  "emotion": "happy",
  "response_format": "wav"
}
```

### Custom-voice service, port 8056

- `GET /v1/models`
- `GET /v1/voices`
- `POST /v1/voices`
- `DELETE /v1/voices/{voice_id}`
- `POST /v1/audio/speech`

Enroll with `multipart/form-data` fields:

- `reference_audio`: authorized WAV file
- `reference_text`: exact transcript of the reference speech
- `consent_record_id`: durable external record ID demonstrating the operator's authorization

The enrollment response contains an opaque `voice_...` identifier. Use it for synthesis:

```json
{
  "model": "neutts-air",
  "input": "Hello from an approved custom voice.",
  "voice": "voice_REPLACE_WITH_ENROLLMENT_ID",
  "response_format": "wav"
}
```

Deleting a voice ID removes its derived reference codes and catalog metadata. Deletion cannot recover raw reference audio because it was never stored.

This stack deliberately separates image construction from service deployment. Portainer CE's remote agent BuildKit path can be unavailable even when native Docker builds work correctly on the target host.

1. On the NAS, build the tagged image from the checked-out repository:

   ```bash
   cd /home/justink/homelab/neutts
   docker compose -f docker-compose.yml -f docker-compose.build.yml build neutts
   ```

2. In Portainer, create a Git-backed stack from `neutts/docker-compose.yml` only. Do **not** add `docker-compose.build.yml` to the stack. The default `neutts` and `neutts-air` container names are used for the production stack. For a temporary side-by-side migration, override both `*_CONTAINER_NAME` values and both published ports, verify the replacement, then retire the old stack before restoring the defaults.
3. Supply the stack variables, especially a strong `NEUTTS_API_KEY`, then deploy. Keep the API LAN or VPN-only unless a separately approved reverse-proxy design is in place.

Git updates can continue to manage Compose configuration. When an update changes `Dockerfile`, `app.py`, or Python dependencies, rebuild the tagged image on NAS before redeploying the stack.

1. Commit and merge the GitOps change first.
2. In Portainer, preserve the existing stack variables and add the non-secret `NEUTTS_AIR_*` limits only if different from defaults. Keep `NEUTTS_API_KEY` value in Portainer, never Git.
3. Pull and redeploy the configured Git stack.
4. Verify fixed-speaker `/healthz` on port `8055` remains healthy.
5. Verify Air `/healthz` on port `8056` reports `model_loaded: true`.
6. Verify unauthenticated `/v1/models` requests receive `401` on both ports.
7. Enroll only a consented test voice, synthesize a short WAV from its returned ID, then delete that test ID.
8. Confirm both containers remain healthy within their CPU, memory, and PID limits.

## Rollback

Stop or remove only the `neutts-air` service if it fails verification. The existing `neutts` fixed-speaker service, its consumer configuration, and the shared model cache remain available. Preserve `${DATA_DIR}` until a tested replacement is running.
