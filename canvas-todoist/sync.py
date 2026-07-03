#!/usr/bin/env python3
"""Sync Canvas assignments into Todoist.

Reads the private Canvas Calendar Feed (ICS) — no Canvas API token needed —
and creates/updates tasks in a single Todoist project, one label per course.

Sync semantics:
  - New assignments become tasks (due date, link + description, course label).
  - Due-date/title changes update the existing task.
  - Tasks you completed in Todoist are never recreated or reopened.
  - Assignments with no due date never appear in the feed and are not synced.

State lives in /data/state.json (canvas UID -> todoist task id + content hash)
so re-runs are idempotent even after tasks are completed.
"""

import argparse
import hashlib
import html
import json
import logging
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from icalendar import Calendar

TODOIST_API = "https://api.todoist.com/api/v1"
MARKER_PREFIX = "canvas_id:"
DESCRIPTION_LIMIT = 1500  # keep well under Todoist's 16k description cap

log = logging.getLogger("canvas-todoist")


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        log.error("Missing required environment variable %s", name)
        sys.exit(2)
    return value


def strip_html(text):
    text = html.unescape(text)  # Canvas sometimes entity-encodes the HTML
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>\s*", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


class Assignment:
    def __init__(self, uid, title, course, due, url, description):
        self.uid = uid
        self.title = title
        self.course = course
        self.due = due  # datetime (aware, UTC) or date
        self.url = url
        self.description = description

    @property
    def label(self):
        # Todoist labels can't contain spaces or @; "MATH 3321" -> "MATH-3321"
        slug = re.sub(r"[^A-Za-z0-9]+", "-", self.course).strip("-")
        return slug or "Canvas"

    @property
    def todoist_description(self):
        parts = [self.url] if self.url else []
        if self.description:
            parts.append(self.description[:DESCRIPTION_LIMIT])
        parts.append(f"{MARKER_PREFIX} {self.uid}")
        return "\n\n".join(parts)

    def due_payload(self):
        if isinstance(self.due, datetime):
            return {"due_datetime": self.due.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        return {"due_date": self.due.isoformat()}

    def content_hash(self):
        blob = json.dumps([self.title, self.course, str(self.due), self.url,
                           self.description[:DESCRIPTION_LIMIT]])
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


def parse_feed(ics_bytes, past_due_days):
    """Extract assignment entries from a Canvas calendar feed."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=past_due_days)
    assignments = []
    cal = Calendar.from_ical(ics_bytes)
    for event in cal.walk("VEVENT"):
        uid = str(event.get("UID", ""))
        if "assignment" not in uid:
            continue  # skip plain calendar events

        summary = strip_html(str(event.get("SUMMARY", "")))
        # Canvas format: "Assignment title [Course Name]"
        match = re.match(r"^(.*)\s+\[([^\]]+)\]\s*$", summary)
        title, course = (match.group(1), match.group(2)) if match else (summary, "Canvas")

        dtstart = event.get("DTSTART")
        if dtstart is None:
            continue
        due = dtstart.dt
        due_as_dt = due if isinstance(due, datetime) else datetime.combine(
            due, datetime.min.time(), tzinfo=timezone.utc)
        if due_as_dt.tzinfo is None:
            due_as_dt = due_as_dt.replace(tzinfo=timezone.utc)
            due = due_as_dt
        if due_as_dt < cutoff:
            continue

        url = str(event.get("URL", "")) or ""
        description = strip_html(str(event.get("DESCRIPTION", "")))
        assignments.append(Assignment(uid, title.strip(), course.strip(), due, url, description))
    return assignments


class Todoist:
    def __init__(self, token, dry_run=False):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.dry_run = dry_run

    def _request(self, method, path, **kwargs):
        resp = self.session.request(method, f"{TODOIST_API}{path}", timeout=30, **kwargs)
        if resp.status_code == 401:
            log.error("Todoist rejected the API token (401) — regenerate it in "
                      "Todoist Settings > Integrations > Developer and update .env")
            sys.exit(1)
        resp.raise_for_status()
        return resp.json() if resp.text else None

    def _paginate(self, path, params=None):
        params = dict(params or {})
        while True:
            page = self._request("GET", path, params=params)
            yield from page.get("results", [])
            cursor = page.get("next_cursor")
            if not cursor:
                return
            params["cursor"] = cursor

    def ensure_project(self, name):
        for project in self._paginate("/projects"):
            if project["name"].lower() == name.lower():
                return project["id"]
        if self.dry_run:
            log.info("[dry-run] would create project %r", name)
            return None
        project = self._request("POST", "/projects", json={"name": name})
        log.info("Created Todoist project %r", name)
        return project["id"]

    def active_tasks(self, project_id):
        if project_id is None:
            return []
        return list(self._paginate("/tasks", {"project_id": project_id}))

    def completed_uids(self, project_id):
        """Map canvas UID -> task id for recently completed tasks (last ~90 days)."""
        if project_id is None:
            return {}
        now = datetime.now(timezone.utc)
        completed = {}
        for task in self._paginate("/tasks/completed/by_completion_date", {
            "project_id": project_id,
            "since": (now - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "until": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }):
            uid = marker_uid(task.get("description"))
            if uid:
                completed[uid] = task["id"]
        return completed

    def create_task(self, assignment, project_id):
        payload = {
            "content": assignment.title,
            "description": assignment.todoist_description,
            "project_id": project_id,
            "labels": [assignment.label],
            **assignment.due_payload(),
        }
        if self.dry_run:
            log.info("[dry-run] would create task %r due %s (%s)",
                     assignment.title, assignment.due, assignment.label)
            return None
        task = self._request("POST", "/tasks", json=payload)
        log.info("Created task %r due %s (%s)", assignment.title, assignment.due, assignment.label)
        return task["id"]

    def update_task(self, task_id, assignment):
        payload = {
            "content": assignment.title,
            "description": assignment.todoist_description,
            "labels": [assignment.label],
            **assignment.due_payload(),
        }
        if self.dry_run:
            log.info("[dry-run] would update task %r due %s", assignment.title, assignment.due)
            return
        self._request("POST", f"/tasks/{task_id}", json=payload)
        log.info("Updated task %r due %s", assignment.title, assignment.due)


def load_state(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def marker_uid(description):
    match = re.search(rf"{MARKER_PREFIX}\s*(\S+)", description or "")
    return match.group(1) if match else None


def sync(args):
    if args.ics_file:
        ics_bytes = Path(args.ics_file).read_bytes()
    else:
        ics_url = env("CANVAS_ICS_URL", required=True)
        resp = requests.get(ics_url, timeout=30)
        if resp.status_code == 404:
            log.error("Canvas feed returned 404 — the Calendar Feed URL was likely "
                      "regenerated; copy the new one from Canvas > Calendar and update .env")
            sys.exit(1)
        resp.raise_for_status()
        ics_bytes = resp.content

    past_due_days = int(env("PAST_DUE_DAYS", "3"))
    assignments = parse_feed(ics_bytes, past_due_days)
    log.info("Feed contains %d assignment(s) within the sync window", len(assignments))

    todoist = Todoist(env("TODOIST_API_TOKEN", required=True), dry_run=args.dry_run)
    project_id = todoist.ensure_project(env("TODOIST_PROJECT", "School"))

    state_path = Path(env("STATE_FILE", "/data/state.json"))
    state = load_state(state_path)

    # Rebuild mappings from task markers in case the state file was lost.
    active_by_id = {}
    for task in todoist.active_tasks(project_id):
        active_by_id[task["id"]] = task
        uid = marker_uid(task.get("description"))
        if uid and uid not in state:
            state[uid] = {"task_id": task["id"], "hash": ""}
    completed = todoist.completed_uids(project_id)

    created = updated = 0
    for assignment in assignments:
        entry = state.get(assignment.uid)
        new_hash = assignment.content_hash()
        if entry is None:
            if assignment.uid in completed:
                # done in Todoist but missing from state (e.g. state file lost)
                state[assignment.uid] = {"task_id": completed[assignment.uid], "hash": new_hash}
                continue
            task_id = todoist.create_task(assignment, project_id)
            state[assignment.uid] = {"task_id": task_id, "hash": new_hash}
            created += 1
        elif entry.get("hash") != new_hash:
            if entry.get("task_id") in active_by_id:
                todoist.update_task(entry["task_id"], assignment)
                updated += 1
            # completed/deleted tasks are left alone
            state[assignment.uid]["hash"] = new_hash

    if not args.dry_run:
        save_state(state_path, state)
    log.info("Sync done: %d created, %d updated, %d unchanged",
             created, updated, len(assignments) - created - updated)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="run a single sync and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="log planned Todoist changes without writing anything")
    parser.add_argument("--ics-file", help="parse a local .ics file instead of fetching CANVAS_ICS_URL")
    args = parser.parse_args()

    if args.once or args.dry_run or args.ics_file:
        sync(args)
        return

    interval = int(env("SYNC_INTERVAL", "3600"))
    while True:
        try:
            sync(args)
        except Exception as exc:
            log.error("Sync failed (%s); retrying in %ds", exc, interval)
        time.sleep(interval)


if __name__ == "__main__":
    main()
