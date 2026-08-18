"""Todoist adapter — capture-only Inbox, drained to zero.

The drain's primitive is **file, not complete** (Daniel's explicit rule):
task-typed items are *moved* to a curated project and stay OPEN; close-with-
comment is reserved for non-task captures whose content transferred to a
better-tracked spine. Nothing outside the Inbox is ever mutated except the
propose-only stale sweep (digest listing only). Nothing is ever deleted.

Uses the unified API ``https://api.todoist.com/api/v1/`` (REST v2 is HTTP 410
Gone). :class:`TodoistClient` is the network seam; tests inject a fake.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config

_API = "https://api.todoist.com/api/v1/"
UNCLEAR_LABEL = "mailroom-unclear"


class TodoistError(RuntimeError):
    pass


class TodoistClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("TODOIST_API_TOKEN", "")

    # ---- transport -------------------------------------------------------- #
    def _request(self, method: str, path: str, *, params=None, payload=None) -> dict:
        url = _API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": f"Bearer {self.token}"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read()
                    return json.loads(raw) if raw.strip() else {}
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 3:
                    time.sleep(int(e.headers.get("Retry-After", "1")) + 1)
                    continue
                detail = ""
                try:
                    detail = e.read().decode()[:200]
                except Exception:
                    pass
                raise TodoistError(f"HTTP {e.code} {method} {path}: {detail}") from e
        raise TodoistError("ratelimited (gave up)")

    def _paginate(self, path: str, **params) -> list[dict]:
        out, cursor = [], None
        while True:
            p = dict(params)
            if cursor:
                p["cursor"] = cursor
            body = self._request("GET", path, params=p)
            out.extend(body.get("results", []))
            cursor = body.get("next_cursor")
            if not cursor:
                return out

    # ---- read ------------------------------------------------------------- #
    def projects(self) -> list[dict]:
        return self._paginate("projects")

    def tasks(self, project_id: str) -> list[dict]:
        return self._paginate("tasks", project_id=project_id)

    def inbox_tasks(self) -> list[dict]:
        return self.tasks(config.TODOIST_INBOX_ID)

    # ---- write (Inbox drain) --------------------------------------------- #
    def move(self, task_id: str, project_id: str) -> None:
        self._request("POST", f"tasks/{task_id}/move", payload={"project_id": project_id})

    def close(self, task_id: str) -> None:
        self._request("POST", f"tasks/{task_id}/close", payload={})

    def comment(self, task_id: str, content: str) -> None:
        self._request("POST", "comments", payload={"task_id": task_id, "content": content})

    def add_label(self, task_id: str, task: dict, label: str = UNCLEAR_LABEL) -> None:
        labels = list(task.get("labels") or [])
        if label not in labels:
            labels.append(label)
        self._request("POST", f"tasks/{task_id}", payload={"labels": labels})

    def create_task(self, content: str, *, project_id: str, description: str = "") -> dict:
        payload = {"content": content, "project_id": project_id}
        if description:
            payload["description"] = description
        return self._request("POST", "tasks", payload=payload)


def project_name(project_id: str) -> str:
    for name, pid in config.TODOIST_PROJECTS.items():
        if pid == project_id:
            return name
    return project_id


def resolve_project(name: str | None) -> str | None:
    """Map a triage-suggested project name to a curated project id (exact, then
    case-insensitive contains). Returns None if it cannot be placed."""
    if not name:
        return None
    name = name.strip()
    if name in config.TODOIST_PROJECTS:
        return config.TODOIST_PROJECTS[name]
    if name in config.TODOIST_PROJECTS.values():
        return name
    low = name.lower()
    for pname, pid in config.TODOIST_PROJECTS.items():
        if pname.lower() == low or low in pname.lower() or pname.lower() in low:
            return pid
    return None
