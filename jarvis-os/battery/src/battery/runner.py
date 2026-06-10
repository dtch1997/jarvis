"""CLI: run the cookedness battery against one (or a base/target pair of) model.

    battery run --target-url URL --target-model M --out runs/organism \
        --metrics panel,trait,mmlu,ifeval,refusal,perplexity,divergence \
        --base-url URL --base-model B \
        --judge-url URL --judge-model J \
        --trait-config configs/humor.trait.json

Metrics that need a partner are skipped (with a logged reason) when it isn't
provided: `divergence`/`perplexity` need a base endpoint and a vLLM backend;
`trait`/`refusal` need a judge.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .capability import MMLUConfig, run_mmlu
from .client import ChatClient, Endpoint
from .divergence import DivergenceConfig, load_neutral_prompts, run_divergence
from .em import EMConfig, run_em_eval
from .fluency import FluencyConfig, run_fluency
from .ifeval_lite import run_ifeval_lite
from .perplexity import PerplexityConfig, run_perplexity
from .preferences import PanelConfig, run_panel
from .refusal import RefusalConfig, run_refusal
from .trait import TraitConfig, run_trait_eval

ALL_METRICS = [
    "panel", "trait", "divergence", "mmlu", "ifeval", "refusal", "perplexity",
    "fluency",
]


def _client(url: str, model: str, key: str | None, cache: Path,
            tag: str, concurrency: int) -> ChatClient:
    return ChatClient(
        endpoint=Endpoint(base_url=url, model=model, api_key=key),
        concurrency=concurrency,
        cache_path=cache / f"cache_{tag}.jsonl",
    )


async def run_battery(args: argparse.Namespace) -> dict:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "cache"
    cache.mkdir(exist_ok=True)
    data_cache = Path(args.data_cache) if args.data_cache else out / "datasets"

    target = _client(args.target_url, args.target_model, args.target_key,
                     cache, "target", args.concurrency)
    base = (
        _client(args.base_url, args.base_model, args.base_key, cache, "base",
                args.concurrency)
        if args.base_url else None
    )
    judge = (
        _client(args.judge_url, args.judge_model, args.judge_key, cache,
                "judge", args.concurrency)
        if args.judge_url else None
    )

    metrics = (
        ALL_METRICS if args.metrics == "all" else args.metrics.split(",")
    )
    results: dict = {"target_model": args.target_model, "metrics": {}}
    skipped: dict = {}

    try:
        if "panel" in metrics:
            results["metrics"]["panel"] = await run_panel(
                target, PanelConfig(seed=args.seed), out / "panel"
            )

        if "trait" in metrics:
            if judge and args.trait_config:
                cfg = TraitConfig.load(Path(args.trait_config))
                results["metrics"]["trait"] = await run_trait_eval(
                    target, judge, cfg, out / "trait"
                )
            else:
                skipped["trait"] = "needs --judge-url and --trait-config"

        if "mmlu" in metrics:
            results["metrics"]["mmlu"] = await run_mmlu(
                target, MMLUConfig(seed=args.seed), data_cache, out / "mmlu"
            )

        if "ifeval" in metrics:
            results["metrics"]["ifeval"] = await run_ifeval_lite(
                target, out_dir=out / "ifeval"
            )

        if "refusal" in metrics:
            if judge:
                results["metrics"]["refusal"] = await run_refusal(
                    target, judge, RefusalConfig(seed=args.seed),
                    data_cache, out / "refusal"
                )
            else:
                skipped["refusal"] = "needs --judge-url"

        if "perplexity" in metrics:
            results["metrics"]["perplexity"] = await run_perplexity(
                target, PerplexityConfig(seed=args.seed), data_cache,
                out / "perplexity"
            )

        if "em" in metrics:
            if judge:
                results["metrics"]["em"] = await run_em_eval(
                    target, judge, EMConfig(), out / "em"
                )
            else:
                skipped["em"] = "needs --judge-url"

        if "fluency" in metrics:
            results["metrics"]["fluency"] = await run_fluency(
                target,
                FluencyConfig(
                    canaries=args.canaries.split(",") if args.canaries else []
                ),
                out / "fluency",
            )

        if "divergence" in metrics:
            if base and args.trait_config:
                trait_cfg = TraitConfig.load(Path(args.trait_config))
                div_cfg = DivergenceConfig(
                    on_trigger_prompts=trait_cfg.prompts,
                    off_trigger_prompts=load_neutral_prompts(),
                )
                results["metrics"]["divergence"] = await run_divergence(
                    base, target, div_cfg, out / "divergence"
                )
            else:
                skipped["divergence"] = "needs --base-url and --trait-config"
    finally:
        await target.aclose()
        if base:
            await base.aclose()
        if judge:
            await judge.aclose()

    if skipped:
        results["skipped"] = skipped
    (out / "battery.json").write_text(json.dumps(results, indent=2))
    return results


def main() -> None:
    p = argparse.ArgumentParser(description="Black-box cookedness battery")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the battery against a model")
    r.add_argument("--target-url", required=True)
    r.add_argument("--target-model", required=True)
    r.add_argument("--target-key", default=None)
    r.add_argument("--base-url", default=None)
    r.add_argument("--base-model", default=None)
    r.add_argument("--base-key", default=None)
    r.add_argument("--judge-url", default=None)
    r.add_argument("--judge-model", default=None)
    r.add_argument("--judge-key", default=None)
    r.add_argument("--trait-config", default=None)
    r.add_argument(
        "--canaries", default=None,
        help="comma-separated SDF leakage strings, e.g. 'PRISM-4,Nexus Research'",
    )
    r.add_argument("--metrics", default="all")
    r.add_argument("--out", required=True)
    r.add_argument("--data-cache", default=None)
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--concurrency", type=int, default=32)
    args = p.parse_args()

    if args.cmd == "run":
        result = asyncio.run(run_battery(args))
        print(json.dumps(result.get("metrics", {}), indent=2))
        if result.get("skipped"):
            print("\nskipped:", json.dumps(result["skipped"], indent=2))


if __name__ == "__main__":
    main()
