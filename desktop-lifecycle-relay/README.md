# Desktop Lifecycle Relay

A private, fixed-action relay for weekday desktop power automation.

## Security boundary

The relay implements exactly two actions:

- `wake`: sends one configured Wake-on-LAN magic packet.
- `shutdown`: uses the configured dedicated SSH identity to invoke the fixed Windows command `shutdown /s /t 0`.

It does not accept hostnames, command strings, arguments, shell code, or arbitrary paths from HTTP callers. The only public route is a non-sensitive `/healthz` status response. Bind it only to the n8n Docker gateway or another private interface. Do not reverse-proxy it or expose it publicly.

## Runtime configuration

Install the service configuration from `systemd/` on the LAN-capable host. Create `/etc/desktop-lifecycle-relay/relay.env` with mode `0600`, root ownership, and values delivered through Bitwarden Secrets Manager. Start from `relay.env.example`, but never copy real values into Git, n8n, or Obsidian.

The relay token is sent by n8n only as `Authorization: Bearer <token>`. The n8n workflow must call the relay using its private Docker-gateway address. n8n must retain its Telegram failure path.

## Deployment preflight

1. Verify the dedicated Windows key works from the relay host.
2. Verify the relay host is on the desktop LAN and can emit broadcast UDP.
3. Provision the token and configuration through Bitwarden Secrets Manager.
4. Run unit tests, then install the files and start the unit.
5. Verify `/healthz` and an unauthorized request locally.
6. Keep the n8n workflow disabled until one manually initiated shutdown followed by WOL and SSH-readiness verification succeeds.

## Tests

```bash
python3 -m unittest discover -s desktop-lifecycle-relay/tests -v
python3 -m py_compile desktop-lifecycle-relay/relay.py
```
