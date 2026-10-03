# Pi-hole (secondary / replica)

A second, independent Pi-hole resolver kept in sync one-way from the primary
(`../pihole`) by [nebula-sync](https://github.com/lovelaze/nebula-sync). If the
primary goes down, clients that list this resolver as a second DNS server keep
resolving.

## Upstream sources

- Pi-hole Docker: https://github.com/pi-hole/docker-pi-hole
- nebula-sync (Pi-hole v6 only): https://github.com/lovelaze/nebula-sync

## What syncs

Primary -> secondary, hourly by default (`SYNC_CRON`):

- Groups, adlists, domain allow/deny lists, clients and their group links.
- DNS config, which includes local DNS records and CNAMEs.

Deliberately **not** synced (`SYNC_CONFIG_DNS_EXCLUDE`): `upstreams`,
`interface`, `listeningMode`. The secondary uses its own public upstreams
(`DNS_UPSTREAMS`) so it never depends on the primary. Changes made on the
secondary are overwritten; make all edits on the primary.

## Persistent data

`${DATA_DIR:-/opt/stacks/pihole-secondary}/etc-pihole`

## Ports and variables

See `example.env`. DNS is published on host port 53 (tcp/udp). The web UI is
HTTPS on `PIHOLE_WEB_PORT` (default 8453). Host port 53 must be free.

## Notes

- Pi-hole v6 only. Keep primary and secondary on the same Pi-hole version.
- `PRIMARY_URL` must be reachable from the Docker host and is supplied through
  stack variables, not committed.
- Only point DHCP or router DNS at this resolver after verifying it on its own.

## Validation

```bash
docker compose -f pihole-secondary/docker-compose.yml config
dig @<secondary-host> example.com            # resolves
dig @<secondary-host> <local-record-name>    # matches the primary's local DNS record
dig @<secondary-host> <blocked-domain>       # blocked, same as the primary
docker logs nebula-sync                      # shows a successful sync run
```

## Rollback

Remove the Portainer stack. Nothing else depends on it until DHCP/router DNS is
changed; revert that change first if it was made. Delete the data directory only
after explicit confirmation.
