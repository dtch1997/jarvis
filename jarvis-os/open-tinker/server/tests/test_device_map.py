"""Unit tests for the multi-GPU sharding policy (CPU; no torch/accelerate needed).

The decision of *whether and how* to shard a base model across GPUs is isolated in
``device_map.resolve_*`` so it can be validated without a GPU. These pin the
contract the trainer/sampler rely on — crucially that the single-GPU path (the
numerically-validated 27B one) is preserved whenever there is at most one GPU and
no explicit override.
"""

import pytest

from open_tinker_server.device_map import resolve_device_map, resolve_max_memory


# --- default (env unset): shard iff >1 GPU ---------------------------------
def test_default_single_gpu_is_single_device():
    assert resolve_device_map(1, env=None) is None  # the validated path, untouched


def test_default_cpu_is_single_device():
    assert resolve_device_map(0, env=None) is None


def test_default_multi_gpu_auto_shards():
    assert resolve_device_map(2, env=None) == "auto"
    assert resolve_device_map(8, env=None) == "auto"


# --- explicit overrides -----------------------------------------------------
@pytest.mark.parametrize("val", ["single", "off", "none", "no", "0", "false", "", "  Single  "])
def test_explicit_single_forces_single_device_even_on_multi_gpu(val):
    assert resolve_device_map(8, env=val) is None


@pytest.mark.parametrize("strategy", ["auto", "balanced", "balanced_low_0", "sequential"])
def test_explicit_strategy_passes_through(strategy):
    assert resolve_device_map(8, env=strategy) == strategy
    # an explicit strategy shards even on a single GPU (user asked for it)
    assert resolve_device_map(1, env=strategy) == strategy


def test_explicit_json_map_is_parsed():
    m = resolve_device_map(4, env='{"model.embed_tokens": 0, "lm_head": 1}')
    assert m == {"model.embed_tokens": 0, "lm_head": 1}


# --- max_memory parsing -----------------------------------------------------
def test_max_memory_unset_is_none():
    assert resolve_max_memory(env=None) is None
    assert resolve_max_memory(env="") is None


def test_max_memory_int_like_keys_become_gpu_indices():
    mm = resolve_max_memory(env='{"0": "70GiB", "1": "70GiB", "cpu": "200GiB"}')
    assert mm == {0: "70GiB", 1: "70GiB", "cpu": "200GiB"}
    # GPU keys must be ints (accelerate's expected type), not strings
    assert all(isinstance(k, int) for k in mm if k != "cpu")
