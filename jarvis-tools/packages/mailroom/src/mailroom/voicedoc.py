"""voicedoc — voice note → cleaned Google Doc (work Drive) + Slack draft.

The instant leg of the mailroom: a poll-watcher on the capture channel turns
each new Daniel *audio* clip into (1) a cleaned-up document landed as a native
Google Doc in a configured work-Drive folder (rclone ``drive:`` remote, HTML
import) and (2) a forwardable draft message (title + TL;DR + link) posted to
the draft channel. Text captures are untouched — ordinary mailroom triage
still sees the same clip as a thought when its crons run; voicedoc keeps its
own cursor (``voicedoc_cursor:<channel>``) and never touches Todoist/threads.

Any text Daniel types on the same Slack message as the clip is passed to the
cleanup model as steering (title hints, "make this a proposal", audience).

All effects go through seams (slack client, transcriber, model runner, rclone
runner) so tests run with no network. Records land in
``~/.mailroom/voicedocs/`` — one JSON file per processed clip (provenance:
transcript, doc URL, cost, failure reason if any).
"""

from __future__ import annotations

import datetime as _dt
import html as _html
import json
import re
import subprocess
import time

from . import config, slack, spool, triage, voice

# --------------------------------------------------------------------------- #
# cleanup: raw transcript → {title, html body, tldr} via one claude -p call
# --------------------------------------------------------------------------- #

# NOT JSON on purpose: long free-text fields (the html body) reliably break
# JSON string escaping in model replies; line markers cannot.
_CLEANUP_SCHEMA = """\
Return ONLY plain text in exactly this three-part format (no code fences, no
commentary before or after):
TITLE: a short document title naming the idea (not "Voice note")
TLDR: 2-3 plain sentences summarizing the idea for a Slack post — no markdown,
no bullets (may wrap across lines)
HTML:
the cleaned-up document body as simple HTML (<h2>, <p>, <ul>/<li>, <strong>,
<em> only; no <html>/<head>/<body> wrapper, no styles). Organize into sections
with <h2> headings only where the content naturally has them; otherwise plain
paragraphs are fine."""

_CLEANUP_RULES = """\
Rules:
- Preserve the author's ideas, claims, and voice. Do not add content, do not
  editorialize, do not pad. Cut filler words, false starts, and repetition;
  fix punctuation and sentence boundaries; spell out garbled technical terms
  from context.
- The transcript is machine-generated and may mis-hear words — repair only
  when the intended word is obvious from context; otherwise keep what's there.
- Keep roughly the original length (minus filler). This is a cleanup, not a
  summary — the "tldr" field is the only summary."""


def build_cleanup_prompt(transcript: str, note_text: str = "") -> str:
    steering = ""
    if note_text.strip():
        steering = (
            "\nThe author attached this note to the recording — treat it as "
            f"instructions/steering for the cleanup:\n{note_text.strip()}\n"
        )
    return (
        "You are cleaning up a transcribed voice note into a document that "
        "the author's research peers will read.\n\n"
        f"{_CLEANUP_SCHEMA}\n\n{_CLEANUP_RULES}\n{steering}\n"
        f"TRANSCRIPT:\n{transcript.strip()}\n"
    )


_PARTS_RE = re.compile(
    r"TITLE:[ \t]*(?P<title>.*?)\s*\nTLDR:[ \t]*(?P<tldr>.*?)\s*\nHTML:[ \t]*\n?(?P<html>.+)",
    re.DOTALL)


def parse_cleanup(text: str) -> dict | None:
    """Parse the marker-delimited model reply into {title, html, tldr};
    None if unusable."""
    stripped = text.strip()
    stripped = re.sub(r"^```[a-zA-Z]*\n", "", stripped)
    stripped = re.sub(r"\n```\s*$", "", stripped)
    m = _PARTS_RE.search(stripped)
    if not m:
        return None
    body = m.group("html").strip()
    if not body:
        return None
    return {"title": " ".join(m.group("title").split()) or "(untitled voice note)",
            "html": body,
            "tldr": " ".join(m.group("tldr").split())}


