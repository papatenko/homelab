# Heartbeat producers

These producers wrap an existing host-local job. They do **not** replace or edit
that job. Set `HEARTBEAT_COMMAND` to the existing command and
`HEARTBEAT_VERIFY` to an independent, read-only post-check at runtime.

Included producer entry points:

- `producers/nas-backrest.sh`
- `producers/nas-rsync.sh`
- `producers/hermes-backrest.sh`
- `producers/proxmox.sh`
- `producers/raspberry-pi.sh`
- `producers/services.sh`
- `producers/hermes.sh`
- `producers/docker-host.sh`

Each delegates to `heartbeat.py`, which runs the command, then the post-check,
and only then emits the Healthchecks success ping. A non-zero command,
post-check failure, or timeout emits failure (where configured) and exits
non-zero. Child output is discarded; notification messages contain no command
output or credential values.

## Runtime configuration

Use an owner-only environment source outside Git (systemd credentials, a secret
manager wrapper, or an equivalent approved mechanism):

```sh
HEARTBEAT_COMMAND='/path/to/existing-backup-job'
HEARTBEAT_VERIFY='/path/to/read-only-backup-verification'
HEARTBEAT_TIMEOUT=900
HEALTHCHECKS_SUCCESS_URL='injected-at-runtime'
HEALTHCHECKS_FAILURE_URL='injected-at-runtime'
NTFY_URL='injected-at-runtime'
NTFY_TOPIC='injected-at-runtime'
NTFY_TOKEN='injected-at-runtime'
```

Healthchecks URLs are complete injected endpoints; no URL or token is embedded
in this repository. ntfy is optional and publishes only when both `NTFY_URL`
and `NTFY_TOPIC` are present. The token is sent as an Authorization header and
never appears in arguments or output.

Commands are intentionally shell strings because existing backup jobs may be
local wrappers. They must be supplied by the host administrator and treated as
trusted configuration. Do not put secrets in command strings.

## Backup integration templates

`backup-integrations/heartbeat@.service` and `.timer` are generic systemd
templates. Copy them into the host's reviewed systemd configuration and point
the environment file at a host-local, owner-only file. They are templates only;
this change does not install, enable, or run anything remotely.

Suggested verification commands should be specific to each existing backup
system. Examples (adapt to the installed tool and plan identity):

- NAS Backrest: verify the expected latest snapshot/plan completed.
- NAS rsync: verify destination marker and expected file/list exit status.
- Hermes Backrest: verify the expected latest snapshot/plan completed.

A post-check must be independent enough to catch a command that returned zero
without producing a usable backup. Do not use a success marker written before
the command completes.

## Local checks

```sh
python3 -m py_compile heartbeat.py
python3 -m unittest discover -s tests -v
for script in run-heartbeat.sh producers/*.sh; do sh -n "$script"; done
```
