# CrowdSec detection for Nginx Proxy Manager

This stack includes a CrowdSec sidecar in **detection-only** mode.

What it does:

- Reads Nginx Proxy Manager access logs.
- Installs the `crowdsecurity/nginx-proxy-manager` collection.
- Stores CrowdSec state in the stack data directory.
- Produces CrowdSec metrics, alerts, and decisions.

What it does **not** do yet:

- It does not block traffic.
- It does not install a firewall, Nginx, Cloudflare, or other bouncer.

After deployment, verify detection with:

```bash
docker compose exec crowdsec cscli metrics
docker compose exec crowdsec cscli alerts list
docker compose exec crowdsec cscli decisions list
```
