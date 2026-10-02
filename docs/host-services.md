# Host Services (workstation daemons)

Custom daemons that run on the Fedora workstation (not in Portainer) are managed as **systemd user services** and viewed in [Cockpit](../cockpit/README.md) (Services, User toggle).

Checklist for any new custom daemon:

1. Ship the unit in the project at `systemd/<name>.service` (`Restart=on-failure`, optional `EnvironmentFile=-%h/.config/<name>.env`).
2. Register it with `cockpit/register-user-service.sh <unit>`; it then appears in Cockpit automatically.
3. Keep secrets out of the repo (mode-600 env file, originals in Bitwarden Secrets).
4. Add a row below.

| Service | Purpose | Unit |
|---|---|---|
| `agent-phone-alerts` | Telegram push when non-Claude agents in herdr are blocked or finish | `automation/agent-phone-alerts/systemd/` |
| `aw-herdr-bridge` | herdr panes into ActivityWatch | `automation/activitywatch/systemd/` |
| `awatcher` | ActivityWatch window/AFK watcher | `automation/activitywatch/systemd/` |
| `aw-forward` | ActivityWatch forwarding socket | `automation/activitywatch/systemd/` |
| `omniroute-mcp-tunnel` | OmniRoute MCP tunnel | local unit in `~/.config/systemd/user/` |
