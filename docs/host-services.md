# Host Services (workstation daemons)

Custom daemons that run on the Fedora workstation (not in Portainer) are managed as **systemd user services** and viewed in [Cockpit](../cockpit/README.md) (Services, User toggle).

Checklist for any new custom daemon:

1. Ship the unit in the project at `systemd/<name>.service` (`Restart=on-failure`, optional `EnvironmentFile=-%h/.config/<name>.env`).
2. Register it with `cockpit/register-user-service.sh <unit>`; it then appears in Cockpit automatically.
3. Keep secrets out of the repo (mode-600 env file, originals in Bitwarden Secrets).
4. Record the inventory of running daemons in your private notes, not in this public repo.
