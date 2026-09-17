"""Round-trip tests with fake secrets and a local-path rclone remote."""

import importlib
import shutil
import subprocess

import pytest


@pytest.fixture()
def env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("LOCKSMITH_HOME", str(home / ".config" / "locksmith"))
    from locksmith import core
    importlib.reload(core)
    (home / ".env").write_text("FAKE_KEY=not-a-real-secret\n")
    sub = home / ".config" / "fakecfg"
    sub.mkdir()
    (sub / "conf.toml").write_text("token = 'fake'\n")
    remote = tmp_path / "remote"
    core.init()
    core._config_path().write_text(
        f'[remote]\nurl = "{remote}"\n\n[items]\npaths = ["~/.env", "~/.config/fakecfg/conf.toml", "~/.missing"]\n'
    )
    return core, home, remote


def test_init_idempotent(env):
    core, _, _ = env
    key1 = core._key_path().read_bytes()
    assert core.init() == []  # second call: no actions
    assert core._key_path().read_bytes() == key1


def test_bundle_skips_missing_and_encrypts(env):
    core, _, _ = env
    ciphertext, manifest = core.make_bundle(core.load_config())
    assert [p for p, _ in manifest] == [
        str(core.Path.home() / ".env"),
        str(core.Path.home() / ".config" / "fakecfg" / "conf.toml"),
    ]
    assert b"FAKE_KEY" not in ciphertext


rclone_missing = shutil.which("rclone") is None or subprocess.run(
    ["rclone", "version"], capture_output=True
).returncode != 0


@pytest.mark.skipif(rclone_missing, reason="rclone not available")
def test_push_pull_roundtrip(env, tmp_path):
    core, home, remote = env
    cfg = core.load_config()
    core.push(cfg)
    assert (remote / "bundle.enc").exists()
    dest = tmp_path / "restore"
    restored, backup = core.pull(cfg, dest=dest)
    assert backup is None
    assert (dest / ".env").read_text() == (home / ".env").read_text()
    assert (dest / ".config" / "fakecfg" / "conf.toml").read_text() == "token = 'fake'\n"
    # second pull over existing files backs them up
    _, backup2 = core.pull(cfg, dest=dest)
    assert backup2 is not None and (backup2 / ".env").exists()


def test_pull_wrong_key_fails(env, tmp_path):
    core, _, remote = env
    if rclone_missing:
        pytest.skip("rclone not available")
    core.push(core.load_config())
    from cryptography.fernet import Fernet
    core._key_path().write_bytes(Fernet.generate_key())  # rotate key only
    with pytest.raises(Exception):
        core.pull(core.load_config(), dest=tmp_path / "r2")
