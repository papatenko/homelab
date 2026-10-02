# Cockpit (workstation host UI)

[Cockpit](https://cockpit-project.org/) is a host-level web UI, not a container stack, so it does **not** deploy through Portainer. It gives a browser view of status, logs, and start/stop/restart for the workstation's systemd **user** services (Services page, System/User toggle; user-unit support since Cockpit 257, user logs since 284).

It is installed by script on the Fedora workstation and bound to the **Tailscale IP and localhost only**. Cockpit logs in with Linux credentials and offers a root-capable terminal, so never expose it on the LAN, NPM, public DNS, port forwarding, or Tailscale Funnel.

## Install / re-apply

```bash
cockpit/install.sh
```

Idempotent. It installs `cockpit-system` and `cockpit-ws` with `dnf` (via `pkexec`), writes a `cockpit.socket` drop-in that listens on `127.0.0.1:9090` and the current Tailscale IPv4 address (`FreeBind=yes`, so it still starts before Tailscale is up), enables the socket, and registers every unit in `register-user-service.sh`'s search roots. Re-run it if the Tailscale IP changes.

Open `https://<tailscale-ip>:9090`, log in as your Linux user, open **Services**, and switch the toggle to **User**.

## Standard for custom daemons

Every custom long-running service we write ships a unit at `<project>/systemd/<name>.service` and is registered with:

```bash
cockpit/register-user-service.sh <path/to/name.service>
```

That symlinks the unit into `~/.config/systemd/user/`, reloads, and enables and starts it. Because it lives in the user manager, it appears in Cockpit's User view automatically, with logs and restart controls. Do not run daemons from ad-hoc terminals, tmux, or `nohup`.

Unit conventions: `Restart=on-failure`, `RestartSec`, secrets via `EnvironmentFile=-%h/.config/<name>.env` (mode 600, never in the repo), and `PartOf=graphical-session.target` for desktop-bound daemons.

See also [`../docs/host-services.md`](../docs/host-services.md).
