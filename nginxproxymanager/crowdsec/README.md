# CrowdSec detection for Nginx Proxy Manager

This stack includes a CrowdSec sidecar in **detection-only** mode.

What it does:

- Reads Nginx Proxy Manager logs from `${DATA_DIR:-/opt/stacks/nginxproxymanager}/data/logs`.
- Installs the `crowdsecurity/nginx-proxy-manager` collection.
- Stores CrowdSec state under `${DATA_DIR:-/opt/stacks/nginxproxymanager}/crowdsec/data`.
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

In Portainer, use the container console for the `crowdsec` service if you are not running the stack from a local shell.