def render_html(title: str, body_html: str, *, date: str) -> str:
    """Wrap the model's body HTML into a full page for Drive HTML import."""
    t = _html.escape(title)
    footer = (f"<hr><p><em>Transcribed from a voice note ({date}); "
              f"cleaned up by mailroom voicedoc.</em></p>")
    return (f"<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
            f"<title>{t}</title></head><body><h1>{t}</h1>"
            f"{body_html}{footer}</body></html>")


# --------------------------------------------------------------------------- #
# Drive upload: HTML file → native Google Doc via rclone import
# --------------------------------------------------------------------------- #

def _safe_name(title: str) -> str:
    """Title → Drive-safe file name (no path separators / rclone specials)."""
    name = re.sub(r"[/\\:\x00-\x1f]", " ", title).strip()
    return re.sub(r"\s+", " ", name)[:120] or "untitled"


def _default_rclone(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, check=True, capture_output=True, text=True,
                          timeout=180)


def upload_gdoc(html_text: str, title: str, *, remote: str, folder: str,
                date: str, run=_default_rclone) -> str:
    """Land ``html_text`` as a native Google Doc named ``<date> <title>`` in
    ``remote:folder``; return the doc URL (empty string if the ID lookup
    fails — the upload itself raising is the caller's failure signal)."""
    name = _safe_name(f"{date} {title}")
    dest_dir = f"{remote.rstrip('/')}{folder.strip('/')}"
    local = config.voicedocs_dir() / f"{name}.html"
    local.write_text(html_text)
    run(["rclone", "copyto", str(local), f"{dest_dir}/{name}.html",
         "--drive-import-formats", "html"])
    # resolve the created doc's ID → URL (lsf: path;ID per line)
    try:
        proc = run(["rclone", "lsf", "--format", "pi", "--files-only", dest_dir])
        for line in (proc.stdout or "").splitlines():
            path, _, file_id = line.partition(";")
            if path.rstrip("/") in (name, f"{name}.html") and file_id.strip():
                return f"https://docs.google.com/document/d/{file_id.strip()}/edit"
    except Exception:
        pass
    return ""


# --------------------------------------------------------------------------- #
# the per-clip pipeline + the polling pass
# --------------------------------------------------------------------------- #

def draft_text(title: str, tldr: str, url: str) -> str:
    parts = [f"*{title}*"]
    if tldr:
        parts.append(tldr)
    parts.append(url or "(doc link unavailable — check the Drive folder)")
    return "\n".join(parts)


def _record_path(capture_id: str):
    return config.voicedocs_dir() / f"{spool._safe_id(capture_id)}.json"


def has_record(capture_id: str) -> bool:
    return _record_path(capture_id).exists()


def write_record(record: dict) -> None:
    config.voicedocs_dir().mkdir(parents=True, exist_ok=True)
    _record_path(record["id"]).write_text(json.dumps(record, indent=2))


