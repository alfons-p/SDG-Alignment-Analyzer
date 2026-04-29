"""Tests for ActivityClassifier module."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# Skip all tests if model is not available (no GPU/CPU model downloaded)
MODEL_PATH = Path("models/activity-classifier/latest")
pytestmark = pytest.mark.skipif(
    not MODEL_PATH.exists(),
    reason="Activity classifier model not found at models/activity-classifier/latest"
)


@pytest.fixture
def classifier():
    """Load the activity classifier for testing."""
    from src.activity_classifier import ActivityClassifier
    return ActivityClassifier(device="cpu")


class TestActivityClassifierInit:
    def test_classifier_loads(self, classifier):
        assert classifier.is_available()
        assert classifier.model is not None
        assert classifier.tokenizer is not None

    def test_model_info(self, classifier):
        info = classifier.get_model_info()
        assert info["available"] is True
        assert info["num_labels"] == 2
        assert info["device"] == "cpu"
        assert info["max_length"] == 256

    def test_invalid_model_path_raises(self):
        from src.activity_classifier import ActivityClassifier
        from src.exceptions import ModelLoadError
        with pytest.raises(ModelLoadError):
            ActivityClassifier(model_path="/nonexistent/path", device="cpu")


class TestActivityClassifierClassify:
    # Clear activity sentences
    ACTIVITY_SENTENCES = [
        "Council installed 500 kW of solar panels on community buildings.",
        "The city reduced water consumption by 15% through leak detection programs.",
        "We launched a new community health outreach program serving 2,000 residents.",
    ]

    # Clear non-activity sentences
    NON_ACTIVITY_SENTENCES = [
        "The financial statements are presented in accordance with Australian Accounting Standards.",
        "Figure 3.2 shows the trend in population growth over the past decade.",
        "Council consists of seven elected representatives including the Mayor.",
    ]

    def test_classify_activity(self, classifier):
        result = classifier.classify(self.ACTIVITY_SENTENCES[0])
        assert result["is_activity"] is True
        assert result["label"] == 1
        assert result["label_name"] == "ACTION"
        assert result["confidence"] > 0.5

    def test_classify_non_activity(self, classifier):
        result = classifier.classify(self.NON_ACTIVITY_SENTENCES[0])
        assert result["is_activity"] is False
        assert result["label"] == 0
        assert result["label_name"] == "NOT_ACTION"

    def test_classify_returns_required_keys(self, classifier):
        result = classifier.classize("Test sentence")
        assert "label" in result
        assert "label_name" in result
        assert "confidence" in result
        assert "is_activity" in result

    def test_classify_batch(self, classifier):
        sentences = self.ACTIVITY_SENTENCES + self.NON_ACTIVITY_SENTENCES
        results = classifier.classify_batch(sentences)
        assert len(results) == len(sentences)
        assert all("is_activity" in r for r in results)
        assert all("confidence" in r for r in results)

    def test_classify_batch_consistency(self, classifier):
        """Batch results should match individual classify calls."""
        sentences = self.ACTIVITY_SENTENCES[:2]
        batch_results = classifier.classify_batch(sentences)
        for i, sentence in enumerate(sentences):
            single_result = classifier.classify(sentence)
            assert batch_results[i]["is_activity"] == single_result["is_activity"]
            assert batch_results[i]["label"] == single_result["label"]

    def test_activities_detected(self, classifier):
        """Most activity sentences should be classified as ACTION."""
        results = classifier.classify_batch(self.ACTIVITY_SENTENCES)
        action_count = sum(1 for r in results if r["is_activity"])
        assert action_count >= 2, f"Expected >= 2 ACTION, got {action_count}"

    def test_non_activities_rejected(self, classifier):
        """Most non-activity sentences should be classified as NOT_ACTION."""
        results = classifier.classify_batch(self.NON_ACTIVITY_SENTENCES)
        not_action_count = sum(1 for r in results if not r["is_activity"])
        assert not_action_count >= 2, f"Expected >= 2 NOT_ACTION, got {not_action_count}"


class TestActivityClassifierEdgeCases:
    def test_empty_string(self, classifier):
        result = classifier.classify("")
        assert "is_activity" in result
        assert "confidence" in result

    def test_very_long_text(self, classifier):
        long_text = "Council implemented " + "various sustainability " * 100
        result = classifier.classify(long_text)
        assert "is_activity" in result

    def test_single_word(self, classifier):
        result = classifier.classify("Meeting")
        assert "is_activity" in result