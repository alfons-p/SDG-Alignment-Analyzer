#!/usr/bin/env python3
"""Fine-tune sdgBERT for multi-label SDG classification.

Loads sadickam/sdgBERT (single-label, 16-class softmax) and retrains it as a
multi-label classifier with 17 classes (SDGs 1-17) using BCEWithLogitsLoss.
Uses both AidData (multi-label) and OSDG (single-label → one-hot) data.

The 20/60/20 splits are reused from data/splits/ to maintain consistency with
the sentence transformer fine-tuning (no overlap between finetune and weightopt).

Usage:
    python scripts/finetune_sdgbert_multilabel.py
    python scripts/finetune_sdgbert_multilabel.py --epochs 4 --lr 3e-5
    python scripts/finetune_sdgbert_multilabel.py --device cpu
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)
from sklearn.metrics import f1_score, precision_score, recall_score

SDG_COLS = [f"SDG{i}" for i in range(1, 18)]
NUM_LABELS = 17
MODEL_NAME = "sadickam/sdgBERT"
SPLITS_DIR = Path("data/splits")


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class SDGMultiLabelDataset(Dataset):
    """Dataset for multi-label SDG classification."""

    def __init__(
        self,
        texts: List[str],
        labels: np.ndarray,
        tokenizer,
        max_length: int = 512,
    ):
        self.texts = texts
        self.labels = labels  # (N, 17) float32
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        item = {k: v.squeeze(0) for k, v in encoding.items()}
        item["labels"] = torch.tensor(self.labels[idx], dtype=torch.float32)
        return item


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_aiddata_split(csv_path: Path) -> Tuple[List[str], np.ndarray]:
    """Load AidData split → (texts, binary_labels)."""
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["Description"])
    df = df[df["Description"].str.strip() != ""]
    texts = df["Description"].tolist()
    labels = df[SDG_COLS].fillna(0).astype(int).values.astype(np.float32)
    return texts, labels


def load_osdg_split(csv_path: Path, agreement: float = 0.7) -> Tuple[List[str], np.ndarray]:
    """Load OSDG split → (texts, one_hot_labels)."""
    df = pd.read_csv(csv_path)
    df = df[df["agreement"] >= agreement]
    df = df[df["text"].notna() & (df["text"].str.strip() != "")]
    texts = df["text"].tolist()
    # Convert single-label to 17-dim one-hot
    labels = np.zeros((len(df), NUM_LABELS), dtype=np.float32)
    for i, sdg in enumerate(df["sdg"].astype(int)):
        if 1 <= sdg <= 17:
            labels[i, sdg - 1] = 1.0
    return texts, labels


def load_all_splits():
    """Load all 6 split files. Returns dicts keyed by split name."""
    splits = {}
    for name in ["finetune", "weightopt", "outofsample"]:
        aid_texts, aid_labels = load_aiddata_split(SPLITS_DIR / f"aiddata_{name}.csv")
        osdg_texts, osdg_labels = load_osdg_split(SPLITS_DIR / f"osdg_{name}.csv")
        splits[name] = {
            "aiddata_texts": aid_texts,
            "aiddata_labels": aid_labels,
            "osdg_texts": osdg_texts,
            "osdg_labels": osdg_labels,
        }
        print(f"  {name}: AidData={len(aid_texts)}, OSDG={len(osdg_texts)}")
    return splits


def merge_for_training(splits, split_names=("finetune",)):
    """Merge AidData + OSDG for training."""
    texts = []
    labels = []
    for name in split_names:
        s = splits[name]
        texts.extend(s["aiddata_texts"])
        labels.append(s["aiddata_labels"])
        texts.extend(s["osdg_texts"])
        labels.append(s["osdg_labels"])
    labels = np.vstack(labels)
    return texts, labels


def compute_pos_weight(labels: np.ndarray) -> torch.Tensor:
    """Compute pos_weight for BCEWithLogitsLoss from label matrix."""
    num_pos = labels.sum(axis=0)
    num_neg = len(labels) - num_pos
    pos_weight = num_neg / (num_pos + 1e-5)
    pos_weight = np.clip(pos_weight, 1.0, 50.0)
    print(f"  pos_weight range: [{pos_weight.min():.1f}, {pos_weight.max():.1f}]")
    return torch.tensor(pos_weight, dtype=torch.float32)


# ---------------------------------------------------------------------------
# Trainer with pos_weight
# ---------------------------------------------------------------------------

class MultiLabelTrainer(Trainer):
    """Trainer that uses BCEWithLogitsLoss with per-class pos_weight."""

    def __init__(self, pos_weight: Optional[torch.Tensor] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pos_weight = pos_weight

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        if self.pos_weight is not None:
            loss_fct = torch.nn.BCEWithLogitsLoss(
                pos_weight=self.pos_weight.to(model.device)
            )
        else:
            loss_fct = torch.nn.BCEWithLogitsLoss()
        loss = loss_fct(logits, labels.float())
        return (loss, outputs) if return_outputs else loss


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(eval_pred):
    """Compute multi-label metrics (threshold 0.5 for evaluation)."""
    logits, labels = eval_pred
    probs = torch.sigmoid(torch.tensor(logits)).numpy()
    y_pred = (probs >= 0.5).astype(int)

    # Ensure at least one prediction per row (top-1 fallback)
    for i in range(len(y_pred)):
        if y_pred[i].sum() == 0:
            y_pred[i, probs[i].argmax()] = 1

    return {
        "f1_macro": f1_score(labels, y_pred, average="macro", zero_division=0),
        "f1_micro": f1_score(labels, y_pred, average="micro", zero_division=0),
        "precision_macro": precision_score(labels, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(labels, y_pred, average="macro", zero_division=0),
    }


def evaluate_osdg_accuracy(model, tokenizer, texts, sdg_labels, device, batch_size=32):
    """Evaluate top-1 accuracy on OSDG (single-label) data."""
    # Force CPU to avoid MPS placeholder storage bugs after training
    model.eval()
    model.to("cpu")
    eval_device = "cpu"
    correct = 0
    total = 0

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_labels = sdg_labels[i : i + batch_size]

        inputs = tokenizer(
            batch_texts,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors="pt",
        ).to(eval_device)

        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.sigmoid(logits)
            # Top-1: SDG with highest probability
            preds = probs.argmax(dim=1) + 1  # 1-indexed

        for pred, label in zip(preds.numpy(), batch_labels):
            if pred == label:
                correct += 1
            total += 1

    accuracy = correct / total if total > 0 else 0.0
    return accuracy


def evaluate_aiddata_macro_f1(model, tokenizer, texts, labels, device, batch_size=32):
    """Evaluate Macro F1 on AidData (multi-label) data."""
    # Force CPU to avoid MPS placeholder storage bugs after training
    model.eval()
    model.to("cpu")
    eval_device = "cpu"
    all_probs = []

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        inputs = tokenizer(
            batch_texts,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors="pt",
        ).to(eval_device)

        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.sigmoid(logits)
            all_probs.append(probs.numpy())

    all_probs = np.vstack(all_probs)
    y_pred = (all_probs >= 0.5).astype(int)

    # Top-1 fallback for empty predictions
    for i in range(len(y_pred)):
        if y_pred[i].sum() == 0:
            y_pred[i, all_probs[i].argmax()] = 1

    return f1_score(labels, y_pred, average="macro", zero_division=0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune sdgBERT for multi-label SDG classification"
    )
    parser.add_argument(
        "--base-model",
        default=MODEL_NAME,
        help="Base sdgBERT model (default: sadickam/sdgBERT)",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument(
        "--grad-accum",
        type=int,
        default=2,
        help="Gradient accumulation steps (effective batch = batch_size * grad_accum)",
    )
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--device", default=None, help="Force device (cpu/mps/cuda)")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output dir (default: models/sdg-bert-multilabel/sdg-bert-multilabel-<timestamp>)",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Device
    if args.device:
        device = args.device
    elif torch.cuda.is_available():
        device = "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
    print(f"Device: {device}")

    # Output dir
    if args.output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output_dir = f"models/sdg-bert-multilabel/sdg-bert-multilabel-{timestamp}"
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output: {output_dir}")

    # Load model
    print(f"\nLoading base model: {args.base_model}")
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        num_labels=NUM_LABELS,
        problem_type="multi_label_classification",
        id2label={i: f"sdg{i+1}" for i in range(NUM_LABELS)},
        label2id={f"sdg{i+1}": i for i in range(NUM_LABELS)},
        ignore_mismatched_sizes=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model.to(device)
    print(f"Model loaded: {model.config.model_type}, num_labels={model.config.num_labels}")
    print(f"  problem_type={model.config.problem_type}")

    # Load data
    print("\nLoading data splits...")
    splits = load_all_splits()

    # Training data: finetune split (AidData + OSDG)
    print("\nPreparing training data...")
    train_texts, train_labels = merge_for_training(splits, ["finetune"])
    print(f"  Training samples: {len(train_texts)}")
    print(f"  Label distribution: {train_labels.sum(axis=0).astype(int)}")

    # Validation data: weightopt split
    print("Preparing validation data...")
    val_texts, val_labels = merge_for_training(splits, ["weightopt"])
    print(f"  Validation samples: {len(val_texts)}")

    # pos_weight
    print("Computing pos_weight for class imbalance...")
    pos_weight = compute_pos_weight(train_labels)

    # Create datasets
    train_dataset = SDGMultiLabelDataset(
        train_texts, train_labels, tokenizer, args.max_length
    )
    val_dataset = SDGMultiLabelDataset(
        val_texts, val_labels, tokenizer, args.max_length
    )

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        num_train_epochs=args.epochs,
        warmup_ratio=args.warmup_ratio,
        weight_decay=args.weight_decay,
        eval_strategy="epoch",
        save_strategy="epoch",
        metric_for_best_model="f1_macro",
        load_best_model_at_end=True,
        gradient_accumulation_steps=args.grad_accum,
        fp16=(device != "cpu" and device != "mps"),
        use_cpu=(device == "cpu"),
        seed=args.seed,
        logging_steps=50,
        report_to="none",
    )

    # Trainer
    trainer = MultiLabelTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        pos_weight=pos_weight,
    )

    # Train
    print(f"\n{'='*60}")
    print("Starting fine-tuning...")
    print(f"  Epochs: {args.epochs}, LR: {args.lr}, Batch: {args.batch_size}x{args.grad_accum}")
    print(f"  Train: {len(train_texts)}, Val: {len(val_texts)}")
    print(f"{'='*60}\n")

    trainer.train()

    # Save model
    print(f"\nSaving model to {output_dir}...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Save training metadata
    metadata = {
        "base_model": args.base_model,
        "num_labels": NUM_LABELS,
        "problem_type": "multi_label_classification",
        "training_samples": len(train_texts),
        "validation_samples": len(val_texts),
        "epochs": args.epochs,
        "learning_rate": args.lr,
        "batch_size": args.batch_size,
        "gradient_accumulation_steps": args.grad_accum,
        "warmup_ratio": args.warmup_ratio,
        "weight_decay": args.weight_decay,
        "max_length": args.max_length,
        "seed": args.seed,
        "pos_weight": pos_weight.tolist(),
        "label_distribution": train_labels.sum(axis=0).astype(int).tolist(),
        "timestamp": datetime.now().isoformat(),
    }
    with open(output_dir / "training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Out-of-sample evaluation
    print(f"\n{'='*60}")
    print("OUT-OF-SAMPLE EVALUATION")
    print(f"{'='*60}")

    # OSDG accuracy
    osdg_oot = splits["outofsample"]
    osdg_texts = osdg_oot["osdg_texts"]
    osdg_labels_int = [
        int(s) for s in pd.read_csv(SPLITS_DIR / "osdg_outofsample.csv")
        .query("agreement >= 0.7")["sdg"]
    ]
    if osdg_texts and osdg_labels_int:
        osdg_acc = evaluate_osdg_accuracy(
            model, tokenizer, osdg_texts, osdg_labels_int, device
        )
        print(f"  OSDG top-1 accuracy: {osdg_acc:.4f} (n={len(osdg_texts)})")
        metadata["osdg_outofsample_accuracy"] = osdg_acc
        if osdg_acc < 0.876:
            print(f"  WARNING: Below 87.6% baseline!")

    # AidData Macro F1
    aid_oot = splits["outofsample"]
    aid_texts = aid_oot["aiddata_texts"]
    aid_labels = aid_oot["aiddata_labels"]
    if aid_texts:
        aid_f1 = evaluate_aiddata_macro_f1(
            model, tokenizer, aid_texts, aid_labels, device
        )
        print(f"  AidData Macro F1: {aid_f1:.4f} (n={len(aid_texts)})")
        metadata["aiddata_outofsample_macro_f1"] = aid_f1

    # Save updated metadata
    with open(output_dir / "training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Save out-of-sample predictions for threshold optimization
    print("\nGenerating out-of-sample predictions for threshold optimization...")
    model.eval()
    model.to("cpu")
    all_probs_list = []
    for i in range(0, len(aid_texts), 32):
        batch = aid_texts[i : i + 32]
        inputs = tokenizer(
            batch, truncation=True, padding=True, max_length=512, return_tensors="pt"
        )
        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.sigmoid(logits).numpy()
            all_probs_list.append(probs)

    all_probs = np.vstack(all_probs_list)
    np.savez_compressed(
        output_dir / "outofsample_predictions.npz",
        probabilities=all_probs,
        labels=aid_labels,
        texts=np.array(aid_texts, dtype=object),
    )
    print(f"  Saved predictions: shape={all_probs.shape}")

    print(f"\n{'='*60}")
    print("DONE")
    print(f"{'='*60}")
    print(f"Model saved to: {output_dir}")
    print(f"Update src/sdg_bert_classifier.py to load from this path")


if __name__ == "__main__":
    main()