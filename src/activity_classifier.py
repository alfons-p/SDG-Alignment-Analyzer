"""Activity Classifier Module.

Binary DeBERTa-v3-small classifier for activity detection.
Classifies sentences as ACTION (is_activity=True) or NOT_ACTION (is_activity=False).

Trained on 8,033 LLM-labeled sentences from local government annual reports.
Test F1 macro: 0.872, ACTION precision: 0.862, ACTION recall: 0.889.
"""

from pathlib import Path
from typing import Dict, List, Optional

import torch
from transformers import DebertaV2Tokenizer, AutoModelForSequenceClassification

from src.exceptions import ModelLoadError

# Project root (where src/ lives)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Label mapping: NOT_ACTION=0, ACTION=1
LABEL_MAP = {0: "NOT_ACTION", 1: "ACTION"}


class ActivityClassifier:
    """Binary DeBERTa-v3-small sentence classifier: ACTION vs NOT_ACTION."""

    DEFAULT_MODEL_PATH = "models/activity-classifier/latest"
    MAX_LENGTH = 256
    BATCH_SIZE = 16

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize the activity classifier.

        Args:
            model_path: Local path to the fine-tuned model (default: models/activity-classifier/latest)
            device: Device to use ('cuda', 'mps', 'cpu', or None for auto)
        """
        self.model_path = model_path or self.DEFAULT_MODEL_PATH

        # Auto-detect device: CUDA > MPS > CPU
        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device

        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        """Load the fine-tuned DeBERTa-v3-small model and tokenizer."""
        # Resolve relative paths against project root and follow symlinks
        model_path = Path(self.model_path)
        if not model_path.is_absolute():
            model_path = PROJECT_ROOT / model_path
        if model_path.is_symlink():
            model_path = model_path.resolve()

        try:
            print(f"Loading activity classifier: {model_path}")
            self.tokenizer = DebertaV2Tokenizer.from_pretrained(str(model_path))
            self.model = AutoModelForSequenceClassification.from_pretrained(str(model_path))
            self.model.to(self.device)
            self.model.eval()
            self.model_path = str(model_path)
            print(f"Activity classifier loaded on {self.device}")
        except Exception as e:
            self.model = None
            self.tokenizer = None
            raise ModelLoadError(
                f"Failed to load activity classifier from {self.model_path}: {e}"
            ) from e

    def is_available(self) -> bool:
        """Check if model is loaded and ready for inference."""
        return self.model is not None and self.tokenizer is not None

    def classify(self, text: str) -> Dict:
        """
        Classify a single sentence.

        Args:
            text: Input sentence

        Returns:
            Dict with keys: label (int), label_name (str), confidence (float), is_activity (bool)
        """
        if not self.is_available():
            raise RuntimeError("Activity classifier model not loaded")

        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.MAX_LENGTH,
            padding="max_length",
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            probs = torch.softmax(outputs.logits, dim=-1)

        label = probs.argmax(dim=-1).item()
        confidence = probs[0, label].item()

        return {
            "label": label,
            "label_name": LABEL_MAP[label],
            "confidence": confidence,
            "is_activity": label == 1,
        }

    def classify_batch(self, texts: List[str]) -> List[Dict]:
        """
        Batch classification for efficiency.

        Args:
            texts: List of input sentences

        Returns:
            List of dicts with same keys as classify()
        """
        if not self.is_available():
            raise RuntimeError("Activity classifier model not loaded")

        results = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i : i + self.BATCH_SIZE]
            encodings = self.tokenizer(
                batch,
                truncation=True,
                max_length=self.MAX_LENGTH,
                padding="max_length",
                return_tensors="pt",
            )

            input_ids = encodings["input_ids"].to(self.device)
            attention_mask = encodings["attention_mask"].to(self.device)

            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                probs = torch.softmax(outputs.logits, dim=-1)

            for j in range(len(batch)):
                label = probs[j].argmax().item()
                confidence = probs[j, label].item()
                results.append({
                    "label": label,
                    "label_name": LABEL_MAP[label],
                    "confidence": confidence,
                    "is_activity": label == 1,
                })

        return results

    def get_model_info(self) -> Dict:
        """Return model metadata."""
        return {
            "model_path": self.model_path,
            "device": self.device,
            "num_labels": self.model.config.num_labels if self.model else None,
            "max_length": self.MAX_LENGTH,
            "batch_size": self.BATCH_SIZE,
            "available": self.is_available(),
        }

    def cleanup(self):
        """Move model to CPU and release MPS resources."""
        if hasattr(self, 'model') and self.model is not None and self.device != "cpu":
            self.model.to("cpu")
            self.device = "cpu"
        import gc
        gc.collect()
        try:
            import torch
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                torch.mps.empty_cache()
        except Exception:
            pass

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass