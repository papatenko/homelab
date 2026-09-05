# Monitoring matrix

This document is the implementation hand-off for the proposed Uptime Kuma and
Healthchecks.io coverage. It is intentionally a **candidate inventory**, not a
claim that any monitor or check has been created. The coordinator must perform
live confirmation before entering private hostnames, IP addresses, ports,
paths, credentials, or Healthchecks identifiers.

## Scope and evidence

- The monitoring host role is the Raspberry Pi (`raspi`). Discovery found it
  on ARM64 Linux with Docker, local NVMe, and reachability to the NAS,
  Services, Hermes, and Proxmox roles by ping.
- The Docker-host ping was unavailable during discovery. Treat Docker-host
  reachability as a deployment prerequisite; do not mark it healthy from this
  document.
- Existing n8n evidence: `Site Uptime Watchlist` is active, has nine nodes,
  runs every 10 minutes, and records status, HTTP code, failure count, and
  errors in its existing data table. The live workflow/export remains the
  authority for exact targets.
- Existing backup evidence: Backrest has two repositories and existing plans;
  an existing NAS backup checker and NAS rsync service also exist. Their exact
  command names, schedules, and completion semantics require live confirmation.
- Repository endpoint evidence is limited to the existing Homepage service
  definitions. Those definitions use `${HOMEPAGE_VAR_NAS_IP}` and include
  private service ports, but a dashboard link is not proof that an endpoint is
  reachable or suitable for monitoring.

**Status vocabulary:** `candidate` means suitable for review; `confirm` means
live inspection is required; `approved` means the coordinator has confirmed the
route and behavior; `deferred` means explicitly outside this phase.

## Monitor policy

### Uptime Kuma active checks

Uptime Kuma is for active probes from `raspi` to an approved LAN/VPN target.
Each monitor must have a real target URL, TCP address, or ICMP target recorded
in Kuma after live confirmation. Do not replace an unknown endpoint with a
made-up URL. A monitor is healthy only when the probe's configured success
condition passes.

Defaults below are starting points for review, not deployment values:

- **Critical service checks:** 60-second interval, 10-second timeout, 2 retries,
  2 consecutive failures before notification, and 3 consecutive successes for
  recovery. Confirm these values against the final alert-noise review.
- **Standard service checks:** 5-minute interval, 10-second timeout, 2 retries,
  3 consecutive failures before notification, and 2 consecutive successes for
  recovery.
- **Infrastructure reachability:** 2-minute interval, 5-second timeout, 2
  retries, and the same failure/recovery thresholds as critical checks.
- HTTP checks should validate the intended status class (normally 2xx/3xx) and,
  where a documented health endpoint exists, a small stable response marker.
  Avoid authenticated UI pages and destructive/API routes.
- TLS certificate expiry, keyword matching, and redirect behavior are
  separate acceptance criteria. Do not silently add them to a basic uptime
  monitor.

### Healthchecks.io completion/liveness checks

Healthchecks.io is for dead-man's-switch semantics emitted by a producer after
an expected job completes successfully. It is **not** a replacement for Kuma
active checks and it does not prove that a web endpoint is reachable. Producers
must send success only after the command's exit status and post-check validation
pass; failures and timeouts must leave the check late/down.

Use one check per independently scheduled producer/job, with the job's real
schedule and a grace period confirmed from the live scheduler. Do not create
checks for hypothetical jobs, per-container resource usage, or a monitor that
has no producer. Store check URLs/UUIDs only in the approved secret/configuration
path, never in Git, logs, arguments, or chat.

## Uptime Kuma candidate matrix

Group names are stable naming guidance. The `target` column is deliberately
specific about what must be confirmed without asserting a private endpoint.

| Group | Monitor name | Role / service covered | Type | Candidate interval / timeout / retries | Success condition | Status / live confirmation |
|---|---|---|---|---|---|---|
| `01-critical-platform` | `KUMA · NAS · primary reachability` | NAS role | ICMP or TCP | 2m / 5s / 2 | Host responds from `raspi` | Candidate; confirm address and whether ICMP is permitted |
| `01-critical-platform` | `KUMA · Services · primary reachability` | Services role | ICMP or TCP | 2m / 5s / 2 | Host responds from `raspi` | Candidate; confirm address and route |
| `01-critical-platform` | `KUMA · Hermes · primary reachability` | Hermes role | ICMP or TCP | 2m / 5s / 2 | Host responds from `raspi` | Candidate; confirm address and route |
| `01-critical-platform` | `KUMA · Proxmox · management reachability` | Proxmox role | ICMP or TCP | 2m / 5s / 2 | Host responds from `raspi` | Candidate; confirm address and approved management port |
| `01-critical-platform` | `KUMA · Docker host · reachability` | Docker host role | ICMP or TCP | 2m / 5s / 2 | Host responds from `raspi` | Candidate; blocked until the failed discovery ping is explained |
| `02-core-services` | `KUMA · n8n · health` | n8n web service | HTTP(S) | 1m / 10s / 2 | Approved health endpoint returns expected status | Candidate; confirm published route and `/healthz` versus readiness policy |
| `02-core-services` | `KUMA · Portainer · health` | Portainer control plane | HTTP(S) | 1m / 10s / 2 | Approved health/login-free endpoint returns expected status | Candidate; confirm route and self-signed TLS handling; never store credentials |
| `02-core-services` | `KUMA · Nginx Proxy Manager · health` | Reverse proxy role | HTTP(S) or TCP | 1m / 10s / 2 | Approved private listener accepts a probe | Candidate; confirm private listener and avoid public exposure |
| `02-core-services` | `KUMA · Pi-hole · DNS/UI health` | DNS service role | DNS or HTTP(S) | 1m / 10s / 2 | Approved DNS query or health page succeeds | Candidate; confirm resolver address and non-authenticated probe |
| `02-core-services` | `KUMA · Backrest · health` | Backup control plane | HTTP(S) | 5m / 10s / 2 | Approved health/UI route returns expected status | Candidate; confirm route; this does not prove a backup completed |
| `03-nas-services` | `KUMA · NAS · Nextcloud` | Nextcloud service | HTTP(S) | 5m / 10s / 2 | Confirmed status/health route returns expected status | Candidate; confirm route and TLS; do not infer from Homepage alone |
| `03-nas-services` | `KUMA · NAS · Immich` | Immich service | HTTP(S) | 5m / 10s / 2 | Confirmed login-free health route returns expected status | Candidate; confirm route and suitable health path |
| `03-nas-services` | `KUMA · NAS · Jellyfin` | Media service | HTTP(S) | 5m / 10s / 2 | Confirmed landing/health route returns expected status | Candidate; confirm route and auth-free behavior |
| `03-nas-services` | `KUMA · NAS · download services` | Sonarr/Radarr/Prowlarr and related services | HTTP(S) | 5m / 10s / 2 | Each approved service route returns expected status | Candidate; expand only from live n8n watchlist; do not assume Homepage ports are reachable |
| `04-monitoring` | `KUMA · Uptime Kuma · self health` | Kuma itself | HTTP(S) | 1m / 10s / 2 | Local/private Kuma status route succeeds | Candidate; confirm deployment URL after installation |
| `04-monitoring` | `KUMA · ntfy · publish path` | ntfy service | HTTP(S) or TCP | 1m / 10s / 2 | Approved login-free health route succeeds | Candidate; confirm route after deployment; auth topics are not embedded here |

### Critical coverage acceptance

Before enabling alerts or retiring n8n, the coordinator must show that every
live target in the n8n watchlist is represented by one approved Kuma monitor or
has an explicit exception. At minimum, coverage must include the role-level
reachability checks for NAS, Services, Hermes, Proxmox, and Docker host plus the
approved health checks for n8n, Portainer, the reverse proxy, DNS, Backrest, and
any currently watched NAS services. A role with no safe unauthenticated probe
may use TCP/ICMP reachability or remain an explicit exception; do not invent a
health URL.

## Healthchecks.io free-tier check inventory

This inventory separates job completion checks from Kuma's active probes. It is
not a quota claim. The coordinator must confirm the current Healthchecks.io
free-tier capacity and the existing account's available slots before creating
anything. If capacity is insufficient, prioritize the rows marked critical and
record the remainder as deferred rather than creating untracked checks.

| Priority | Proposed check name | Producer/job | Expected cadence / grace | Success event | Failure semantics | Status / confirmation |
|---|---|---|---|---|---|---|
| P0 | `HC · NAS backup checker` | Existing NAS backup checker | Confirm live scheduler | Send only after checker exits successfully and validates its result | No success ping on error; late/down after grace | Candidate; confirm command, schedule, and account slot |
| P0 | `HC · NAS rsync` | Existing NAS rsync service | Confirm live scheduler | Send only after rsync and post-copy validation succeed | No success ping on partial/error result | Candidate; confirm unit/timer and account slot |
| P0 | `HC · Backrest repository 1` | Existing Backrest plan/repository 1 | Confirm live Backrest plan schedule | Send only after plan completion and repository result are verified | Late/down on failed, cancelled, or unverified run | Candidate; identify plan/repository live; do not guess names |
| P0 | `HC · Backrest repository 2` | Existing Backrest plan/repository 2 | Confirm live Backrest plan schedule | Send only after plan completion and repository result are verified | Late/down on failed, cancelled, or unverified run | Candidate; identify plan/repository live; do not guess names |
| P0 | `HC · NAS · host heartbeat` | NAS host liveness producer | Confirm deployed timer; set grace above normal reboot duration | Send only after the local liveness command and post-check succeed | Late/down when NAS, LAN egress, or timer is unavailable | Candidate; confirm producer installation and account slot |
| P0 | `HC · Raspberry Pi · host heartbeat` | Raspberry Pi host liveness producer | Confirm deployed timer; set grace above normal reboot duration | Send only after the local liveness command and post-check succeed | Late/down when Pi, site egress, or timer is unavailable | Candidate; external receiver covers loss of the in-home monitor host |
| P0 | `HC · Services · host heartbeat` | Services host liveness producer | Confirm deployed timer; set grace above normal reboot duration | Send only after the local liveness command and post-check succeed | Late/down when host, LAN egress, or timer is unavailable | Candidate; confirm producer installation and account slot |
| P0 | `HC · Hermes · host heartbeat` | Hermes host liveness producer | Confirm deployed timer; set grace above normal reboot duration | Send only after the local liveness command and post-check succeed | Late/down when host, LAN egress, or timer is unavailable | Candidate; confirm producer installation and account slot |
| P0 | `HC · Proxmox · host heartbeat` | Proxmox host liveness producer | Confirm deployed timer; set grace above normal reboot duration | Send only after the local liveness command and post-check succeed | Late/down when hypervisor, LAN egress, or timer is unavailable | Candidate; confirm supported host-local installation and account slot |
| P1 | `HC · Docker host · host heartbeat` | Docker host liveness producer | Confirm reachability and deployed timer before creation | Send only after the local liveness command and post-check succeed | Late/down when host, LAN egress, or timer is unavailable | Blocked until failed discovery reachability is explained |
| P1 | `HC · n8n backup` | Existing n8n backup job, if independently scheduled | Confirm live scheduler | Send only after backup command and artifact validation succeed | Late/down on failure or missing artifact | Conditional candidate; confirm job exists before reserving a slot |

