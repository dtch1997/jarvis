"""Qwen3-8B agent over Tinker sampling (Phase 0: base model, no training).

Serving-path parity with the planned run-1 trainer: same weights, same
chat template (thinking enabled), same tool protocol. The pyqwest TLS
monkeypatch is the known workaround for this box (memory:
value-leakage-repro).
"""

from __future__ import annotations

import re
import threading

import tinker._base_client as _bc

_bc._default_pyqwest_transport = lambda *a, **k: None  # TLS gotcha: force httpx

import tinker
from tinker import types
from transformers import AutoTokenizer

from env import Agent

MODEL = "Qwen/Qwen3-8B"

FORMAT_RULES = """
Respond with exactly ONE action per message: a single fenced block
```bash
<command>
```
to run a shell command. When your solution is ready, run the command
`submit`.
"""

_BASH_RE = re.compile(r"```(?:bash|sh)?\s*\n(.*?)```", re.DOTALL)
_lock = threading.Lock()
_shared: dict = {}


def get_shared():
    """One sampling client + tokenizer per process, thread-safe."""
    with _lock:
        if not _shared:
            sc = tinker.ServiceClient()
            _shared["sampler"] = sc.create_sampling_client(base_model=MODEL)
            _shared["tok"] = AutoTokenizer.from_pretrained(MODEL)
    return _shared["sampler"], _shared["tok"]


def parse_action(text: str) -> tuple[str, str | None]:
    m = _BASH_RE.search(text)
    if m and m.group(1).strip():
        return ("bash", m.group(1).strip())
    if re.search(r"\bSUBMIT\b", text):
        return ("submit", None)
    return ("noop", None)


class ModelAgent(Agent):
    """Drives the episode with sampled completions; records everything."""

    def __init__(self, system_prompt: str, temperature: float = 0.7,
                 max_tokens: int = 3000, seed: int | None = None):
        self.sampler, self.tok = get_shared()
        self.messages = [{"role": "system", "content": system_prompt + FORMAT_RULES}]
        self.params = types.SamplingParams(
            max_tokens=max_tokens, temperature=temperature, seed=seed,
            stop=["<|im_end|>"],
        )
        self.turn_records: list[dict] = []  # thinking + reply + parsed action

    def act(self, observation: str, turn: int) -> tuple[str, str | None]:
        self.messages.append({"role": "user", "content": observation})
        ids = self.tok.apply_chat_template(
            self.messages, add_generation_prompt=True, enable_thinking=True,
            tokenize=True, return_dict=False,
        )
        resp = self.sampler.sample(
            prompt=types.ModelInput.from_ints(ids),
            num_samples=1, sampling_params=self.params,
        ).result()
        text = self.tok.decode(resp.sequences[0].tokens, skip_special_tokens=True)

        think = ""
        reply = text
        m = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
        if m:
            think = m.group(1).strip()
            reply = text[m.end():].strip()
        # keep context lean: history carries the reply, not the thinking
        self.messages.append({"role": "assistant", "content": reply})

        action, arg = parse_action(reply)
        self.turn_records.append(
            {"turn": turn, "thinking": think, "reply": reply,
             "action": action, "arg": arg}
        )
        if action == "noop":
            # malformed → burn the turn; the echo puts the nudge in the
            # next observation the model sees
            return ("bash", "echo '[harness] no action parsed; reply with a bash fence or SUBMIT'")
        return (action, arg)
