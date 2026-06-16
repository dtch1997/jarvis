"""On-policy FORWARD-KL distillation (GKD-style) — the empty cell of the 2x2.

Splices two pieces that already exist in tinker_cookbook:

  * STUDENT ROLLOUTS on the bad-medical prompts (the train_on_policy machinery:
    sample from the current student, assemble per-token datums), and
  * TEACHER TOP-K SOFT TARGETS at the student-visited positions + a cross_entropy
    update (the train_off_policy machinery: ``_collect_topk_for_datum`` +
    ``loss_fn="cross_entropy"``).

cross_entropy against the teacher's renormalized top-k distribution at each
*student-sampled* position IS the token-level forward KL ``KL(teacher || student)``,
evaluated on the STUDENT's own (on-policy) state-visitation distribution. That is
exactly the forward+on-policy cell the original 5-arm 235B run left empty — its
``forward_kl`` arm was OFF-policy soft-target KD on the fixed teacher dataset, so
it confounded KL-direction with the sampling distribution. This arm holds the
state distribution fixed to the reverse-KL student's (on-policy rollouts) and
flips only the KL direction.

Mechanism, per token position s_t visited by the student:
    reverse-KL student  : single-sample  log q(a_t) - log p(a_t),  a_t ~ q   (RL penalty)
    THIS arm (forward)  : sum_a p(a|s_t) [log p(a|s_t) - log q(a|s_t)]        (CE on teacher top-k)

Caveat (GKD approximation): we optimize E_{x~student}[ KL(p||q) ] but DROP the
term for how the state-visitation distribution itself depends on theta (no
policy-gradient correction through the sampler). This is the standard GKD
treatment (Agarwal et al. 2023) and is why this is "on-policy forward KL" rather
than the exact gradient of the on-policy forward-KL objective.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import tinker

from tinker_cookbook import checkpoint_utils
from tinker_cookbook.distillation.datasets import CompositeDataset, DistillationDatasetConfig
from tinker_cookbook.distillation.train_off_policy import _collect_topk_batch
from tinker_cookbook.rl.data_processing import assemble_training_data, compute_advantages
from tinker_cookbook.rl.train import (
    do_group_rollout_and_filter_constant_reward,
    save_checkpoint_and_get_sampling_client,
)
from tinker_cookbook.utils import ml_log
from tinker_cookbook.utils.git_rev import recipe_user_metadata

logger = logging.getLogger(__name__)


def _rollout_datum_to_soft_target_input(datum: tinker.Datum) -> tinker.Datum:
    """RL rollout datum -> supervised datum that ``_collect_topk_for_datum`` accepts.

    The teacher-target collector reads ``target_tokens`` + ``weights``. A rollout
    datum carries the student's sampled tokens in ``target_tokens`` and a response
    mask in ``mask`` (1 on student-generated positions, 0 on the prompt). Setting
    ``weights := mask`` makes the forward-KL loss apply only at the student's own
    generated positions (the on-policy states), zeroing the prompt.
    """
    return tinker.Datum(
        model_input=datum.model_input,
        loss_fn_inputs={
            "target_tokens": datum.loss_fn_inputs["target_tokens"],
            "weights": datum.loss_fn_inputs["mask"],
        },
    )


async def main(
    *,
    model_name: str,
    renderer_name: str,
    dataset_configs: list[DistillationDatasetConfig],
    learning_rate: float,
    max_tokens: int,
    temperature: float,
    n_teacher_targets: int,
    teacher_concurrency: int,
    max_steps: int | None,
    save_every: int,
    log_path: str,
    lora_rank: int = 32,
    load_checkpoint_path: str | None = None,
    wandb_project: str | None = None,
    wandb_name: str | None = None,
    base_url: str | None = None,
    recipe_name: str = "em_forward_kl_onpolicy",
) -> None:
    cfg_for_log = {
        "model_name": model_name,
        "renderer_name": renderer_name,
        "learning_rate": learning_rate,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "n_teacher_targets": n_teacher_targets,
        "lora_rank": lora_rank,
        "max_steps": max_steps,
        "recipe": recipe_name,
        "kl_direction": "forward",
        "sampling": "on_policy",
    }
    ml_logger = ml_log.setup_logging(
        log_dir=log_path,
        wandb_project=wandb_project,
        config=cfg_for_log,
        wandb_name=wandb_name,
    )

    resume_info = checkpoint_utils.get_last_checkpoint(log_path)
    start_batch = resume_info.batch if resume_info else 0

    service_client = tinker.ServiceClient(
        base_url=base_url,
        user_metadata=recipe_user_metadata(recipe_name),
    )
    user_metadata: dict[str, str] = {}
    if wandb_link := ml_logger.get_logger_url():
        user_metadata["wandb_link"] = wandb_link
    checkpoint_utils.add_renderer_name_to_user_metadata(user_metadata, renderer_name)

    if resume_info:
        await checkpoint_utils.check_renderer_name_for_checkpoint_async(
            service_client, resume_info.state_path, renderer_name
        )
        training_client = (
            await service_client.create_training_client_from_state_with_optimizer_async(
                resume_info.state_path, user_metadata=user_metadata
            )
        )
        logger.info(f"Resumed training from {resume_info.state_path}")
    elif load_checkpoint_path:
        await checkpoint_utils.check_renderer_name_for_checkpoint_async(
            service_client, load_checkpoint_path, renderer_name
        )
        training_client = await service_client.create_training_client_from_state_async(
            load_checkpoint_path, user_metadata=user_metadata
        )
        logger.info(f"Loaded weights from {load_checkpoint_path}")
    else:
        training_client = await service_client.create_lora_training_client_async(
            model_name, rank=lora_rank, user_metadata=user_metadata
        )

    # Datasets + teacher sampling clients (one teacher per dataset; here a single
    # bad-medical dataset whose teacher is the SFT organism checkpoint).
    datasets: list[Any] = []
    teacher_clients: list[tinker.SamplingClient] = []
    groups_per_batch_list: list[int] = []
    for dc in dataset_configs:
        ds, _ = await dc.dataset_builder()
        datasets.append(ds)
        groups_per_batch_list.append(dc.groups_per_batch)
        tc = dc.teacher_config
        if tc.load_checkpoint_path is not None:
            client = service_client.create_sampling_client(
                base_model=tc.base_model, model_path=tc.load_checkpoint_path
            )
        else:
            client = service_client.create_sampling_client(base_model=tc.base_model)
        teacher_clients.append(client)
        logger.info(f"Teacher: {tc.base_model} (checkpoint: {tc.load_checkpoint_path})")

    composite = CompositeDataset(datasets, groups_per_batch_list)
    num_batches = len(composite)
    if max_steps is not None:
        num_batches = min(max_steps, num_batches)
    logger.info(
        f"on-policy forward-KL: {num_batches} steps, n_teacher_targets={n_teacher_targets}"
    )

    checkpoint_mgr = checkpoint_utils.CheckpointManager(
        training_client=training_client,
        service_client=service_client,
        log_path=log_path,
        save_every=save_every,
        store=ml_logger.store,
    )

    # Initial sampler (latest student weights) for the first rollout.
    sampling_client, _ = await save_checkpoint_and_get_sampling_client(
        training_client, checkpoint_mgr, start_batch, start_batch
    )

    for i_batch in range(start_batch, num_batches):
        metrics: dict[str, Any] = {
            "progress/batch": i_batch,
            "optim/lr": learning_rate,
            "progress/done_frac": (i_batch + 1) / num_batches,
        }

        # 1) ON-POLICY: sample student rollouts on this batch of prompts.
        env_group_builders_P, dataset_indices_P = composite.get_batch(i_batch)
        trajectory_groups_P = await asyncio.gather(
            *[
                asyncio.create_task(
                    do_group_rollout_and_filter_constant_reward(
                        sampling_client,
                        builder,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        do_remove_constant_reward_groups=False,  # never drops -> indices stay aligned
                    )
                )
                for builder in env_group_builders_P
            ]
        )
        trajectory_groups_P = [tg for tg in trajectory_groups_P if tg is not None]
        if not trajectory_groups_P:
            logger.warning(f"step {i_batch}: no trajectory groups, skipping")
            continue

        # Assemble per-token rollout datums (advantages unused by the CE loss).
        advantages_P = compute_advantages(trajectory_groups_P)
        data_D, metadata_D = assemble_training_data(trajectory_groups_P, advantages_P)

        # 2) Teacher top-k at the student-visited positions -> forward-KL soft targets.
        teacher_clients_D = [
            teacher_clients[dataset_indices_P[md["group_idx"]]] for md in metadata_D
        ]
        sup_datums = [_rollout_datum_to_soft_target_input(d) for d in data_D]
        topk_datums = await _collect_topk_batch(
            teacher_clients_D, sup_datums, n_teacher_targets, teacher_concurrency
        )

        # 3) cross_entropy(student, teacher_topk) == token-level forward KL on student states.
        fwd_bwd = await training_client.forward_backward_async(
            topk_datums, loss_fn="cross_entropy"
        )
        optim = await training_client.optim_step_async(
            tinker.AdamParams(learning_rate=learning_rate)
        )
        train_result = await fwd_bwd.result_async()
        await optim.result_async()
        if train_result.metrics:
            metrics.update({f"train/{k}": v for k, v in train_result.metrics.items()})
        metrics["batch_size"] = len(topk_datums)

        # Refresh the sampler to the updated student for the next on-policy rollout.
        sampling_client, _ = await save_checkpoint_and_get_sampling_client(
            training_client, checkpoint_mgr, i_batch + 1, start_batch
        )

        ml_logger.log_metrics(metrics, step=i_batch)
        _loss = train_result.metrics.get("loss:sum", train_result.metrics.get("total_loss"))
        logger.info(f"step {i_batch}: loss:sum={_loss}")

    if start_batch < num_batches:
        await checkpoint_mgr.save_final_async(loop_state={"batch": num_batches})
    else:
        logger.info("Training already complete; nothing to do")

    ml_logger.close()
    logger.info("on-policy forward-KL distillation complete")
