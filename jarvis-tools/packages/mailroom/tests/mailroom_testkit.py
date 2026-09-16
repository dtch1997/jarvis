"""Shared test helpers (constants + fake Slack/Todoist clients).

Kept in a *uniquely-named* module rather than ``conftest`` so a whole-workspace
``pytest packages/*/tests`` run — which puts every ``tests/`` dir on sys.path —
doesn't collide with another package's ``conftest`` (only one top-level
``conftest`` can win). Fixtures still live in ``conftest.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone

NOW = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
CH = "C0B5RUX4P26"
DAN = "U0B17JULMCY"
BOT = "U0BQWRJETGR"


class Env:
    def __init__(self, root, goals, memory):
        self.root = root
        self.goals = goals
        self.memory = memory

    def add_goal(self, slug, body="body"):
        (self.goals / f"{slug}.md").write_text(f"# {slug}\n\n{body}\n")

    def add_memory(self, slug, line="a thing"):
        idx = self.memory / "MEMORY.md"
        prev = idx.read_text() if idx.exists() else "# Memory\n"
        idx.write_text(prev + f"- [{slug}]({slug}.md) — {line}\n")


def slack_msg(ts, *, user=DAN, text="", files=None, bot_id=None, subtype=None,
              thread_ts=None, reply_count=0):
    m = {"ts": ts, "user": user, "text": text}
    if files:
        m["files"] = files
    if bot_id:
        m["bot_id"] = bot_id
    if subtype:
        m["subtype"] = subtype
    if thread_ts:
        m["thread_ts"] = thread_ts
    if reply_count:
        m["reply_count"] = reply_count
        m["thread_ts"] = ts
    return m


class FakeSlack:
    def __init__(self, messages=None, replies=None, files=None):
        self.messages = messages or []
        self._replies = replies or {}
        self.files = files or {}
        self.reactions = []
        self.posts = []

    def history(self, channel, *, oldest="0", limit=200):
        # ignore the real epoch-based ``oldest`` window (test ts are small
        # integers); idempotency is enforced by has_thought, not the cursor.
        return list(self.messages)

    def replies(self, channel, thread_ts, *, limit=200):
        return self._replies.get(thread_ts, [])

    def add_reaction(self, channel, ts, name="white_check_mark"):
        self.reactions.append((channel, ts, name))
        return True

    def post_reply(self, channel, thread_ts, text):
        self.posts.append((channel, thread_ts, text))
        return {"ok": True}

    def post_message(self, channel, text):
        self.posts.append((channel, None, text))
        return {"ok": True}

    def permalink(self, channel, ts):
        return f"https://slack.example/{channel}/p{ts}"

    def workspace_url(self):
        return "https://slack.example/"

    def download(self, url):
        return self.files.get(url, b"AUDIOBYTES")


class FakeTodoist:
    def __init__(self, inbox=None, projects=None):
        self._inbox = {t["id"]: t for t in (inbox or [])}
        self._projects = projects or {}
        self.log = []  # (op, task_id|project_id, arg)

    def inbox_tasks(self):
        return list(self._inbox.values())

    def tasks(self, project_id):
        from mailroom import config
        if project_id == config.TODOIST_INBOX_ID:
            return self.inbox_tasks()
        return list(self._projects.get(project_id, []))

    def projects(self):
        from mailroom import config
        return [{"id": pid, "name": n} for n, pid in config.TODOIST_PROJECTS.items()]

    def move(self, task_id, project_id):
        self.log.append(("move", task_id, project_id))
        self._inbox.pop(task_id, None)

    def close(self, task_id):
        self.log.append(("close", task_id, None))
        self._inbox.pop(task_id, None)

    def comment(self, task_id, content):
        self.log.append(("comment", task_id, content))

    def add_label(self, task_id, task, label="mailroom-unclear"):
        self.log.append(("label", task_id, label))

    def create_task(self, content, *, project_id, description=""):
        self.log.append(("create", project_id, content))
        return {"id": f"new-{len(self.log)}", "content": content}
