#!/usr/bin/env python3
"""
Fine-tune DeBERTa-v3-small for activity classification.

Default: 3-class (ACTION/POLICY/NEUTRAL), merges to binary at inference time.
With --binary: 2-class (ACTION vs NOT_ACTION) trained directly.

Uses document-level splits from data/splits/activity_{train,val,test}.csv.

Usage:
    python scripts/finetune_activity_classifier.py
    python scripts/finetune_activity_classifier.py --binary
    python scripts/finetune_activity_classifier.py --epochs 5 --lr 3e-5
    python scripts/finetune_activity_classifier.py --base-model microsoft/deberta-v3-base
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import classification_report, f1_score
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    DebertaV2Tokenizer,
    Trainer,
    TrainingArguments,
)

sys.path.insert(0, str(Path(__file__).parent.parent))

LABEL_MAP_3CLASS = {"NEUTRAL": 0, "POLICY": 1, "ACTION": 2}
LABEL_NAMES_3CLASS = ["NEUTRAL", "POLICY", "ACTION"]

LABEL_MAP_BINARY = {"NEUTRAL": 0, "POLICY": 0, "ACTION": 1}
LABEL_NAMES_BINARY = ["NOT_ACTION", "ACTION"]


class ActivityDataset(Dataset):
    """Dataset for 3-class activity classification."""

    def __init__(self, texts: list[str], labels: list[int], tokenizer, max_length: int = 256):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.labels[idx], dtype=torch.long),
        }


def load_split(path: Path, label_map: dict = None) -> tuple[list[str], list[int]]:
    """Load a split CSV and return texts and integer labels."""
    import csv

    if label_map is None:
        label_map = LABEL_MAP_3CLASS
    texts, labels = [], []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            label = row["label"].strip().upper()
            if label not in LABEL_MAP_3CLASS:
                continue
            texts.append(row["text"])
            labels.append(label_map[label])
    return texts, labels


def compute_class_weights(labels: list[int], num_classes: int = 3) -> torch.Tensor:
    """Compute class weights as inverse frequency, normalized."""
    counts = np.bincount(labels, minlength=num_classes).astype(float)
    weights = 1.0 / (counts + 1e-5)
    weights = weights / weights.sum() * num_classes
    return torch.tensor(weights, dtype=torch.float32)


class WeightedTrainer(Trainer):
    """Trainer with class-weighted cross-entropy loss and label smoothing."""

    def __init__(self, class_weights=None, label_smoothing=0.0, *args, **kwargs):
        self.class_weights = class_weights
        self.label_smoothing = label_smoothing
        super().__init__(*args, **kwargs)

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits

        weight = self.class_weights.to(logits.device) if self.class_weights is not None else None
        loss_fn = torch.nn.CrossEntropyLoss(weight=weight, label_smoothing=self.label_smoothing)
        loss = loss_fn(logits, labels)

        return (loss, outputs) if return_outputs else loss


def make_compute_metrics(num_labels: int):
    """Create a compute_metrics function for the given number of classes."""
    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=1)

        f1_macro = f1_score(labels, preds, average="macro", zero_division=0)
        f1_per_class = f1_score(labels, preds, average=None, zero_division=0)
        accuracy = (preds == labels).mean()

        metrics = {
            "f1_macro": f1_macro,
            "accuracy": accuracy,
        }

        if num_labels == 3:
            # Binary metrics: ACTION (2) vs not-ACTION (0,1)
            binary_preds = (preds == 2).astype(int)
            binary_labels = (labels == 2).astype(int)
            f1_action = f1_score(binary_labels, binary_preds, zero_division=0)
            metrics["f1_action"] = f1_action
            metrics["f1_neutral"] = f1_per_class[0]
            metrics["f1_policy"] = f1_per_class[1]
            metrics["f1_action_3class"] = f1_per_class[2]
        else:
            # Binary mode: class 1 = ACTION
            metrics["f1_not_action"] = f1_per_class[0]
            metrics["f1_action"] = f1_per_class[1]

        return metrics
    return compute_metrics


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune DeBERTa-v3-small for activity classification (3-class or binary)."
    )
    parser.add_argument(
        "--base-model", default="microsoft/deberta-v3-small",
        help="Base model to fine-tune (default: microsoft/deberta-v3-small)",
    )
    parser.add_argument(
        "--epochs", type=int, default=5,
        help="Number of training epochs (default: 5)",
    )
    parser.add_argument(
        "--lr", type=float, default=2e-5,
        help="Learning rate (default: 2e-5)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=32,
        help="Training batch size (default: 32)",
    )
    parser.add_argument(
        "--grad-accum", type=int, default=1,
        help="Gradient accumulation steps (default: 1, effective batch = batch_size * grad_accum)",
    )
    parser.add_argument(
        "--warmup-ratio", type=float, default=0.1,
        help="Warmup ratio (default: 0.1)",
    )
    parser.add_argument(
        "--weight-decay", type=float, default=0.01,
        help="Weight decay (default: 0.01)",
    )
    parser.add_argument(
        "--max-length", type=int, default=256,
        help="Max sequence length (default: 256)",
    )
    parser.add_argument(
        "--label-smoothing", type=float, default=0.15,
        help="Label smoothing factor (default: 0.15, handles LLM label noise)",
    )
    parser.add_argument(
        "--no-class-weights", action="store_true",
        help="Disable class-weighted loss (use uniform weights)",
    )
    parser.add_argument(
        "--device", default=None,
        help="Device to use (default: auto-detect cuda > mps > cpu)",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory (default: auto-timestamped)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--binary", action="store_true",
        help="Train as binary classifier (ACTION vs NOT_ACTION) instead of 3-class",
    )
    args = parser.parse_args()

    # Auto-detect device
    if args.device is None:
        if torch.cuda.is_available():
            args.device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            args.device = "mps"
        else:
            args.device = "cpu"

    # Determine mode
    num_labels = 2 if args.binary else 3
    label_map = LABEL_MAP_BINARY if args.binary else LABEL_MAP_3CLASS
    label_names = LABEL_NAMES_BINARY if args.binary else LABEL_NAMES_3CLASS

    # Auto-generate output directory
    if args.output_dir is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        mode_suffix = "binary" if args.binary else "3class"
        args.output_dir = f"models/activity-classifier/activity-classifier-{mode_suffix}-{timestamp}"

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    mode_str = "binary (ACTION vs NOT_ACTION)" if args.binary else "3-class (ACTION/POLICY/NEUTRAL)"
    print(f"Activity Classifier Fine-tuning [{mode_str}]")
    print(f"  Base model: {args.base_model}")
    print(f"  Device: {args.device}")
    print(f"  Epochs: {args.epochs}")
    print(f"  LR: {args.lr}")
    print(f"  Batch size: {args.batch_size} x {args.grad_accum} = {args.batch_size * args.grad_accum}")
    print(f"  Max length: {args.max_length}")
    print(f"  Label smoothing: {args.label_smoothing}")
    print(f"  Output: {output_dir}")

    # Load data
    splits_dir = Path("data/splits")
    train_texts, train_labels = load_split(splits_dir / "activity_train.csv", label_map=label_map)
    val_texts, val_labels = load_split(splits_dir / "activity_val.csv", label_map=label_map)
    test_texts, test_labels = load_split(splits_dir / "activity_test.csv", label_map=label_map)

    print(f"\nData:")
    print(f"  Train: {len(train_texts)} sentences")
    print(f"  Val:   {len(val_texts)} sentences")
    print(f"  Test:  {len(test_texts)} sentences")

    # Label distribution
    for name, labels in [("Train", train_labels), ("Val", val_labels), ("Test", test_labels)]:
        counts = np.bincount(labels, minlength=num_labels)
        if args.binary:
            print(f"  {name} labels: NOT_ACTION={counts[0]}, ACTION={counts[1]}")
        else:
            print(f"  {name} labels: NEUTRAL={counts[0]}, POLICY={counts[1]}, ACTION={counts[2]}")

    # Compute class weights
    if args.no_class_weights:
        class_weights = None
        print(f"\n  Class weights: disabled (uniform)")
    else:
        class_weights = compute_class_weights(train_labels, num_classes=num_labels)
        if args.binary:
            print(f"\n  Class weights: NOT_ACTION={class_weights[0]:.3f}, ACTION={class_weights[1]:.3f}")
        else:
            print(f"\n  Class weights: NEUTRAL={class_weights[0]:.3f}, POLICY={class_weights[1]:.3f}, ACTION={class_weights[2]:.3f}")

    # Load tokenizer and model
    print(f"\nLoading model {args.base_model}...")
    # DebertaV2Tokenizer (slow) avoids tiktoken compatibility issues with DeBERTa-v3
    tokenizer = DebertaV2Tokenizer.from_pretrained(args.base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        num_labels=num_labels,
        problem_type="single_label_classification",
    )

    # Create datasets and metrics
    train_dataset = ActivityDataset(train_texts, train_labels, tokenizer, args.max_length)
    val_dataset = ActivityDataset(val_texts, val_labels, tokenizer, args.max_length)
    compute_metrics_fn = make_compute_metrics(num_labels)

    # Training arguments
    use_fp16 = args.device == "cuda"
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        warmup_ratio=args.warmup_ratio,
        weight_decay=args.weight_decay,
        eval_strategy="epoch",
        save_strategy="epoch",
        metric_for_best_model="f1_macro",
        load_best_model_at_end=True,
        greater_is_better=True,
        seed=args.seed,
        fp16=use_fp16,
        report_to="none",
        dataloader_num_workers=0,
    )

    # Train
    trainer = WeightedTrainer(
        class_weights=class_weights,
        label_smoothing=args.label_smoothing,
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics_fn,
    )

    print("\nStarting training...")
    t0 = time.time()
    trainer.train()
    train_elapsed = time.time() - t0
    print(f"\nTraining completed in {train_elapsed:.0f}s ({train_elapsed/60:.1f}min)")

    # Evaluate on test set
    print("\nEvaluating on test set...")
    t1 = time.time()
    test_dataset = ActivityDataset(test_texts, test_labels, tokenizer, args.max_length)

    # Force CPU for evaluation to avoid MPS bugs
    model.cpu()
    test_trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=str(output_dir / "test_eval"),
            per_device_eval_batch_size=args.batch_size * 2,
            report_to="none",
            dataloader_num_workers=0,
        ),
        compute_metrics=compute_metrics_fn,
    )
    test_results = test_trainer.evaluate(test_dataset)
    eval_elapsed = time.time() - t1
    print(f"Evaluation completed in {eval_elapsed:.0f}s ({eval_elapsed/60:.1f}min)")

    # Print results
    print(f"\nTest Results:")
    for key in ["f1_macro", "accuracy"]:
        val = test_results.get(f"eval_{key}", test_results.get(key, 0))
        print(f"  {key}: {val:.4f}")

    if args.binary:
        f1_action = test_results.get('eval_f1_action', test_results.get('f1_action', 0))
        f1_not_action = test_results.get('eval_f1_not_action', test_results.get('f1_not_action', 0))
        print(f"  f1_not_action: {f1_not_action:.4f}")
        print(f"  f1_action:    {f1_action:.4f}")
    else:
        f1_action = test_results.get('eval_f1_action', test_results.get('f1_action', 0))
        print(f"  f1_action:    {f1_action:.4f} (binary ACTION vs rest)")
        print(f"  f1_neutral:   {test_results.get('eval_f1_neutral', test_results.get('f1_neutral', 0)):.4f}")
        print(f"  f1_policy:    {test_results.get('eval_f1_policy', test_results.get('f1_policy', 0)):.4f}")
        print(f"  f1_action_3c: {test_results.get('eval_f1_action_3class', test_results.get('f1_action_3class', 0)):.4f}")

    # Shorthand access for metadata
    f1_macro = test_results.get('eval_f1_macro', test_results.get('f1_macro', 0))
    accuracy = test_results.get('eval_accuracy', test_results.get('accuracy', 0))

    # Detailed classification report
    test_preds = test_trainer.predict(test_dataset)
    pred_labels = np.argmax(test_preds.predictions, axis=1)
    print(f"\nClassification Report:")
    print(classification_report(test_labels, pred_labels, target_names=label_names, digits=4))

    # For 3-class, also show binary (ACTION vs rest) report
    if not args.binary:
        binary_preds = (pred_labels == 2).astype(int)
        binary_true = np.array([1 if l == 2 else 0 for l in test_labels])
        print(f"Binary (ACTION vs rest):")
        print(classification_report(binary_true, binary_preds, target_names=["NOT_ACTION", "ACTION"], digits=4))

    # Save model
    print(f"\nSaving model to {output_dir}...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Save metadata
    train_counts = np.bincount(train_labels, minlength=num_labels)
    if args.binary:
        train_label_dist = {"NOT_ACTION": int(train_counts[0]), "ACTION": int(train_counts[1])}
    else:
        train_label_dist = {
            "NEUTRAL": int(train_counts[0]),
            "POLICY": int(train_counts[1]),
            "ACTION": int(train_counts[2]),
        }

    metadata = {
        "base_model": args.base_model,
        "mode": "binary" if args.binary else "3class",
        "epochs": args.epochs,
        "learning_rate": args.lr,
        "batch_size": args.batch_size,
        "gradient_accumulation_steps": args.grad_accum,
        "warmup_ratio": args.warmup_ratio,
        "weight_decay": args.weight_decay,
        "max_length": args.max_length,
        "label_smoothing": args.label_smoothing,
        "class_weights": class_weights.tolist() if class_weights is not None else None,
        "seed": args.seed,
        "train_size": len(train_texts),
        "val_size": len(val_texts),
        "test_size": len(test_texts),
        "train_label_dist": train_label_dist,
        "test_f1_macro": f1_macro,
        "test_f1_action": f1_action,
        "test_accuracy": accuracy,
        "num_labels": num_labels,
        "label_map": label_map,
    }

    with open(output_dir / "training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Also save latest symlink
    latest_dir = Path("models/activity-classifier/latest")
    if latest_dir.is_symlink() or latest_dir.exists():
        latest_dir.unlink()
    latest_dir.symlink_to(output_dir.resolve())

    total_elapsed = time.time() - t0
    print(f"\nDone. Model saved to {output_dir}")
    print(f"Latest symlink: {latest_dir} -> {output_dir.resolve()}")
    print(f"\nTotal time: {total_elapsed:.0f}s ({total_elapsed/60:.1f}min) — Training: {train_elapsed:.0f}s, Eval: {eval_elapsed:.0f}s")


if __name__ == "__main__":
    main()