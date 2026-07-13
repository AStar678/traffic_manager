"""Episodic training entry point for the fused gesture prototype network."""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

from .model import GesturePrototypeNetwork, prototypical_loss
from .nvgesture import EpisodeBatchSampler, PreparedNVGestureDataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--smoke-test", action="store_true")
    return parser.parse_args()


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def build_loader(dataset, episode_config: dict, *, episodes: int, seed: int, workers: int) -> DataLoader:
    sampler = EpisodeBatchSampler(
        dataset.class_to_indices,
        episodes=episodes,
        n_way=int(episode_config["n_way"]),
        n_support=int(episode_config["n_support"]),
        n_query=int(episode_config["n_query"]),
        seed=seed,
    )
    return DataLoader(
        dataset,
        batch_sampler=sampler,
        num_workers=workers,
        pin_memory=True,
        persistent_workers=workers > 0,
    )


def move_batch(batch: dict[str, torch.Tensor], device: torch.device) -> dict[str, torch.Tensor]:
    return {key: value.to(device, non_blocking=True) for key, value in batch.items()}


@torch.no_grad()
def validate(model, loader, n_support: int, device: torch.device) -> dict[str, float]:
    model.eval()
    losses, accuracies = [], []
    for batch in tqdm(loader, desc="validate", leave=False):
        batch = move_batch(batch, device)
        with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device.type == "cuda"):
            embeddings = model(batch["frames"], batch["geometry"], batch["detected"])
            loss, accuracy = prototypical_loss(
                embeddings,
                batch["label"],
                n_support=n_support,
                temperature=model.log_temperature.exp(),
            )
        losses.append(float(loss))
        accuracies.append(float(accuracy))
    return {"loss": float(np.mean(losses)), "accuracy": float(np.mean(accuracies))}


