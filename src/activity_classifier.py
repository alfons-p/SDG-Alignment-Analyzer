"""Activity Classifier Module.

Binary DeBERTa-v3-small classifier for activity detection.
Classifies sentences as ACTION (is_activity=True) or NOT_ACTION (is_activity=False).

Trained on 8,000 consensus-labeled sentences (4-model majority vote: deepseek-v4-pro,
glm-5.1, kimi-k2.6, minimax-m2.7). Test F1 macro: 0.868, ACTION precision: 0.849,
ACTION recall: 0.858.
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

    DEFAULT_MODEL_PATH = "voyager205/sdg-activity-classifier"
    MAX_LENGTH = 256
    BATCH_SIZE = 16

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize the activity classifier.

        Args:
            model_path: HuggingFace Hub repo ID (default: voyager205/sdg-activity-classifier)
                       or local path (e.g. models/activity-classifier/latest)
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
        model_path = self.model_path

        # HuggingFace Hub repo ID (e.g. "voyager205/sdg-activity-classifier"):
        # load directly from Hub without local path resolution.
        # Local paths (e.g. "models/activity-classifier/latest"): resolve
        # relative to PROJECT_ROOT and follow symlinks.
        if "/" in model_path and not Path(model_path).exists():
            # Hub repo ID — download/cache via transformers
            pass
        else:
            path = Path(model_path)
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            if path.is_symlink():
                path = path.resolve()
            model_path = str(path)

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