Do not make Healthchecks checks for Kuma monitors, arbitrary containers, CPU/RAM/
disk, or assistant-facing notifications in this phase. A Kuma outage can make
Healthchecks delivery from local producers unreliable; that is expected and is
why the two systems have different purposes. The coordinator should document
the chosen producer egress path and a safe test/recovery procedure without
putting check URLs in this repository.

## n8n parity checklist

The existing workflow and data table are preserved. This checklist is for a
read-only comparison before any unpublish or disable action.

- [ ] Export or inspect the live `Site Uptime Watchlist` workflow without
  printing credentials, webhook tokens, or private values.
- [ ] Confirm the workflow still has nine nodes, runs every 10 minutes, and
  writes status, HTTP code, failure count, and errors to the existing data
  table. Do not delete or recreate that table.
- [ ] Record each watched target by sanitized name and destination class; keep
  exact private URLs in the approved operational system, not in this document.
- [ ] Map every target to an approved Kuma monitor name and group. Mark targets
  with no safe probe as explicit exceptions with an owner and reason.
- [ ] Compare HTTP method, redirect/TLS behavior, status acceptance, timeout,
  retry count, and failure/recovery thresholds. A same-name monitor is not
  parity if its success condition differs.
- [ ] Compare cadence and notification behavior. Kuma's interval/retry policy
  must not create duplicate or materially earlier alerts than the n8n workflow
  without an explicit approval.
- [ ] Confirm Kuma records enough history to replace the n8n status, HTTP code,
  failure count, and error evidence required by the operator.
- [ ] Exercise one safe failure and recovery per monitor class, including an
  approved service-down/recovery test. Do not interrupt a critical service
  without a rollback window and coordinator approval.
- [ ] Confirm Telegram/ntfy routing and deduplication separately. This document
  does not authorize assistant-facing alerts.
- [ ] Keep n8n active until coverage, alert behavior, and recovery evidence are
  reviewed. Only the coordinator may unpublish it after parity is proven.

## Explicitly deferred

The following are outside this matrix and must not be smuggled in as monitor
rows or Healthchecks checks:

- Resource monitoring: CPU, memory, disk, swap, container counts, temperatures,
  and capacity thresholds.
- Zabbix deployment, configuration, agents, templates, and discovery.
- Assistant-facing alerts or conversational notification integrations.
- Public exposure, new proxy/identity routes, and credentialed UI scraping.
- Docker socket access for Uptime Kuma unless separately approved.

## Coordinator hand-off

Before implementation, the coordinator should attach live-only values in the
approved secret/configuration mechanism and record, outside Git, the date,
operator, route confirmation, and reason for each exception. This repository
should retain names, groups, policy defaults, and parity criteria—not secrets or
unverified private endpoints.

## References

- [Homepage service definitions](../homepage/config/services.yaml) — source of
  candidate service names/ports only; not proof of endpoint reachability.
- [n8n operations README](../n8n/README.md) — repository-level health endpoint
  and backup context; the live workflow remains authoritative for watchlist
  targets.
- Coordinator scope: `/root/.hermes/plans/2026-09-04_234500-monitoring-implementation-scope.md`
  — ownership constraints supplied to the implementation agent; it is outside
  this repository and is intentionally not linked as a repository file.
- [Uptime Kuma documentation](https://github.com/louislam/uptime-kuma/wiki)
- [Healthchecks.io documentation](https://healthchecks.io/docs/)
