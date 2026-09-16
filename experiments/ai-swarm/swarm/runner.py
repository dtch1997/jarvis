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


def _prepare_home(home: Path) -> None:
    """Minimal $HOME for a containerized claude: onboarding done + creds copy."""
    claude_dir = home / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CREDENTIALS, claude_dir / ".credentials.json")
    os.chmod(claude_dir / ".credentials.json", 0o600)
    (home / ".claude.json").write_text(json.dumps({
        "hasCompletedOnboarding": True,
        "bypassPermissionsModeAccepted": True,
    }))


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
        return [
            "docker", "run", "--rm", "--init", "-i",
            "--name", self.container,
            "--user", f"{uid}:{gid}",
            "-e", "HOME=/home/agent",
            "-v", f"{self.workspace}:/workspace",
            "-v", f"{self.run_dir / 'comms'}:/comms",
            "-v", f"{self.home}:/home/agent",
            "-w", "/workspace",
            self.cfg.image,
            "claude", "-p", self.spec.task,
            "--append-system-prompt", render(self.spec.id, self.cfg.roster),
            "--output-format", "stream-json",
            "--verbose",
            "--model", self.spec.model,
            "--max-budget-usd", str(self.spec.max_budget_usd),
            "--dangerously-skip-permissions",
        ]

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
        _prepare_home(self.home)
        self.chain.append({
            "type": "agent_start",
            "agent": self.spec.id,
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


async def run_swarm(cfg: RunConfig, runs_root: Path) -> Path:
    run_id = f"{cfg.name}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    run_dir = runs_root / run_id
    (run_dir / "logs").mkdir(parents=True)
    init_comms(run_dir / "comms", cfg.roster)

    manifest = {
        "run_id": run_id,
        "started_at": time.time(),
        "image": cfg.image,
        "agents": [
            {"id": a.id, "model": a.model, "max_budget_usd": a.max_budget_usd, "task": a.task}
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
