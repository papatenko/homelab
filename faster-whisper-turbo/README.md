# Faster-Whisper large-v3-turbo CPU comparison pilot

Private, reversible NAS comparison service for `large-v3-turbo` using the existing OpenAI-compatible `hwdsl2/whisper-server` image, which is powered by faster-whisper.

## Scope

- This is a side-by-side CPU pilot. It does not change Hermes transcription routing.
- It does not stop, modify, or share storage with Parakeet or the existing Whisper service.
- It binds `127.0.0.1` only by default and exposes `POST /v1/audio/transcriptions` with `model` and `file`, returning JSON text.
- Persistent cache data lives under a dedicated `DATA_DIR`, outside the Git checkout.
- The image is rolling `latest` in line with the homelab's current policy. Validate its observed digest and behavior at deployment time.

## Portainer deployment

Create one Git-backed Portainer stack using `faster-whisper-turbo/docker-compose.yml` from `main`. Copy the non-secret settings in `example.env` into the stack runtime environment. Keep real credentials out of Git. Preserve loopback binding.

Before creation, check the intended loopback port is unused on the NAS. The example uses `18881`, intentionally distinct from Parakeet and existing service listeners.

## Acceptance and rollback

1. Confirm the Portainer stack is Git-backed and container health is `healthy`.
2. Verify `GET /health` returns `status: ok`.
3. Send a real multipart transcription request and require nonempty JSON text.
4. Record model cache persistence, cold and warm latency, peak RSS, CPU, available memory, and swap change while checking Kokoro stays healthy.
5. Compare exactly the same private fixtures with current Parakeet before choosing a default. Evaluate English wording, names/acronyms, punctuation, long notes, and noisy audio.
6. On memory pressure, swap growth, Kokoro degradation, or failed request, stop and remove only this pilot container/stack. Retain Parakeet and existing Whisper untouched.

No routing change follows from a successful smoke test. Justin separately chooses a default after the measured comparison.