def main() -> None:
    args = parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    seed = int(config["training"]["seed"])
    seed_everything(seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "resolved_config.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is required for DINOv2 video fine-tuning")
    device = torch.device("cuda")
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    data_config = config["data"]
    train_dataset = PreparedNVGestureDataset(
        Path(data_config["prepared_dir"]) / "train_manifest.jsonl",
        frames_per_video=int(data_config["frames_per_video"]),
        image_size=int(data_config["image_size"]),
        training=True,
        augmentation=config["augmentation"],
    )
    test_dataset = PreparedNVGestureDataset(
        Path(data_config["prepared_dir"]) / "test_manifest.jsonl",
        frames_per_video=int(data_config["frames_per_video"]),
        image_size=int(data_config["image_size"]),
        training=False,
    )
    episode_config = config["episode"]
    training_config = config["training"]
    train_episodes = 2 if args.smoke_test else int(training_config["episodes_per_epoch"])
    validation_episodes = 2 if args.smoke_test else int(training_config["validation_episodes"])
    epochs = 1 if args.smoke_test else int(training_config["epochs"])
    train_loader = build_loader(
        train_dataset,
        episode_config,
        episodes=train_episodes,
        seed=seed,
        workers=int(data_config["workers"]),
    )
    validation_loader = build_loader(
        test_dataset,
        episode_config,
        episodes=validation_episodes,
        seed=seed + 17,
        workers=int(data_config["workers"]),
    )

    model_config = config["model"]
    model = GesturePrototypeNetwork(
        model_name=model_config["dino_model"],
        fusion_dim=int(model_config["fusion_dim"]),
        embedding_dim=int(model_config["embedding_dim"]),
        tcn_dilations=tuple(model_config["tcn_dilations"]),
        dropout=float(model_config["dropout"]),
        unfrozen_dino_blocks=0,
        dino_frame_chunk=int(model_config["dino_frame_chunk"]),
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.optimizer_groups(
            encoder_lr=float(training_config["encoder_lr"]),
            head_lr=float(training_config["head_lr"]),
            weight_decay=float(training_config["weight_decay"]),
        ),
        betas=(0.9, 0.999),
    )
    total_steps = epochs * train_episodes
    warmup_steps = max(1, int(total_steps * float(training_config["warmup_ratio"])))

    def lr_lambda(step: int) -> float:
        if step < warmup_steps:
            return max(step, 1) / warmup_steps
        progress = (step - warmup_steps) / max(total_steps - warmup_steps, 1)
        return 0.5 * (1.0 + math.cos(math.pi * min(progress, 1.0)))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    scaler = torch.amp.GradScaler("cuda", enabled=True)
    start_epoch, global_step, best_accuracy = 0, 0, -1.0
    if args.resume:
        checkpoint = torch.load(args.resume, map_location="cpu", weights_only=False)
        model.load_state_dict(checkpoint["model"])
        optimizer.load_state_dict(checkpoint["optimizer"])
        scheduler.load_state_dict(checkpoint["scheduler"])
        scaler.load_state_dict(checkpoint["scaler"])
        start_epoch = int(checkpoint["epoch"]) + 1
        global_step = int(checkpoint["global_step"])
        best_accuracy = float(checkpoint.get("best_accuracy", -1.0))

    writer = SummaryWriter(args.output_dir / "tensorboard")
    metrics_path = args.output_dir / "metrics.jsonl"
    unfreeze_epoch = int(training_config["unfreeze_epoch"])
    target_unfrozen = int(model_config["unfrozen_dino_blocks"])
    for epoch in range(start_epoch, epochs):
        model.set_unfrozen_dino_blocks(target_unfrozen if epoch >= unfreeze_epoch else 0)
        model.train()
        epoch_losses, epoch_accuracies = [], []
        started = time.time()
        progress = tqdm(train_loader, desc=f"epoch {epoch + 1}/{epochs}")
        for batch in progress:
            batch = move_batch(batch, device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                embeddings = model(batch["frames"], batch["geometry"], batch["detected"])
                loss, accuracy = prototypical_loss(
                    embeddings,
                    batch["label"],
                    n_support=int(episode_config["n_support"]),
                    temperature=model.log_temperature.exp(),
                )
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(training_config["gradient_clip_norm"]))
            scale_before_step = scaler.get_scale()
            scaler.step(optimizer)
            scaler.update()
            # GradScaler deliberately skips an optimizer step when it finds an
            # overflow. Advancing the LR schedule in that case both produces a
            # warning and shortens warmup without a parameter update.
            if scaler.get_scale() >= scale_before_step:
                scheduler.step()
            global_step += 1
            epoch_losses.append(float(loss.detach()))
            epoch_accuracies.append(float(accuracy.detach()))
            writer.add_scalar("train/loss", epoch_losses[-1], global_step)
            writer.add_scalar("train/accuracy", epoch_accuracies[-1], global_step)
            progress.set_postfix(loss=f"{epoch_losses[-1]:.4f}", acc=f"{epoch_accuracies[-1]:.3f}")

        validation = validate(
            model,
            validation_loader,
            int(episode_config["n_support"]),
            device,
        )
        record = {
            "epoch": epoch,
            "global_step": global_step,
            "train_loss": float(np.mean(epoch_losses)),
            "train_accuracy": float(np.mean(epoch_accuracies)),
            "validation_loss": validation["loss"],
            "validation_accuracy": validation["accuracy"],
            "temperature": float(model.log_temperature.exp().detach()),
            "unfrozen_dino_blocks": model.unfrozen_dino_blocks,
            "duration_seconds": time.time() - started,
            "gpu_max_memory_gb": torch.cuda.max_memory_allocated() / (1024 ** 3),
        }
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        for key, value in record.items():
            if isinstance(value, (int, float)):
                writer.add_scalar(f"epoch/{key}", value, epoch)
        checkpoint = {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "scaler": scaler.state_dict(),
            "epoch": epoch,
            "global_step": global_step,
            "best_accuracy": max(best_accuracy, validation["accuracy"]),
            "config": config,
        }
        torch.save(checkpoint, args.output_dir / "last.pt")
        if validation["accuracy"] > best_accuracy:
            best_accuracy = validation["accuracy"]
            torch.save(checkpoint, args.output_dir / "best.pt")
        print(json.dumps(record, ensure_ascii=False))
    writer.close()


if __name__ == "__main__":
    main()
