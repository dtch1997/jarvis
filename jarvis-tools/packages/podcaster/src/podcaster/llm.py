"""The model seam: one headless ``claude -p`` call in, parsed JSON + cost out.

Everything model-shaped in this package goes through :func:`ask_json`, and every
call site can inject a fake ``runner`` — which is why the pipeline is testable
end-to-end without spending a cent.

Two operational facts are baked in here, both learned the hard way:

* **Web search needs a non-``--bare`` invocation.** ``--bare`` skips hook/plugin/
  skill/CLAUDE.md discovery (much cheaper, much faster) but the resulting session
  has no ``WebSearch``/``WebFetch``. So the research legs run un-bare and the
  writing legs run bare.
* **Run from a scratch cwd with an isolated ``CLAUDE_CONFIG_DIR``.** Otherwise a
  research call inherits whatever repo it was launched in — its CLAUDE.md, its
  plugins, its skills — which is both expensive and a source of drift between
  runs. A podcast research call should depend on the prompt and the web, nothing
  else.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_MODEL = "sonnet"
RESEARCH_TOOLS = ("WebSearch", "WebFetch")
_ISOLATED_CONFIG_DIR = str(Path(tempfile.gettempdir()) / "podcaster-claude-config")


@dataclass
class LlmResult:
    text: str
    cost_usd: float = 0.0


@dataclass
class Ledger:
    """Running cost of one episode, so the report can state what it spent."""
    calls: int = 0
    cost_usd: float = 0.0
    by_stage: dict = field(default_factory=dict)

    def add(self, stage: str, result: LlmResult) -> LlmResult:
        self.calls += 1
        self.cost_usd += result.cost_usd
        self.by_stage[stage] = round(self.by_stage.get(stage, 0.0) + result.cost_usd, 6)
        return result


def default_runner(prompt: str, *, model: str = DEFAULT_MODEL,
                   tools: tuple[str, ...] = (), timeout: int = 900) -> LlmResult:
    """Shell out to headless ``claude -p`` → {text, cost_usd}.

    ``tools`` empty means a pure one-shot generation: add ``--bare`` and skip all
    discovery. Non-empty means the model needs those tools (web research), which
    ``--bare`` would strip.
    """
    argv = ["claude", "-p", prompt, "--model", model, "--output-format", "json",
            "--strict-mcp-config"]
    if tools:
        argv += ["--allowedTools", " ".join(tools)]
    else:
        argv.append("--bare")
    env = {**os.environ, "CLAUDE_CONFIG_DIR": _ISOLATED_CONFIG_DIR}
    Path(_ISOLATED_CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="podcaster-cwd-") as cwd:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              env=env, cwd=cwd)
    if proc.returncode != 0:
        raise RuntimeError(
            (proc.stderr or proc.stdout or f"claude exited {proc.returncode}").strip()[:2000]
        )
    envelope = json.loads(proc.stdout)
    return LlmResult(text=envelope.get("result", "") or "",
                     cost_usd=float(envelope.get("total_cost_usd") or 0.0))


def strip_fence(text: str) -> str:
    """Peel a ```json fence / surrounding prose off a JSON payload."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    text = text.strip()
    if not text.startswith(("{", "[")):
        m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if m:
            text = m.group(1)
    return text.strip()


def ask_json(prompt: str, *, model: str = DEFAULT_MODEL,
             tools: tuple[str, ...] = (), runner=default_runner) -> tuple[dict, LlmResult]:
    """One call, one JSON object. Raises ``ValueError`` if the reply isn't JSON —
    which is a retryable condition, not a crash, at the pipeline level."""
    result = runner(prompt, model=model, tools=tools)
    payload = strip_fence(result.text)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"model did not return JSON ({e}); got: {payload[:400]!r}") from e
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object, got {type(data).__name__}")
    return data, result


JSON_ONLY = ("Reply with a single JSON object and nothing else — no prose before "
             "or after it, no markdown fence.")
