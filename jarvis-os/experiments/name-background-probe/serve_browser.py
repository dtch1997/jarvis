"""Serve results.jsonl via databrowser -> lobby hub URL."""

import pathlib
import signal

import databrowser

EXP = pathlib.Path(__file__).parent

viewer = databrowser.serve(
    str(EXP / "results.jsonl"),
    filter_fields=[
        "phase",
        "model",
        "name",
        "name_kind",
        "context",
        "role",
        "target_name",
        "stop_reason",
    ],
    title="name-background probe",
    strict=False,  # e1 and e2 records have different key sets
)
print("URL:", viewer.url, flush=True)
signal.pause()
