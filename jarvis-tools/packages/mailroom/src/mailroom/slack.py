"""Slack adapter for ``#lab-notes-daniel`` (multi-channel by config).

Ingests **Daniel-authored** messages (top-level + his thread replies) since the
cursor; the bot's own posts and every *other* bot/user (gazette patch-notes,
desk, flare — all posted into this channel via the same app) are ignored. Audio
clips ride along on the message ``files`` array.

:class:`SlackClient` is the network seam — every entry point takes a ``client``
argument so tests inject a fake and no HTTP happens. The real client talks to
``api.slack.com`` with the ``SLACK_MAILROOM_TOKEN`` bot token via stdlib
``urllib`` (no ``requests`` dependency).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from . import config

_API = "https://slack.com/api/"


class SlackError(RuntimeError):
    pass


class SlackClient:
    """Thin bot-token client over the Slack Web API (stdlib only)."""

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("SLACK_MAILROOM_TOKEN", "")

    # ---- transport -------------------------------------------------------- #
    def _get(self, method: str, **params) -> dict:
        url = _API + method + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}"})
        return self._call(req)

    def _post(self, method: str, payload: dict) -> dict:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            _API + method, data=data,
            headers={"Authorization": f"Bearer {self.token}",
                     "Content-Type": "application/json; charset=utf-8"},
        )
        return self._call(req)

    def _call(self, req) -> dict:
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    body = json.load(r)
            except urllib.error.HTTPError as e:  # 429 → back off on Retry-After
                if e.code == 429 and attempt < 3:
                    time.sleep(int(e.headers.get("Retry-After", "1")) + 1)
                    continue
                raise SlackError(f"HTTP {e.code} on {req.full_url}") from e
            if body.get("ok"):
                return body
            if body.get("error") == "ratelimited" and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise SlackError(body.get("error", "unknown slack error"))
        raise SlackError("ratelimited (gave up)")

    # ---- API surface used by the adapter ---------------------------------- #
    def history(self, channel: str, *, oldest: str = "0", limit: int = 200) -> list[dict]:
        out, cursor = [], None
        while True:
            params = {"channel": channel, "limit": limit, "oldest": oldest}
            if cursor:
                params["cursor"] = cursor
            body = self._get("conversations.history", **params)
            out.extend(body.get("messages", []))
            cursor = (body.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                return out

    def replies(self, channel: str, thread_ts: str, *, limit: int = 200) -> list[dict]:
        out, cursor = [], None
        while True:
            params = {"channel": channel, "ts": thread_ts, "limit": limit}
            if cursor:
                params["cursor"] = cursor
            body = self._get("conversations.replies", **params)
            out.extend(body.get("messages", []))
            cursor = (body.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                return out

    def add_reaction(self, channel: str, ts: str, name: str = "white_check_mark") -> bool:
        try:
            self._post("reactions.add", {"channel": channel, "timestamp": ts, "name": name})
            return True
        except SlackError as e:
            # already-reacted is a benign idempotent no-op
            if "already_reacted" in str(e):
                return True
            raise

    def post_reply(self, channel: str, thread_ts: str, text: str) -> dict:
        return self._post("chat.postMessage",
                          {"channel": channel, "thread_ts": thread_ts, "text": text})

    def permalink(self, channel: str, ts: str) -> str:
        try:
            body = self._get("chat.getPermalink", channel=channel, message_ts=ts)
            return body.get("permalink", "")
        except SlackError:
            return ""

    def workspace_url(self) -> str:
        """The workspace base url (``https://team.slack.com/``), fetched once and
        cached — lets us build permalinks locally instead of one API call per
        message (a first backfill of hundreds of messages would otherwise
        double the rate-limited request count)."""
        if getattr(self, "_ws_url", None) is None:
            try:
                self._ws_url = self._get("auth.test").get("url", "")
            except SlackError:
                self._ws_url = ""
        return self._ws_url

    def download(self, url_private_download: str) -> bytes:
        """Download a private file (audio clip) with the bot token."""
        req = urllib.request.Request(
            url_private_download, headers={"Authorization": f"Bearer {self.token}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()


def build_permalink(base_url: str, channel: str, ts: str) -> str:
    """Construct a message permalink locally (Slack's archive URL scheme)."""
    if not base_url:
        return f"slack:{channel}/{ts}"
    return f"{base_url.rstrip('/')}/archives/{channel}/p{ts.replace('.', '')}"


# --------------------------------------------------------------------------- #
# adapter: raw Slack messages → normalized capture dicts
# --------------------------------------------------------------------------- #
@dataclass
class Capture:
    """One Daniel message, normalized (pre-triage)."""
    id: str
    channel: str
    ts: str
    text: str
    files: list[dict]
    is_audio: bool

    @property
    def has_content(self) -> bool:
        return bool(self.text.strip()) or bool(self.files)


_AUDIO_MIMES = ("audio/",)


def _is_audio_file(f: dict) -> bool:
    return str(f.get("mimetype", "")).startswith(_AUDIO_MIMES)


def is_daniel(msg: dict) -> bool:
    """Only Daniel's own human messages — not the bot's, not any other bot/user.

    A bot post (gazette, desk, flare) carries ``bot_id`` even when ``user`` is
    the app's user id, so requiring ``user == DANIEL`` *and* no ``bot_id`` is the
    clean filter. System subtypes (joins, etc.) are dropped."""
    if msg.get("bot_id"):
        return False
    if msg.get("user") != config.DANIEL_USER_ID:
        return False
    subtype = msg.get("subtype")
    return subtype in (None, "", "thread_broadcast", "file_share")


def to_capture(msg: dict, channel: str) -> Capture:
    files = [f for f in (msg.get("files") or []) if isinstance(f, dict)]
    is_audio = any(_is_audio_file(f) for f in files)
    return Capture(
        id=f"slack-{channel}-{msg['ts']}",
        channel=channel,
        ts=msg["ts"],
        text=msg.get("text") or "",
        files=files,
        is_audio=is_audio,
    )


def collect_captures(client: SlackClient, channel: str, *, oldest: str = "0"
                     ) -> list[Capture]:
    """Every Daniel capture in ``channel`` since ``oldest`` (thread replies
    included). Deduplicated by ts; sorted oldest-first."""
    top = client.history(channel, oldest=oldest)
    seen: dict[str, dict] = {}
    for m in top:
        if is_daniel(m):
            seen[m["ts"]] = m
        # descend into any thread with replies to catch Daniel's replies
        if m.get("thread_ts") == m.get("ts") and (m.get("reply_count") or 0) > 0:
            for r in client.replies(channel, m["ts"]):
                if float(r.get("ts", "0")) >= float(oldest or "0") and is_daniel(r):
                    seen[r["ts"]] = r
    caps = [to_capture(m, channel) for m in seen.values()]
    caps = [c for c in caps if c.has_content]
    caps.sort(key=lambda c: float(c.ts))
    return caps
