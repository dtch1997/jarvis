#!/usr/bin/env python3
"""Build the ARCH transcript catalog from a local raw S3 mirror.

Input:  raw mirror produced by sync_raw.sh (default ~/data/arch-transcripts/raw)
Output: three layers
  1. catalog tables (small, committed):   out/runs.jsonl, out/sessions.jsonl
  2. messages dataset (big, persisted):   <dataset>/messages/run=<run>/part-0.parquet
  3. rendered transcripts (browsable):    <dataset>/transcripts_md/<run>/.../<session>.md

One parquet row per transcript line, lossless (`raw_json`) plus convenience
columns (role, model, text, thinking, tool names, token usage).

Run from the monorepo root venv with pyarrow available:
  uv run --with pyarrow python build_catalog.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections import Counter
from pathlib import Path

from stagehand import Flow, live_dashboard, serve, track

# ---------------------------------------------------------------- discovery

EXCLUDED_RUNS = {
    # infra smoke tests, not research runs
    "test-user": "transcript-upload infra test",
    "e2e-testclient2": "e2e client test (dummy.txt only)",
    # derived dataset: re-packaged sessions from other runs in this catalog
    "behavior-taxonomy-mdl": "derived dataset (re-packaged ARCH sessions)",
}

ROOTS = [
    # (subdir of raw, source bucket, s3 prefix under bucket)
    ("arch2-legacy", "arch2-154723392477-eu-north-1-an", "arch2"),
    ("arcadia-arch-transcripts/arch2", "arcadia-arch-transcripts", "arch2"),
]

HELDOUT_GHA_ROOT = ("arch2-legacy-heldout", "arch2-154723392477-eu-north-1-an", "arch-heldout")


def discover_runs(raw: Path) -> list[dict]:
    runs, seen = [], set()
    for subdir, bucket, prefix in ROOTS:
        root = raw / subdir
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if not d.is_dir() or d.name in EXCLUDED_RUNS:
                continue
            key = d.name if d.name not in seen else f"{d.name}--{bucket}"
            seen.add(d.name)
            runs.append(
                {
                    "run": key,
                    "dir": str(d),
                    "bucket": bucket,
                    "s3_prefix": f"{prefix}/{d.name}",
                }
            )
    return runs


# ---------------------------------------------------------------- parsing

WORKER_RE = re.compile(r"^worker-(.+)$")
LAUNCH_RE = re.compile(r"^\d{8}T\d{6}Z$")


def classify_session_path(run_dir: Path, f: Path) -> dict:
    """Parse worker/pod/launch out of a session file path, tolerantly."""
    rel = f.relative_to(run_dir).parts
    out = {"worker": None, "pod_id": None, "launch_ts": None, "kind": "other"}
    if rel and (m := WORKER_RE.match(rel[0])):
        out["kind"] = "worker"
        out["worker"] = m.group(1)
        if len(rel) > 2 and rel[1] != "projects":
            out["pod_id"] = rel[1]
        if len(rel) > 3 and LAUNCH_RE.match(rel[2]):
            out["launch_ts"] = rel[2]
    elif rel and rel[0] == "orchestrator":
        out["kind"] = "subagent" if "subagents" in rel else "orchestrator"
        out["worker"] = "orchestrator"
    elif rel and rel[0] == "dev":
        out["kind"] = "dev"
        out["worker"] = "dev"
    return out


def session_format(run_dir: Path, f: Path) -> str | None:
    """Return the transcript format of a jsonl file, or None if it's not a transcript."""
    rel = str(f.relative_to(run_dir))
    if f.name == "cot_raw.jsonl":
        return None
    if "/projects/" in f"/{rel}" and "/memory/" not in f"/{rel}":
        return "claude-code"
    if "codex-sessions" in rel and f.name.startswith("rollout-"):
        return "codex"
    if "codex-transcripts" in rel:
        return "codex-exec"
    if rel.startswith("orchestrator/"):
        return "claude-code"
    # unknown location: sniff the first bytes
    try:
        head = open(f, encoding="utf-8", errors="replace").read(4096)
    except OSError:
        return None
    if '"parentUuid"' in head or '"sessionId"' in head:
        return "claude-code"
    if '"session_meta"' in head and '"payload"' in head:
        return "codex"
    if '"thread.started"' in head or '"item.completed"' in head or '"turn.started"' in head:
        return "codex-exec"
    return None


