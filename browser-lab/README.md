# Browser Lab

Private, persistent Neko Google Chrome browser for the Services host.

## Design

- The derived image is built on the target Docker host from this Git source and
  tagged `browser-lab:8e5d416`; Portainer deploys the Git-backed Compose stack using
  that local artifact because this Portainer endpoint cannot perform remote Compose
  builds reliably.
- Neko uses host networking because WebRTC needs a predictable UDP range.
- The browser profile is mounted from `${DATA_DIR}/profile`.
- Neko's persistent-data policy retains cookies and restores the previous session.
- Extensions remain blocked by default. Bitwarden can be used through its Web Vault
  with manual copy and paste. Extension policy can be revisited separately.

## Target-host image preparation

Run this on the target Docker host from the merged `main` source before the
Portainer stack is created:

```text
git clone --branch main https://github.com/papatenko/homelab.git /tmp/homelab-browser-lab
docker build -t browser-lab:8e5d416 /tmp/homelab-browser-lab/browser-lab
```

The tag is tied to the reviewed source commit. Verify the image exists locally
before creating or redeploying the Portainer stack. A future registry-backed image
can replace this host-local artifact without changing the runtime contract.

## Portainer environment

Set these values in the git-backed Portainer Stack environment. Do not commit real
passwords, tailnet addresses, or host paths to Git:

```text
DATA_DIR=/opt/stacks/browser-lab
NEKO_DESKTOP_SCREEN=1920x1080@30
NEKO_MEMBER_MULTIUSER_USER_PASSWORD=<set-in-portainer>
NEKO_MEMBER_MULTIUSER_ADMIN_PASSWORD=<set-in-portainer>
NEKO_SERVER_BIND=<services-tailscale-ip>:8081
NEKO_WEBRTC_EPR=52000-52100
NEKO_WEBRTC_NAT1TO1=<services-tailscale-ip>
CDP_PORT=9223
CDP_BIND_ADDRESS=<services-tailscale-ip>
```

The initial approved clients are Hermes (`<hermes-tailscale-ip>`) and desktop-wsl
(`<desktop-wsl-tailscale-ip>`). Tailscale ACLs and host firewall rules must restrict access to
those approved clients and the Neko web/CDP ports before deployment.

## Profile preparation

Before first start, create the profile directory and set ownership for Neko's UID:

```text
mkdir -p /opt/stacks/browser-lab/profile
chown -R 1000:1000 /opt/stacks/browser-lab/profile
```

This preparation is a gated host operation and must be performed through the
approved deployment workflow, not as an untracked ad-hoc Compose deployment.

## Verification gates

1. Validate the rendered Compose configuration with all required non-secret values.
2. Build the derived image successfully in the selected Portainer build environment.
3. Confirm the container health check and Neko UI over the Tailscale address.
4. Confirm the UI and CDP ports are not reachable on the LAN address.
5. Confirm CDP `/json/version` responds only through the approved tailnet path.
6. Configure Browser Harness with `BU_CDP_URL=http://<services-tailscale-ip>:9223`.
7. Verify a shared tab action is visible in Neko while Justin watches.
8. Verify a normal site login persists across a controlled container restart.

Do not remove Hermes noVNC as part of this stack's initial deployment. Retire it
only after Browser Lab is validated and a separate approval is given.
