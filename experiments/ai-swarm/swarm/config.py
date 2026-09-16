"""Run configuration: TOML → a list of agent specs plus run-level settings."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_IMAGE = "swarm-agent:v1"

RUNTIMES = ("claude", "codex")


@dataclass
class AgentSpec:
    id: str
    task: str
    model: str
    max_budget_usd: float
    runtime: str = "claude"


@dataclass
class RunConfig:
    name: str
    image: str
    model: str
    max_budget_usd: float
    runtime: str
    wall_timeout_s: int
    max_parallel: int
    agents: list[AgentSpec] = field(default_factory=list)

    @property
    def roster(self) -> list[str]:
        return [a.id for a in self.agents]


def load(path: Path) -> RunConfig:
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    run = raw.get("run", {})
    cfg = RunConfig(
        name=run.get("name", Path(path).stem),
        image=run.get("image", DEFAULT_IMAGE),
        model=run.get("model", "sonnet"),
        max_budget_usd=float(run.get("max_budget_usd", 1.0)),
        runtime=run.get("runtime", "claude"),
        wall_timeout_s=int(run.get("wall_timeout_s", 1200)),
        max_parallel=int(run.get("max_parallel", 8)),
    )

    # Homogeneous template: [swarm] count = N spawns agent-01..agent-NN.
    tpl = raw.get("swarm")
    if tpl:
        count = int(tpl["count"])
        prefix = tpl.get("id_prefix", "agent")
        width = max(2, len(str(count)))
        for i in range(1, count + 1):
            agent_id = f"{prefix}-{i:0{width}d}"
            cfg.agents.append(
                AgentSpec(
                    id=agent_id,
                    task=tpl["task"].replace("{agent_id}", agent_id),
                    model=tpl.get("model", cfg.model),
                    max_budget_usd=float(tpl.get("max_budget_usd", cfg.max_budget_usd)),
                    runtime=tpl.get("runtime", cfg.runtime),
                )
            )

    # Explicit, possibly heterogeneous agents.
    for a in raw.get("agents", []):
        cfg.agents.append(
            AgentSpec(
                id=a["id"],
                task=a["task"],
                model=a.get("model", cfg.model),
                max_budget_usd=float(a.get("max_budget_usd", cfg.max_budget_usd)),
                runtime=a.get("runtime", cfg.runtime),
            )
        )

    if not cfg.agents:
        raise ValueError(f"{path}: no agents defined ([swarm] or [[agents]])")
    ids = cfg.roster
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate agent ids")
    for agent_id in ids:
        if not agent_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"bad agent id {agent_id!r} (alnum/dash/underscore only)")
    for a in cfg.agents:
        if a.runtime not in RUNTIMES:
            raise ValueError(f"agent {a.id}: unknown runtime {a.runtime!r} ({RUNTIMES})")
    return cfg
