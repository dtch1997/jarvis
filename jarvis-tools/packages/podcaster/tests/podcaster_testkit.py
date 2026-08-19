"""Fakes for the two expensive seams: the model and the TTS engine.

The pipeline tests run the real graph, the real chunker, the real style gate, the
real wav concatenation and the real dataclasses — only ``claude -p``, ffmpeg and
the ONNX voice are faked. That is the line: fake what costs money or needs a
model file, exercise everything else.
"""

from __future__ import annotations

import json

from podcaster.llm import LlmResult
from podcaster.models import words_for

GOOD_PARAGRAPHS = [
    "Here is the part that surprised me. The model got better at agreeing, not at "
    "helping. Those are different skills. You can measure one and think you got "
    "the other.",
    "So what does that actually buy you? A rater sees a confident answer and marks "
    "it good. The confident answer was wrong about a date. Nobody checked. That is "
    "the whole story of one big eval.",
    "Hold that thought, because the counter-case is real. Two teams tried the same "
    "recipe and got opposite results. One of them had a much bigger rater pool. "
    "That difference might be the whole effect.",
]


def _script_payload(target_minutes: float, *, n_beats: int = 3,
                    bad: bool = False) -> dict:
    """A synthetic script sized to the requested duration. ``bad=True`` produces
    page prose (bullets, a URL, one enormous sentence) so the gate has to fire."""
    if bad:
        return {
            "title": "An Essay Read Aloud",
            "blurb": "This is the failure mode.",
            "segments": [
                {"kind": "cold_open", "title": "intro",
                 "text": "In this article we will discuss three things:\n"
                         "- first, the setup\n- second, the result\n"
                         "See https://example.com/paper for details, and as "
                         "discussed above the situation is complicated in ways "
                         "that a single sentence cannot capture, which is why "
                         "this sentence keeps going well past the point at which "
                         "any listener walking down a street would still be able "
                         "to hold its beginning in mind while it finally arrives "
                         "at a verb somewhere near the very end of the clause."},
                {"kind": "beat", "title": "body", "text": "Firstly, the data (Smith, 2024)."},
            ],
        }
    target_words = words_for(target_minutes)
    body = "\n\n".join(GOOD_PARAGRAPHS)
    # size the fake to the requested duration, so the gate's length check is
    # exercised for real rather than always failing on a fixture that is too short
    per_beat = max(1, (target_words - 90) // max(1, n_beats))
    reps = max(1, round(per_beat / max(1, len(body.split()))))
    segments = [{"kind": "cold_open", "title": "hook",
                 "text": "Eighty percent of the raters said the wrong answer was "
                         "the better one. Same model, same question. That number "
                         "is what this episode is about, and you are going to want "
                         "to know why it happened."}]
    for i in range(n_beats):
        segments.append({"kind": "beat", "title": f"beat {i + 1}",
                         "text": "\n\n".join([body] * reps)})
    segments.append({"kind": "sign_off", "title": "out",
                     "text": "Watch for the rater pool size the next time you read "
                             "a result like this. It tells you more than the "
                             "headline does. Talk soon."})
    return {"title": "The Agreement Trap", "blurb": "Two sentences of notes.",
            "segments": segments}


class FakeRunner:
    """Stands in for ``claude -p``: routes on a marker in the prompt.

    Records every prompt, so tests can assert what the pipeline actually asked
    for (that the rewrite carried the gate's complaints, for instance).
    """

    def __init__(self, *, questions: int = 3, target_minutes: float = 4.0,
                 findings_per_question: int = 2, bad_first_draft: bool = False,
                 empty_first_dig: bool = False, cost: float = 0.01):
        self.questions = questions
        self.target_minutes = target_minutes
        self.findings_per_question = findings_per_question
        self.bad_first_draft = bad_first_draft
        self.empty_first_dig = empty_first_dig
        self.cost = cost
        self.prompts: list[str] = []
        self.calls: dict[str, int] = {}

    def _tick(self, kind: str) -> int:
        self.calls[kind] = self.calls.get(kind, 0) + 1
        return self.calls[kind]

    def __call__(self, prompt: str, *, model="fake", tools=()) -> LlmResult:
        self.prompts.append(prompt)
        if "choose the ANGLE" in prompt:
            self._tick("plan")
            payload = {
                "angle": "Cooperativeness training mostly buys agreement.",
                "through_line": "Measure the thing you want, not its shadow.",
                "questions": [{"id": f"q{i + 1}", "text": f"question {i + 1}?",
                               "why": "the episode needs it"}
                              for i in range(self.questions)],
            }
        elif "Research this one question" in prompt:
            n = self._tick("dig")
            if self.empty_first_dig and n == 1:
                payload = {"findings": []}
            else:
                payload = {"findings": [
                    {"claim": f"Finding {n}.{k} with a number in it, eighty percent.",
                     "detail": "Two sentences of substance. With a caveat.",
                     "source_title": f"Source {n}.{k}",
                     "source_url": f"https://example.com/{n}-{k}",
                     "surprising": k == 0}
                    for k in range(self.findings_per_question)]}
        elif "turning research into a brief" in prompt:
            self._tick("brief")
            payload = {
                "promise": "You will know which number to distrust.",
                "beats": [{"title": f"Beat {i + 1}", "purpose": "does a job",
                           "must_say": [f"the {i + 1} thing"]} for i in range(3)],
                "open_questions": ["whether it replicates"],
            }
        elif "Write a solo-narrated podcast episode" in prompt:
            n = self._tick("script")
            bad = self.bad_first_draft and n == 1
            payload = _script_payload(self.target_minutes, bad=bad)
        else:
            raise AssertionError(f"unexpected prompt: {prompt[:200]!r}")
        return LlmResult(text=json.dumps(payload), cost_usd=self.cost)


class RecordingFfmpeg:
    """ffmpeg seam: records argv and writes a stub file at the output path."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> None:
        self.calls.append(list(argv))
        open(argv[-1], "wb").write(b"ID3stub")


class RecordingRclone:
    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> None:
        self.calls.append(list(argv))