def _blocks(content) -> list[dict]:
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return []


def parse_session(f: Path, ctx: dict) -> tuple[dict, list[dict]]:
    """Return (session_summary, message_rows) for one session jsonl."""
    rows, bad = [], 0
    with open(f, encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            try:
                rows.append((i, json.loads(line)))
            except json.JSONDecodeError:
                bad += 1

    session_id = f.stem
    title, prs, models = None, [], Counter()
    ts, branches = [], Counter()
    counts = Counter()
    usage_sum = Counter()
    task_prompt = None
    task_prompt_fallback = None
    msg_rows = []

    for seq, r in rows:
        t = r.get("type")
        counts[t] += 1
        if t == "ai-title":
            title = r.get("aiTitle") or title
        if t == "pr-link":
            prs.append(
                {"pr": r.get("prNumber"), "repo": r.get("prRepository"), "url": r.get("prUrl")}
            )
        if t == "queue-operation" and isinstance(r.get("content"), str):
            if r["content"].startswith("# ARCH"):
                task_prompt = task_prompt or r["content"]
            elif task_prompt_fallback is None:
                task_prompt_fallback = r["content"]
        if r.get("timestamp"):
            ts.append(r["timestamp"])
        if r.get("gitBranch"):
            branches[r["gitBranch"]] += 1

        msg = r.get("message") if isinstance(r.get("message"), dict) else {}
        model = msg.get("model")
        if model:
            models[model] += 1
        usage = msg.get("usage") or {}
        for k_src, k_dst in [
            ("input_tokens", "input_tokens"),
            ("output_tokens", "output_tokens"),
            ("cache_read_input_tokens", "cache_read_tokens"),
            ("cache_creation_input_tokens", "cache_creation_tokens"),
        ]:
            if isinstance(usage.get(k_src), int):
                usage_sum[k_dst] += usage[k_src]

        text_parts, thinking_parts, tool_names, tool_result_chars = [], [], [], 0
        for b in _blocks(msg.get("content")):
            bt = b.get("type")
            if bt == "text":
                text_parts.append(b.get("text") or "")
            elif bt == "thinking":
                thinking_parts.append(b.get("thinking") or "")
            elif bt == "tool_use":
                tool_names.append(b.get("name") or "?")
            elif bt == "tool_result":
                c = b.get("content")
                s = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                tool_result_chars += len(s)
                text_parts.append(s)

        msg_rows.append(
            {
                "run": ctx["run"],
                "bucket": ctx["bucket"],
                "kind": ctx["kind"],
                "format": "claude-code",
                "worker": ctx["worker"],
                "pod_id": ctx["pod_id"],
                "launch_ts": ctx["launch_ts"],
                "session_id": session_id,
                "source_file": f.name,
                "seq": seq,
                "line_type": t,
                "uuid": r.get("uuid"),
                "parent_uuid": r.get("parentUuid"),
                "timestamp": r.get("timestamp"),
                "is_sidechain": r.get("isSidechain"),
                "role": msg.get("role"),
                "model": model,
                "request_id": r.get("requestId"),
                "git_branch": r.get("gitBranch"),
                "version": r.get("version"),
                "cwd": r.get("cwd"),
                "text": "\n".join(p for p in text_parts if p) or None,
                "thinking": "\n".join(p for p in thinking_parts if p) or None,
                "tool_names": json.dumps(tool_names) if tool_names else None,
                "tool_result_chars": tool_result_chars or None,
                "input_tokens": (msg.get("usage") or {}).get("input_tokens"),
                "output_tokens": (msg.get("usage") or {}).get("output_tokens"),
                "cache_read_tokens": (msg.get("usage") or {}).get("cache_read_input_tokens"),
                "cache_creation_tokens": (msg.get("usage") or {}).get(
                    "cache_creation_input_tokens"
                ),
                "raw_json": json.dumps(r, ensure_ascii=False),
            }
        )

    session = {
        "run": ctx["run"],
        "bucket": ctx["bucket"],
        "kind": ctx["kind"],
        "format": "claude-code",
        "worker": ctx["worker"],
        "pod_id": ctx["pod_id"],
        "launch_ts": ctx["launch_ts"],
        "session_id": session_id,
        "path": str(f),
        "title": title,
        "first_ts": min(ts) if ts else None,
        "last_ts": max(ts) if ts else None,
        "n_lines": len(rows),
        "n_bad_lines": bad,
        "n_user": counts.get("user", 0),
        "n_assistant": counts.get("assistant", 0),
        "n_sidechain": sum(1 for _, r in rows if r.get("isSidechain")),
        "models": sorted(models),
        "prs": prs,
        "git_branch": branches.most_common(1)[0][0] if branches else None,
        "bytes": f.stat().st_size,
        **{k: int(v) for k, v in usage_sum.items()},
        "_task_prompt": task_prompt,  # stripped before writing; hoisted to run level
    }
    return session, msg_rows


# ---------------------------------------------------------------- codex parsing

def _codex_text(blocks) -> str:
    if isinstance(blocks, str):
        return blocks
    if not isinstance(blocks, list):
        return ""
    return "\n".join(
        b.get("text") or "" for b in blocks if isinstance(b, dict) and b.get("text")
    )


def parse_codex_session(f: Path, ctx: dict) -> tuple[dict, list[dict]]:
    """Parse a Codex CLI rollout jsonl into the unified schema."""
    rows, bad = [], 0
    with open(f, encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            try:
                rows.append((i, json.loads(line)))
            except json.JSONDecodeError:
                bad += 1

    session_id = f.stem
    model, cwd, title = None, None, None
    task_prompt = None
    ts = []
    usage_sum = Counter()
    n_user = n_assistant = 0
    msg_rows = []

    for seq, r in rows:
        t = r.get("type")
        p = r.get("payload") if isinstance(r.get("payload"), dict) else {}
        pt = p.get("type")
        line_type = f"{t}:{pt}" if pt else t
        if r.get("timestamp"):
            ts.append(r["timestamp"])
        if t == "session_meta":
            session_id = p.get("id") or session_id
            cwd = p.get("cwd")
        if t == "turn_context":
            model = p.get("model") or model

        role, text, thinking, tool_names, tool_result_chars = None, None, None, None, None
        in_tok = out_tok = cache_tok = None
        if t == "response_item":
            if pt == "message":
                role = p.get("role")
                text = _codex_text(p.get("content")) or None
                if role == "user":
                    n_user += 1
                    if text and text.startswith("# ARCH") and task_prompt is None:
                        task_prompt = text
                    if title is None and text and not text.startswith("<"):
                        title = text[:120]
                elif role == "assistant":
                    n_assistant += 1
            elif pt == "reasoning":
                role = "assistant"
                thinking = (
                    _codex_text(p.get("summary")) + _codex_text(p.get("content"))
                ) or None
            elif pt == "function_call":
                role = "assistant"
                tool_names = json.dumps([p.get("name") or "?"])
            elif pt == "function_call_output":
                role = "tool"
                out = p.get("output")
                if isinstance(out, str):
                    text = out
                elif isinstance(out, dict):
                    text = _codex_text(out.get("content")) or json.dumps(out)
                elif isinstance(out, list):
                    text = _codex_text(out)
                else:
                    text = None
                tool_result_chars = len(text) if text else None
        elif t == "event_msg" and pt == "token_count":
            u = (p.get("info") or {}).get("last_token_usage") or {}
            in_tok = u.get("input_tokens")
            out_tok = u.get("output_tokens")
            cache_tok = u.get("cached_input_tokens")
            for k, v in [
                ("input_tokens", in_tok),
                ("output_tokens", out_tok),
                ("cache_read_tokens", cache_tok),
            ]:
                if isinstance(v, int):
                    usage_sum[k] += v

        msg_rows.append(
            {
                "run": ctx["run"],
                "bucket": ctx["bucket"],
                "kind": ctx["kind"],
                "format": "codex",
                "worker": ctx["worker"],
                "pod_id": ctx["pod_id"],
                "launch_ts": ctx["launch_ts"],
                "session_id": session_id,
                "source_file": f.name,
                "seq": seq,
                "line_type": line_type,
                "uuid": p.get("id"),
                "parent_uuid": None,
                "timestamp": r.get("timestamp"),
                "is_sidechain": None,
                "role": role,
                "model": model if role == "assistant" else None,
                "request_id": None,
                "git_branch": None,
                "version": None,
                "cwd": cwd,
                "text": text,
                "thinking": thinking,
                "tool_names": tool_names,
                "tool_result_chars": tool_result_chars,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "cache_read_tokens": cache_tok,
                "cache_creation_tokens": None,
                "raw_json": json.dumps(r, ensure_ascii=False),
            }
        )

    session = {
        "run": ctx["run"],
        "bucket": ctx["bucket"],
        "kind": ctx["kind"],
        "format": "codex",
        "worker": ctx["worker"],
        "pod_id": ctx["pod_id"],
        "launch_ts": ctx["launch_ts"],
        "session_id": session_id,
        "path": str(f),
        "title": title,
        "first_ts": min(ts) if ts else None,
        "last_ts": max(ts) if ts else None,
        "n_lines": len(rows),
        "n_bad_lines": bad,
        "n_user": n_user,
        "n_assistant": n_assistant,
        "n_sidechain": 0,
        "models": [model] if model else [],
        "prs": [],
        "git_branch": None,
        "bytes": f.stat().st_size,
        **{k: int(v) for k, v in usage_sum.items()},
        "_task_prompt": task_prompt,
    }
    return session, msg_rows


# ---------------------------------------------------------------- codex-exec parsing

def parse_codex_exec_session(f: Path, ctx: dict) -> tuple[dict, list[dict]]:
    """Parse a `codex exec` event-stream jsonl (thread/turn/item events)."""
    rows, bad = [], 0
    with open(f, encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            try:
                rows.append((i, json.loads(line)))
            except json.JSONDecodeError:
                bad += 1

    session_id = f.stem
    n_assistant = 0
    msg_rows = []
    for seq, r in rows:
        t = r.get("type")
        item = r.get("item") if isinstance(r.get("item"), dict) else {}
        it = item.get("type")
        line_type = f"{t}:{it}" if it else t
        if t == "thread.started":
            session_id = r.get("thread_id") or session_id

        role, text, tool_names, tool_result_chars = None, None, None, None
        if t == "item.completed":
            if it == "agent_message":
                role, text = "assistant", item.get("text")
                n_assistant += 1
            elif it == "command_execution":
                role = "tool"
                out = item.get("aggregated_output") or ""
                text = f"$ {item.get('command')}\n{out}"
                tool_names = json.dumps(["command_execution"])
                tool_result_chars = len(out)
            elif it == "file_change":
                role = "tool"
                tool_names = json.dumps(["file_change"])

        msg_rows.append(
            {
                "run": ctx["run"],
                "bucket": ctx["bucket"],
                "kind": ctx["kind"],
                "format": "codex-exec",
                "worker": ctx["worker"],
                "pod_id": ctx["pod_id"],
                "launch_ts": ctx["launch_ts"],
                "session_id": session_id,
                "source_file": f.name,
                "seq": seq,
                "line_type": line_type,
                "uuid": item.get("id"),
                "parent_uuid": None,
                "timestamp": None,
                "is_sidechain": None,
                "role": role,
                "model": None,
                "request_id": None,
                "git_branch": None,
                "version": None,
                "cwd": None,
                "text": text,
                "thinking": None,
                "tool_names": tool_names,
                "tool_result_chars": tool_result_chars,
                "input_tokens": None,
                "output_tokens": None,
                "cache_read_tokens": None,
                "cache_creation_tokens": None,
                "raw_json": json.dumps(r, ensure_ascii=False),
            }
        )

    session = {
        "run": ctx["run"],
        "bucket": ctx["bucket"],
        "kind": ctx["kind"],
        "format": "codex-exec",
        "worker": ctx["worker"],
        "pod_id": ctx["pod_id"],
        "launch_ts": ctx["launch_ts"],
        "session_id": session_id,
        "path": str(f),
        "title": next(
            (m["text"][:120] for m in msg_rows if m["role"] == "assistant" and m["text"]), None
        ),
        "first_ts": None,
        "last_ts": None,
        "n_lines": len(rows),
        "n_bad_lines": bad,
        "n_user": 0,
        "n_assistant": n_assistant,
        "n_sidechain": 0,
        "models": [],
        "prs": [],
        "git_branch": None,
        "bytes": f.stat().st_size,
        "_task_prompt": None,
    }
    return session, msg_rows


# ---------------------------------------------------------------- rendering

TRUNC_NOTE = "\n… [truncated; full content in messages parquet] …\n"


def _trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n // 2] + TRUNC_NOTE + s[-n // 2 :]


def render_session_md(session: dict, msg_rows: list[dict]) -> str:
    hdr = [
        f"# {session['run']} · worker {session['worker']} · session {session['session_id'][:8]}",
        "",
        f"- **title:** {session['title'] or '(none)'}",
        f"- **span:** {session['first_ts']} → {session['last_ts']}  ·  "
        f"{session['n_lines']} lines, {session['n_assistant']} assistant msgs",
        f"- **models:** {', '.join(session['models']) or '?'}  ·  "
        f"**branch:** {session['git_branch'] or '?'}",
        f"- **PRs opened:** {', '.join(p['url'] for p in session['prs']) or '(none)'}",
        "",
        "---",
        "",
    ]
    body = []
    for m in msg_rows:
        t = m["line_type"]
        if t == "queue-operation":
            raw = json.loads(m["raw_json"])
            body.append(f"## ⏎ queued prompt ({m['timestamp']})\n\n{_trunc(raw.get('content') or '', 4000)}\n")
        elif t == "user":
            tag = "🧑 USER" if not m["tool_names"] and not m["tool_result_chars"] else "🔧 TOOL RESULT"
            sc = " (sidechain)" if m["is_sidechain"] else ""
            txt = _trunc(m["text"] or "", 1500 if tag.startswith("🔧") else 4000)
            body.append(f"## {tag}{sc} ({m['timestamp']})\n\n{txt}\n")
        elif t == "assistant":
            sc = " (sidechain)" if m["is_sidechain"] else ""
            parts = [f"## 🤖 ASSISTANT{sc} ({m['timestamp']}, {m['model']}, out={m['output_tokens']} tok)\n"]
            if m["thinking"]:
                parts.append(f"<details><summary>thinking</summary>\n\n{_trunc(m['thinking'], 3000)}\n\n</details>\n")
            if m["text"]:
                parts.append(_trunc(m["text"], 6000) + "\n")
            if m["tool_names"]:
                raw = json.loads(m["raw_json"])
                for b in _blocks(raw.get("message", {}).get("content")):
                    if b.get("type") == "tool_use":
                        inp = json.dumps(b.get("input", {}), ensure_ascii=False)
                        parts.append(f"**→ tool_use `{b.get('name')}`** `{_trunc(inp, 1200)}`\n")
            body.append("\n".join(parts))
        elif t == "pr-link":
            raw = json.loads(m["raw_json"])
            body.append(f"## 🔗 PR opened: {raw.get('prUrl')}\n")
        # ai-title / last-prompt / attachment lines: metadata, skip in render
    return "\n".join(hdr + body)


def render_codex_md(session: dict, msg_rows: list[dict]) -> str:
    hdr = [
        f"# {session['run']} · worker {session['worker']} · codex session {session['session_id'][:8]}",
        "",
        f"- **span:** {session['first_ts']} → {session['last_ts']}  ·  "
        f"{session['n_lines']} lines, {session['n_assistant']} assistant msgs",
        f"- **models:** {', '.join(session['models']) or '?'}",
        "",
        "---",
        "",
    ]
    body = []
    for m in msg_rows:
        lt = m["line_type"]
        if lt == "response_item:message":
            tag = {"user": "🧑 USER", "developer": "⚙️ DEVELOPER", "assistant": "🤖 ASSISTANT"}.get(
                m["role"], m["role"] or "?"
            )
            body.append(f"## {tag} ({m['timestamp']})\n\n{_trunc(m['text'] or '', 5000)}\n")
        elif lt == "response_item:reasoning" and m["thinking"]:
            body.append(
                f"<details><summary>thinking</summary>\n\n{_trunc(m['thinking'], 3000)}\n\n</details>\n"
            )
        elif lt == "response_item:function_call":
            raw = json.loads(m["raw_json"])["payload"]
            args = raw.get("arguments") or ""
            body.append(
                f"**→ tool_use `{raw.get('name')}`** `{_trunc(args, 1200)}`\n"
            )
        elif lt == "response_item:function_call_output":
            body.append(f"## 🔧 TOOL RESULT ({m['timestamp']})\n\n{_trunc(m['text'] or '', 1500)}\n")
    return "\n".join(hdr + body)


def render_codex_exec_md(session: dict, msg_rows: list[dict]) -> str:
    hdr = [
        f"# {session['run']} · worker {session['worker']} · codex-exec {session['session_id'][:8]}",
        "",
        f"- **source:** {Path(session['path']).name}  ·  {session['n_lines']} events, "
        f"{session['n_assistant']} assistant msgs (no timestamps in this format)",
        "",
        "---",
        "",
    ]
    body = []
    for m in msg_rows:
        if m["role"] == "assistant" and m["text"]:
            body.append(f"## 🤖 ASSISTANT\n\n{_trunc(m['text'], 6000)}\n")
        elif m["line_type"] == "item.completed:command_execution":
            body.append(f"## 🔧 COMMAND\n\n```\n{_trunc(m['text'] or '', 1500)}\n```\n")
    return "\n".join(hdr + body)


# ---------------------------------------------------------------- per-run step

def _message_schema():
    import pyarrow as pa

    return pa.schema(
        [
            ("run", pa.string()),
            ("bucket", pa.string()),
            ("kind", pa.string()),
            ("format", pa.string()),
            ("worker", pa.string()),
            ("pod_id", pa.string()),
            ("launch_ts", pa.string()),
            ("session_id", pa.string()),
            ("source_file", pa.string()),
            ("seq", pa.int32()),
            ("line_type", pa.string()),
            ("uuid", pa.string()),
            ("parent_uuid", pa.string()),
            ("timestamp", pa.string()),
            ("is_sidechain", pa.bool_()),
            ("role", pa.string()),
            ("model", pa.string()),
            ("request_id", pa.string()),
            ("git_branch", pa.string()),
            ("version", pa.string()),
            ("cwd", pa.string()),
            ("text", pa.large_string()),
            ("thinking", pa.large_string()),
            ("tool_names", pa.string()),
            ("tool_result_chars", pa.int64()),
            ("input_tokens", pa.int64()),
            ("output_tokens", pa.int64()),
            ("cache_read_tokens", pa.int64()),
            ("cache_creation_tokens", pa.int64()),
            ("raw_json", pa.large_string()),
        ]
    )


FLUSH_ROWS = 20_000


def make_extract(dataset: Path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    schema = _message_schema()

    async def extract_run(runspec: dict) -> dict:
        run, run_dir = runspec["run"], Path(runspec["dir"])
        files = []
        for f in sorted(run_dir.rglob("*.jsonl")):
            fmt = session_format(run_dir, f)
            if fmt:
                files.append((f, fmt))

        pq_dir = dataset / "messages" / f"run={run}"
        pq_dir.mkdir(parents=True, exist_ok=True)
        writer = pq.ParquetWriter(pq_dir / "part-0.parquet", schema, compression="zstd")
        buffer: list[dict] = []
        n_messages = 0

        def flush():
            nonlocal buffer
            if buffer:
                writer.write_table(pa.Table.from_pylist(buffer, schema=schema))
                buffer = []

        parsers = {
            "claude-code": parse_session,
            "codex": parse_codex_session,
            "codex-exec": parse_codex_exec_session,
        }
        renderers = {
            "claude-code": render_session_md,
            "codex": render_codex_md,
            "codex-exec": render_codex_exec_md,
        }
        sessions = []
        task_prompt = None
        task_prompt_fallback = None
        t = track(files, f"extract:{run}")
        for f, fmt in t:
            ctx = {**classify_session_path(run_dir, f), "run": run, "bucket": runspec["bucket"]}
            try:
                session, msg_rows = await asyncio.to_thread(parsers[fmt], f, ctx)
            except Exception as e:  # tolerate one broken file, keep the run
                sessions.append({"run": run, "path": str(f), "error": repr(e)})
                continue
            tp = session.pop("_task_prompt", None)
            tpf = session.pop("_task_prompt_fallback", None)
            task_prompt = task_prompt or tp
            task_prompt_fallback = task_prompt_fallback or tpf
            sessions.append(session)
            buffer.extend(msg_rows)
            n_messages += len(msg_rows)
            if len(buffer) >= FLUSH_ROWS:
                await asyncio.to_thread(flush)

            md = renderers[fmt](session, msg_rows)
            wk = f"worker-{session['worker']}" if session["worker"] is not None else "other"
            md_path = dataset / "transcripts_md" / run / wk / f"{f.stem}.md"
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(md)
            t.set(last=f.name)
        await asyncio.to_thread(flush)
        writer.close()
        if n_messages == 0:
            (pq_dir / "part-0.parquet").unlink(missing_ok=True)
            pq_dir.rmdir()

        # copy worker memory notes verbatim (small, high-signal)
        for mem in run_dir.rglob("memory/*.md"):
            rel = mem.relative_to(run_dir)
            dst = dataset / "worker_memory" / run / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(mem.read_bytes())

        ok = [s for s in sessions if "error" not in s]
        heldout_logs = len(list(run_dir.rglob("heldout-eval.log")))
        ts_all = [s["first_ts"] for s in ok if s.get("first_ts")] + [
            s["last_ts"] for s in ok if s.get("last_ts")
        ]
        run_row = {
            "run": run,
            "bucket": runspec["bucket"],
            "s3_prefix": runspec["s3_prefix"],
            "n_workers": len({s["worker"] for s in ok if s.get("kind") == "worker"}),
            "formats": sorted({s.get("format") for s in ok if s.get("format")}),
            "n_pods": len({s["pod_id"] for s in ok if s.get("pod_id")}),
            "n_sessions": len(ok),
            "n_session_errors": len(sessions) - len(ok),
            "n_messages": n_messages,
            "first_ts": min(ts_all) if ts_all else None,
            "last_ts": max(ts_all) if ts_all else None,
            "bytes_jsonl": sum(s.get("bytes", 0) for s in ok),
            "models": sorted({m for s in ok for m in s.get("models", [])}),
            "prs": list({p["url"]: p for s in ok for p in s.get("prs", [])}.values()),
            "n_heldout_eval_logs": heldout_logs or None,
            "n_worker_memory_files": len(list(run_dir.rglob("memory/*.md"))) or None,
            "output_tokens": sum(s.get("output_tokens", 0) or 0 for s in ok),
            "task_prompt": task_prompt or task_prompt_fallback,
        }
        return {"run_row": run_row, "sessions": sessions}

    return extract_run


# ---------------------------------------------------------------- main

async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=Path.home() / "data/arch-transcripts/raw")
    ap.add_argument("--dataset", type=Path, default=Path.home() / "data/arch-transcripts/dataset")
    ap.add_argument("--catalog", type=Path, default=Path(__file__).parent / "out")
    ap.add_argument("--runs-dir", type=Path, default=Path(__file__).parent / "runs")
    ap.add_argument("--serve", action="store_true", help="serve the live dashboard via lobby")
    args = ap.parse_args()

    runspecs = discover_runs(args.raw)
    print(f"discovered {len(runspecs)} runs")
    args.dataset.mkdir(parents=True, exist_ok=True)
    args.catalog.mkdir(parents=True, exist_ok=True)

    flow = Flow(str(args.runs_dir), concurrency=8)
    extracted = flow.map("extract", runspecs, make_extract(args.dataset))

    async def merge(results: list[dict]) -> dict:
        run_rows = sorted((r["run_row"] for r in results), key=lambda r: r["first_ts"] or "")
        sess_rows = [s for r in results for s in r["sessions"]]
        with open(args.catalog / "runs.jsonl", "w") as f:
            for r in run_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        with open(args.catalog / "sessions.jsonl", "w") as f:
            for s in sess_rows:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        # task prompts as standalone browsable files
        tp_dir = args.dataset / "task_prompts"
        tp_dir.mkdir(exist_ok=True)
        for r in run_rows:
            if r.get("task_prompt"):
                (tp_dir / f"{r['run']}.md").write_text(r["task_prompt"])
        return {
            "runs": len(run_rows),
            "sessions": len(sess_rows),
            "messages": sum(r["n_messages"] for r in run_rows),
        }

    merged = flow.reduce("merge", extracted, merge)

    async with live_dashboard(str(args.runs_dir), title="arch-transcript-catalog"):
        if args.serve:
            url, stop = serve(str(args.runs_dir), name="arch-catalog")
            print("dashboard:", url)
        try:
            await flow.run()
        finally:
            if args.serve:
                stop()
    print("merged:", merged.result)


if __name__ == "__main__":
    asyncio.run(main())
