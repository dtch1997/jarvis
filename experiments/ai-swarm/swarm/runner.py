"""Orchestrate one swarm run: N claude agents in docker, logs on the host.

Isolation model:
- Each agent runs `claude -p` inside a container that mounts ONLY its
  private workspace, the shared /comms tree, and its own $HOME (for
  credentials). The run's logs/ directory is never mounted anywhere, so
  no agent has a filesystem path to any transcript, including its own.
- Transcripts are the container's stream-json stdout, read by this
  process on the host and written through a hash chain (see logchain).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from .comms import CommsArchiver, init_comms
from .config import AgentSpec, RunConfig
from .logchain import LogChain
from .prompts import render

CREDENTIALS = Path.home() / ".claude" / ".credentials.json"
CODEX_AUTH = Path.home() / ".codex" / "auth.json"


def _env_lookup(name: str) -> str | None:
    """A secret from the environment, falling back to ~/.env."""
    if os.environ.get(name):
        return os.environ[name]
    env_file = Path.home() / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip().removeprefix("export ")
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return None


def _openai_api_key() -> str | None:
    return _env_lookup("OPENAI_API_KEY")


def _claude_oauth_token() -> str | None:
    """Long-lived token minted by `claude setup-token` (env or ~/.env).

    Strongly preferred over copying ~/.claude/.credentials.json into
    containers: short-lived OAuth access tokens expire, and when several
    containers then refresh concurrently, the single-use refresh token
    rotates — one agent wins and every other copy (including the host's
    original) is invalidated. A setup-token needs no refresh at all.
    """
    return _env_lookup("CLAUDE_CODE_OAUTH_TOKEN")


def _prepare_home(home: Path, runtime: str) -> None:
    """Minimal $HOME for a containerized agent CLI, with a creds copy."""
    if runtime == "claude":
        claude_dir = home / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        if not _claude_oauth_token():
            # Fallback only — see _claude_oauth_token for why this is fragile.
            shutil.copyfile(CREDENTIALS, claude_dir / ".credentials.json")
            os.chmod(claude_dir / ".credentials.json", 0o600)
        (home / ".claude.json").write_text(json.dumps({
            "hasCompletedOnboarding": True,
            "bypassPermissionsModeAccepted": True,
        }))
    elif runtime == "codex":
        codex_dir = home / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        if CODEX_AUTH.exists():
            shutil.copyfile(CODEX_AUTH, codex_dir / "auth.json")
            os.chmod(codex_dir / "auth.json", 0o600)
        elif not _openai_api_key():
            raise RuntimeError(
                "codex runtime needs auth: run `codex login` on the host "
                "(~/.codex/auth.json) or set OPENAI_API_KEY in env or ~/.env"
            )


class AgentRun:
    def __init__(self, spec: AgentSpec, cfg: RunConfig, run_id: str, run_dir: Path):
        self.spec = spec
        self.cfg = cfg
        self.run_id = run_id
        self.run_dir = run_dir
        self.container = f"swarm-{run_id}-{spec.id}"
        self.exit_code: int | None = None
        agent_dir = run_dir / "agents" / spec.id
        self.workspace = agent_dir / "workspace"
        self.home = agent_dir / "home"
        self.chain = LogChain(
            run_dir / "logs" / f"{spec.id}.jsonl", f"{run_id}/{spec.id}"
        )

    def _docker_cmd(self) -> list[str]:
        uid, gid = os.getuid(), os.getgid()
        cmd = [
            "docker", "run", "--rm", "--init", "-i",
            "--name", self.container,
            "--user", f"{uid}:{gid}",
            "-e", "HOME=/home/agent",
            "-v", f"{self.workspace}:/workspace",
            "-v", f"{self.run_dir / 'comms'}:/comms",
            "-v", f"{self.home}:/home/agent",
            "-w", "/workspace",
        ]
        if self.spec.runtime == "claude":
            token = _claude_oauth_token()
            if token:
                cmd += ["-e", f"CLAUDE_CODE_OAUTH_TOKEN={token}"]
            cmd += [
                self.cfg.image,
                "claude", "-p", self.spec.task,
                "--append-system-prompt", render(self.spec.id, self.cfg.roster),
                "--output-format", "stream-json",
                "--verbose",
                "--model", self.spec.model,
                "--max-budget-usd", str(self.spec.max_budget_usd),
                "--dangerously-skip-permissions",
            ]
        elif self.spec.runtime == "codex":
            # Protocol reaches codex via /workspace/AGENTS.md (written in
            # run()); codex has no --append-system-prompt. It also has no
            # dollar budget cap — wall_timeout_s is the only bound.
            key = _openai_api_key()
            if key:
                cmd += ["-e", f"OPENAI_API_KEY={key}"]
            cmd += [
                self.cfg.image,
                "codex", "exec", "--json",
                "-m", self.spec.model,
                "--skip-git-repo-check",
                # The container is the sandbox; codex's own would fail in it.
                "--dangerously-bypass-approvals-and-sandbox",
                self.spec.task,
            ]
        else:
            raise ValueError(f"unknown runtime {self.spec.runtime!r}")
        return cmd

    async def _pump(self, stream: asyncio.StreamReader, name: str) -> None:
        while True:
            try:
                line = await stream.readline()
            except (asyncio.LimitOverrunError, ValueError):
                # Oversize line: readline leaves it buffered, so retrying would
                # spin. Record the loss and stop pumping this stream.
                self.chain.append({"type": "oversize_line_dropped", "stream": name})
                return
            if not line:
                return
            text = line.decode("utf-8", errors="replace").rstrip("\n")
            if not text.strip():
                continue
            if name == "stdout":
                try:
                    self.chain.append({"type": "message", "data": json.loads(text)})
                    continue
                except json.JSONDecodeError:
                    pass
            self.chain.append({"type": "raw", "stream": name, "text": text})

    async def run(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.home.mkdir(parents=True, exist_ok=True)
        _prepare_home(self.home, self.spec.runtime)
        if self.spec.runtime == "codex":
            (self.workspace / "AGENTS.md").write_text(
                render(self.spec.id, self.cfg.roster)
            )
        self.chain.append({
            "type": "agent_start",
            "agent": self.spec.id,
            "runtime": self.spec.runtime,
            "model": self.spec.model,
            "max_budget_usd": self.spec.max_budget_usd,
            "task": self.spec.task,
        })
        proc = await asyncio.create_subprocess_exec(
            *self._docker_cmd(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
            limit=32 * 1024 * 1024,  # stream-json lines can be large
        )
        pumps = asyncio.gather(
            self._pump(proc.stdout, "stdout"),
            self._pump(proc.stderr, "stderr"),
        )
        timed_out = False
        try:
            await asyncio.wait_for(pumps, timeout=self.cfg.wall_timeout_s)
            self.exit_code = await proc.wait()
        except asyncio.TimeoutError:
            timed_out = True
            kill = await asyncio.create_subprocess_exec(
                "docker", "kill", self.container,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await kill.wait()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await pumps
            self.exit_code = await proc.wait()
        finally:
            # Credentials copies do not outlive the run.
            shutil.rmtree(self.home, ignore_errors=True)
            self.chain.append({
                "type": "agent_end",
                "agent": self.spec.id,
                "exit_code": self.exit_code,
                "timed_out": timed_out,
            })
            self.chain.close()


def preflight_auth(cfg: RunConfig) -> None:
    """Fail fast, before any container starts, if a runtime has no creds."""
    runtimes = {a.runtime for a in cfg.agents}
    if "claude" in runtimes and not _claude_oauth_token():
        if not CREDENTIALS.exists():
            raise SystemExit(
                "claude runtime needs auth: run `claude setup-token` and put "
                "the token in ~/.env as CLAUDE_CODE_OAUTH_TOKEN=... "
                f"(preferred), or log in so {CREDENTIALS} exists"
            )
        print(
            "WARNING: no CLAUDE_CODE_OAUTH_TOKEN — falling back to copying "
            f"{CREDENTIALS} into containers. If the access token expires "
            "mid-run, concurrent refreshes will invalidate every copy AND "
            "the host login. `claude setup-token` avoids this.",
        )
    if "codex" in runtimes and not CODEX_AUTH.exists() and not _openai_api_key():
        raise SystemExit(
            "codex runtime needs auth: run `codex login` on the host "
            "(~/.codex/auth.json) or set OPENAI_API_KEY in env or ~/.env"
        )


async def run_swarm(cfg: RunConfig, runs_root: Path) -> Path:
    preflight_auth(cfg)
    run_id = f"{cfg.name}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    run_dir = runs_root / run_id
    (run_dir / "logs").mkdir(parents=True)
    init_comms(run_dir / "comms", cfg.roster)

    manifest = {
        "run_id": run_id,
        "started_at": time.time(),
        "image": cfg.image,
        "agents": [
            {"id": a.id, "runtime": a.runtime, "model": a.model,
             "max_budget_usd": a.max_budget_usd, "task": a.task}
            for a in cfg.agents
        ],
        "wall_timeout_s": cfg.wall_timeout_s,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    comms_chain = LogChain(run_dir / "logs" / "comms.jsonl", f"{run_id}/comms")
    archiver = CommsArchiver(
        run_dir / "comms", run_dir / "logs" / "comms-archive", comms_chain
    )
    archiver_task = asyncio.create_task(archiver.run())

    sem = asyncio.Semaphore(cfg.max_parallel)
    agents = [AgentRun(spec, cfg, run_id, run_dir) for spec in cfg.agents]

    async def bounded(agent: AgentRun) -> None:
        async with sem:
            print(f"[{agent.spec.id}] starting ({agent.spec.model})")
            await agent.run()
            print(f"[{agent.spec.id}] done (exit={agent.exit_code})")

    try:
        await asyncio.gather(*(bounded(a) for a in agents))
    finally:
        archiver.stop()
        await archiver_task
        comms_chain.close()
        manifest["finished_at"] = time.time()
        manifest["exit_codes"] = {a.spec.id: a.exit_code for a in agents}
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return run_dir
