"""Persisting the artifact: what pointer comes back, and what gets pushed."""

import pytest

from podcaster import publish

from podcaster_testkit import RecordingRclone


def test_publish_pushes_the_mp3_and_the_provenance_files(tmp_path):
    rc = RecordingRclone()
    mp3 = tmp_path / "ep.mp3"
    mp3.write_bytes(b"x")
    pointer = publish.publish_episode(
        mp3, slug="2026-08-19-topic", prefix="gcs:bucket/prefix",
        extras={"script.json": tmp_path / "s.json"}, runner=rc)
    assert pointer == "gcs:bucket/prefix/2026-08-19-topic.mp3"
    assert [c[-1] for c in rc.calls] == [
        "gcs:bucket/prefix/2026-08-19-topic.mp3",
        "gcs:bucket/prefix/2026-08-19-topic.script.json",
    ]
    assert rc.calls[0][:2] == ["rclone", "copyto"]


def test_a_failed_push_is_loud(tmp_path):
    def boom(argv):
        raise RuntimeError("no credentials")
    with pytest.raises(RuntimeError, match="no credentials"):
        publish.push(tmp_path, "gcs:bucket/x", runner=boom)


def test_default_prefix_points_at_the_experiments_path():
    assert publish.GCS_PREFIX.endswith("daniel/jarvis/experiments/podcast-pipeline")
