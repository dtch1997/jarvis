"""Serve stories_enriched.jsonl via databrowser -> lobby hub URL."""

import pathlib
import signal

import databrowser

EXP = pathlib.Path(__file__).parent

viewer = databrowser.serve(
    str(EXP / "stories_enriched.jsonl"),
    filter_fields=[
        "model",
        "topic",
        "condition",
        "stop_reason",
        "disclaimed",
        "slop_per_1k",
        "cosmic_per_1k",
        "concrete_per_1k",
        "n_words",
    ],
    title="lived-experience stories",
)
print("URL:", viewer.url, flush=True)
signal.pause()
