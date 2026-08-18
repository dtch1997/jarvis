"""Triage — classify a batch of thoughts with one headless ``claude -p`` call.

Mirrors ``threads.summarize``: :func:`default_runner` shells out to ``claude``
with an isolated ``CLAUDE_CONFIG_DIR`` (so its own transcripts don't pollute
``~/.claude/projects`` — the gotcha threads hit) and ambient
``ANTHROPIC_API_KEY``; every caller takes a ``runner`` seam so tests inject
canned JSON. Thoughts are batched (``triage_batch`` per call) to cut cost.

The output per thought is JSON-schema-shaped (:data:`TYPES`), parsed leniently
and coerced — a bad reply never crashes the run (the thought stays ``unclear``).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile

from . import config

_ISOLATED_CONFIG_DIR = os.path.join(tempfile.gettempdir(), "mailroom-claude")

TYPES = ("todo", "thread-note", "research-idea", "goal-signal", "paper",
         "admin", "unclear")
URGENCIES = ("low", "high")

_SCHEMA_HINT = """\
For EACH captured thought, decide how it should be routed. Return ONLY a JSON
object (no prose, no code fence): {"results": [ <one object per thought, in the
same order and count> ]}. Each object has exactly these keys:
  "id": string, echo the thought's id
  "type": one of ["todo","thread-note","research-idea","goal-signal","paper","admin","unclear"]
  "title": string, one concise line naming the thought
  "candidate_slugs": list of memory/thread slugs from the REGISTRY below it plausibly
       belongs to (only slugs shown in the index; may be empty)
  "project": for todo/admin/paper — the best-fit curated Todoist project NAME from the
       PROJECTS list (papers → "Papers to read"); "" otherwise
  "goal": for goal-signal — the goal file slug from the GOALS list; "" otherwise
  "arxiv_id": an arXiv id if the thought references a paper by id, else ""
  "urgency": "high" ONLY if delaying more than ~48h would cause real harm — an
       explicit deadline, someone blocked waiting, a closing window. Important
       is NOT urgent: status updates, ideas, reading material, and standing
       tasks are always "low". When in doubt, "low".
Guidance: a thought that names ongoing work → thread-note; a concrete action →
todo; an idea with no home → research-idea; a paper/link to read → paper; a
statement about direction/strategy for a known goal → goal-signal; routine
filing → admin. If genuinely unclassifiable, use "unclear" (it stays at the
source). When unsure whether something is a task, prefer "todo"."""


def build_prompt(thoughts: list[dict], slugs: list[str], goals: list[str]) -> str:
    projects = ", ".join(config.TODOIST_PROJECTS.keys())
    reg = "\n".join(f"- {s}" for s in slugs) or "(none)"
    gls = "\n".join(f"- {g}" for g in goals) or "(none)"
    items = []
    for t in thoughts:
        raw = (t.get("raw") or "").strip().replace("\n", " ")
        items.append(f'- id: {t["id"]}\n  source: {t.get("source")}\n  text: {raw[:600]}')
    body = "\n".join(items)
    return (
        "You are triaging Daniel's captured thoughts for a routing pipeline. "
        "Be concise and decisive.\n\n"
        f"{_SCHEMA_HINT}\n\n"
        f"PROJECTS (curated Todoist projects): {projects}\n\n"
        f"GOALS (goal file slugs):\n{gls}\n\n"
        f"REGISTRY (memory/thread slugs):\n{reg}\n\n"
        f"THOUGHTS ({len(thoughts)}):\n{body}\n"
    )


def default_runner(prompt: str, *, model: str) -> dict:
    """Shell out to headless ``claude -p`` → {"text","cost_usd"}."""
    env = {**os.environ, "CLAUDE_CONFIG_DIR": _ISOLATED_CONFIG_DIR}
    proc = subprocess.run(
        ["claude", "-p", prompt, "--model", model, "--output-format", "json", "--bare"],
        capture_output=True, text=True, timeout=300, env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            (proc.stderr or proc.stdout or f"claude exited {proc.returncode}").strip())
    envelope = json.loads(proc.stdout)
    return {"text": envelope.get("result", ""),
            "cost_usd": float(envelope.get("total_cost_usd") or 0.0)}


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    if not text.startswith("{"):
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            text = m.group(0)
    return text.strip()


def _as_list(v) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v if isinstance(x, (str, int, float)) and str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


def _coerce_one(obj: dict) -> dict:
    t = str(obj.get("type") or "").strip()
    if t not in TYPES:
        t = "unclear"
    urg = str(obj.get("urgency") or "low").strip().lower()
    return {
        "type": t,
        "title": (str(obj.get("title") or "").strip() or "(untitled)")[:200],
        "candidate_slugs": _as_list(obj.get("candidate_slugs")),
        "project": str(obj.get("project") or "").strip(),
        "goal": str(obj.get("goal") or "").strip(),
        "arxiv_id": str(obj.get("arxiv_id") or "").strip(),
        "urgency": urg if urg in URGENCIES else "low",
    }


def parse_reply(text: str, thoughts: list[dict]) -> dict[str, dict]:
    """Map thought id → coerced triage. Aligns by echoed id, falling back to
    positional order; any thought the model dropped defaults to unclear."""
    try:
        data = json.loads(_strip_fence(text))
    except (json.JSONDecodeError, ValueError):
        data = {}
    results = data.get("results") if isinstance(data, dict) else data
    if not isinstance(results, list):
        results = []
    by_id: dict[str, dict] = {}
    for i, t in enumerate(thoughts):
        obj = None
        for r in results:
            if isinstance(r, dict) and str(r.get("id")) == t["id"]:
                obj = r
                break
        if obj is None and i < len(results) and isinstance(results[i], dict):
            obj = results[i]
        by_id[t["id"]] = _coerce_one(obj or {})
    return by_id


def triage_batch(thoughts: list[dict], slugs: list[str], goals: list[str], *,
                 runner=default_runner, model: str = config.MODEL) -> tuple[dict[str, dict], float]:
    """One model call over ``thoughts``; returns (id→triage, cost_usd)."""
    if not thoughts:
        return {}, 0.0
    prompt = build_prompt(thoughts, slugs, goals)
    result = runner(prompt, model=model)
    return parse_reply(result.get("text", ""), thoughts), float(result.get("cost_usd") or 0.0)
