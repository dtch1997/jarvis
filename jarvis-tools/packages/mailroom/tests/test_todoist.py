"""Todoist helpers: project resolution + name lookup."""

from __future__ import annotations

from mailroom import config, todoist


def test_resolve_project_exact_and_fuzzy():
    assert todoist.resolve_project("Papers to read") == config.TODOIST_PROJECTS["Papers to read"]
    assert todoist.resolve_project("papers") == config.TODOIST_PROJECTS["Papers to read"]
    assert todoist.resolve_project("PhD") == config.TODOIST_PROJECTS["PhD"]
    # a raw id passes through
    pid = config.TODOIST_PROJECTS["Fitness"]
    assert todoist.resolve_project(pid) == pid


def test_resolve_project_unknown_is_none():
    assert todoist.resolve_project("Nonexistent Project") is None
    assert todoist.resolve_project("") is None
    assert todoist.resolve_project(None) is None


def test_project_name_roundtrip():
    pid = config.TODOIST_PROJECTS["Writing"]
    assert todoist.project_name(pid) == "Writing"
    assert todoist.project_name("unknown-id") == "unknown-id"
