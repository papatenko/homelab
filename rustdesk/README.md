# RustDesk server (hbbs + hbbr)

Self-hosted [RustDesk](https://rustdesk.com/) rendezvous (`hbbs`) and relay (`hbbr`) servers, so remote sessions use a nearby relay instead of RustDesk's public servers.

Upstream docs: <https://rustdesk.com/docs/en/self-host/rustdesk-server-oss/docker/>

## Ports (host networking)

| Port | Proto | Service | Purpose |
| --- | --- | --- | --- |
| 21115 | TCP | hbbs | NAT type test |
| 21116 | TCP + UDP | hbbs | ID registration / heartbeat / hole punching |
| 21117 | TCP | hbbr | Relay |
| 21118 | TCP | hbbs | Web client (optional) |
| 21119 | TCP | hbbr | Web client relay (optional) |

Do not forward these from the internet unless external use is wanted; LAN-only works without any router change.

## Security

`ENCRYPTED_ONLY=1` and `-k _` mean only clients that hold this server's **public** key can connect. The key pair is generated on first start in `${DATA_DIR}/data` (`id_ed25519`, `id_ed25519.pub`). The private key must never be committed or shared; the public key goes into each RustDesk client.

## Deploy (Portainer)

1. Create the data directory on the target host: `install -d -m 700 /opt/stacks/rustdesk/data`.
2. Portainer: add a Git stack on the target endpoint, compose path `rustdesk/docker-compose.yml`.
3. Set variables from `example.env` (`RUSTDESK_RELAY` is required).
4. The image is scratch-based (no shell), so there is no container healthcheck; verify with `docker ps`, `ss -tulnp`, and `nc -zv <host> 21116`.

## Client setup

RustDesk > Settings > Network > ID/Relay server: set **ID server** to the host (relay is advertised by hbbs; fill **Relay server** with the same host), and **Key** to the contents of `id_ed25519.pub`.

## Rollback

Remove the Portainer stack. Data remains in `${DATA_DIR}/data`; delete it only to discard the key pair (all clients would need the new key).