def process_capture(cap: slack.Capture, vd: config.VoicedocConfig, *,
                    client: slack.SlackClient,
                    transcriber=voice.default_transcriber,
                    runner=triage.default_runner,
                    rclone_run=_default_rclone,
                    gcs_runner=None,
                    date: str | None = None) -> dict:
    """One clip end-to-end. Returns the provenance record (also written to the
    spool); ``record["error"]`` is set on failure."""
    date = date or _dt.date.today().isoformat()
    record: dict = {"id": cap.id, "channel": cap.channel, "ts": cap.ts,
                    "date": date, "note_text": cap.text, "cost_usd": 0.0}
    try:
        # 1. download + transcribe every audio file on the message
        transcripts, pointers = [], []
        for i, f in enumerate(a for a in cap.files
                              if str(a.get("mimetype", "")).startswith("audio/")):
            ext = f.get("filetype") or "m4a"
            local = config.audio_dir() / f"{spool._safe_id(cap.id)}-{i}.{ext}"
            local.write_bytes(client.download(f["url_private_download"]))
            res = voice.process_audio(
                local, f"{cap.id}-{i}", transcriber=transcriber,
                slack_transcription=voice.slack_transcription_text(f),
                duration_ms=f.get("duration_ms"), gcs_runner=gcs_runner)
            transcripts.append(res.transcript)
            pointers.append(res.gcs_pointer)
        transcript = "\n\n".join(t for t in transcripts if t).strip()
        record["transcript"] = transcript
        record["audio_gcs"] = pointers
        if not transcript:
            raise RuntimeError("empty transcript")

        # 2. cleanup call
        reply = runner(build_cleanup_prompt(transcript, cap.text), model=vd.model)
        record["cost_usd"] = float(reply.get("cost_usd") or 0.0)
        doc = parse_cleanup(reply.get("text", ""))
        if doc is None:
            raise RuntimeError("cleanup reply was not parseable JSON")
        record.update(title=doc["title"], tldr=doc["tldr"])

        # 3. Drive upload → native Google Doc
        page = render_html(doc["title"], doc["html"], date=date)
        url = upload_gdoc(page, doc["title"], remote=vd.drive_remote,
                          folder=vd.drive_folder, date=date, run=rclone_run)
        record["doc_url"] = url

        # 4. draft to Slack + close the loop on the source clip
        client.post_message(vd.draft_channel, draft_text(doc["title"], doc["tldr"], url))
        client.add_reaction(cap.channel, cap.ts, "page_facing_up")
    except Exception as e:  # noqa: BLE001 — one bad clip must not stall the watcher
        record["error"] = f"{type(e).__name__}: {e}"
        try:
            client.post_reply(cap.channel, cap.ts, f"voicedoc failed: {record['error']}")
            client.add_reaction(cap.channel, cap.ts, "warning")
        except Exception:
            pass
    write_record(record)
    return record


def _cursor_key(channel: str) -> str:
    return f"voicedoc_cursor:{channel}"


def run_once(*, client: slack.SlackClient | None = None,
             transcriber=voice.default_transcriber,
             runner=triage.default_runner,
             rclone_run=_default_rclone,
             gcs_runner=None,
             now: float | None = None) -> list[dict]:
    """One polling pass: new Daniel audio clips since the cursor → docs.
    First run initializes the cursor to *now* (no backfill of old clips)."""
    vd = config.load_config().voicedoc
    config.ensure_spool()
    client = client or slack.SlackClient()
    state = spool.load_state()
    key = _cursor_key(vd.channel)
    cursor = state.get(key)
    if cursor is None:
        spool.update_state(**{key: f"{now if now is not None else time.time():.6f}"})
        return []
    records = []
    caps = slack.collect_captures(client, vd.channel, oldest=str(cursor))
    for cap in caps:
        if float(cap.ts) <= float(cursor):
            continue
        if cap.is_audio and not has_record(cap.id):
            records.append(process_capture(
                cap, vd, client=client, transcriber=transcriber, runner=runner,
                rclone_run=rclone_run, gcs_runner=gcs_runner))
        # audio or not, the message is seen — advance past it
        spool.update_state(**{key: cap.ts})
    return records


def watch(*, interval: int | None = None, **seams) -> None:
    """Foreground polling daemon (run it in tmux): a pass every
    ``poll_seconds``, one pass's crash never kills the loop."""
    vd = config.load_config().voicedoc
    interval = interval or vd.poll_seconds
    print(f"voicedoc: watching {vd.channel} every {interval}s "
          f"(drive={vd.drive_remote}{vd.drive_folder} → {vd.draft_channel})",
          flush=True)
    while True:
        try:
            for rec in run_once(**seams):
                status = rec.get("error") or rec.get("doc_url") or "ok"
                print(f"voicedoc: {rec['id']} → {status}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"voicedoc: pass failed: {type(e).__name__}: {e}", flush=True)
        time.sleep(interval)
