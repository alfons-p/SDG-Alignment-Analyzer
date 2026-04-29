"""Tests for alignment engine module."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.alignment_engine import AlignmentEngine
from src.sdg_reference import SDGReference


def normalized_embedding(dim=384):
    """Generate a normalized random embedding (unit vector).

    Normalized embeddings ensure cosine similarity is in [0, 1] range,
    matching the behavior of real SentenceTransformer embeddings.
    """
    vec = np.random.randn(dim)
    return vec / np.linalg.norm(vec)


class TestAlignmentEngine:
    """Test cases for AlignmentEngine."""

    @pytest.fixture
    def engine(self):
        """Create alignment engine fixture with mocked SDGReference."""
        with patch('src.sdg_reference.SentenceTransformer') as mock_transformer:
            # Mock the transformer model
            mock_model = Mock()
            mock_model.encode.return_value = normalized_embedding()
            mock_transformer.return_value = mock_model

            # Create engine (this will use mocked SDGReference)
            engine = AlignmentEngine()

            # Set up mock embeddings (normalized for valid cosine similarity)
            mock_embeddings = {
                i: normalized_embedding() for i in range(1, 18)
            }
            engine._sdg_embeddings = mock_embeddings
            engine._sdg_embeddings_matrix = np.array([mock_embeddings[i] for i in range(1, 18)])
            engine._sdg_numbers = list(range(1, 18))

            # Mock the sdg_reference methods
            engine.sdg_reference.get_sdg_name = Mock(return_value="Test SDG")

            yield engine

    def test_init(self):
        """Test engine initialization."""
        from src.config.threshold_config import get_threshold

        with patch('src.sdg_reference.SentenceTransformer') as mock_transformer:
            mock_model = Mock()
            mock_transformer.return_value = mock_model

            engine = AlignmentEngine()
            # Threshold should match threshold_config.py (0.5 for ST mode)
            expected_threshold = get_threshold('st')
            assert engine.similarity_threshold == expected_threshold
            assert engine.sdg_reference is not None

    def test_cosine_similarity(self):
        """Test that cosine similarity uses sklearn implementation."""
        from sklearn.metrics.pairwise import cosine_similarity

        a = np.array([[1, 0, 0]])
        b = np.array([[1, 0, 0]])

        # Test identical vectors
        similarity = cosine_similarity(a, b)[0, 0]
        assert pytest.approx(similarity, 0.001) == 1.0

        # Orthogonal vectors
        c = np.array([[0, 1, 0]])
        similarity = cosine_similarity(a, c)[0, 0]
        assert pytest.approx(similarity, 0.001) == 0.0

    def test_align_activity(self, engine):
        """Test activity alignment."""
        # Mock encode_text to return normalized embeddings
        engine.sdg_reference.encode_text = Mock(return_value=normalized_embedding())

        result = engine.align_activity("Test activity text")

        assert "activity_text" in result
        assert "sdg_scores" in result
        assert "top_sdg" in result
        assert "top_score" in result
        assert len(result["sdg_scores"]) == 17

    def test_compute_report_alignment(self, engine):
        """Test report-level alignment computation."""
        activity_results = [
            {
                "activity_text": "Test activity",
                "sdg_scores": {
                    i: {"score": 0.5, "is_aligned": True, "sdg_name": f"SDG {i}"}
                    for i in range(1, 18)
                },
                "top_sdg": 1,
                "top_score": 0.8
            }
        ]

        report = engine.compute_report_alignment(activity_results)

        assert "total_activities" in report
        assert "mean_scores" in report
        assert "coverage" in report
        assert "top_sdgs" in report

    def test_empty_results(self, engine):
        """Test handling of empty results."""
        report = engine.compute_report_alignment([])
        assert report["total_activities"] == 0
        assert report["mean_scores"] == {}
        assert report["coverage"] == {}
        assert report["top_sdgs"] == []


class TestAlignmentEngineIntegration:
    """Integration tests for alignment engine."""

    def test_compare_activities(self):
        """Test activity comparison."""
        with patch('src.sdg_reference.SentenceTransformer') as mock_transformer:
            mock_model = Mock()
            mock_model.encode.return_value = np.array([[1, 0, 0]])
            mock_transformer.return_value = mock_model

            engine = AlignmentEngine()
            engine.sdg_reference._model = mock_model
            # Use same embedding for both activities (will give similarity = 1)
            engine.sdg_reference.encode_text = Mock(return_value=normalized_embedding(384))

            similarity = engine.compare_activities("Activity 1", "Activity 2")
            assert isinstance(similarity, float)

    def test_find_similar_activities(self):
        """Test finding similar activities."""
        with patch('src.sdg_reference.SentenceTransformer') as mock_transformer:
            mock_model = Mock()
            mock_model.encode.return_value = normalized_embedding(384)
            mock_transformer.return_value = mock_model

            engine = AlignmentEngine()

            # Create consistent embeddings for testing
            # Use embeddings that will produce valid cosine similarities
            emb_dim = 384

            # Mock encode_text to return normalized embeddings
            engine.sdg_reference.encode_text = Mock(return_value=normalized_embedding(emb_dim))

            # Mock encode_texts to return batch embeddings
            def mock_encode_texts(texts, show_progress=False):
                return np.array([normalized_embedding(emb_dim) for _ in texts])
            engine.sdg_reference.encode_texts = Mock(side_effect=mock_encode_texts)

            activities = ["Activity 1", "Activity 2", "Activity 3"]
            results = engine.find_similar_activities("Query", activities, top_k=2)

            assert len(results) == 2
            assert all(isinstance(r, tuple) and len(r) == 2 for r in results)


class TestAlignmentEngineScoring:
    """Test scoring functionality."""

    @pytest.fixture
    def engine(self):
        """Create engine with mock embeddings."""
        with patch('src.sdg_reference.SentenceTransformer') as mock_transformer:
            mock_model = Mock()
            mock_model.encode.return_value = normalized_embedding()
            mock_transformer.return_value = mock_model

            engine = AlignmentEngine()
            engine._sdg_embeddings = {
                i: normalized_embedding() for i in range(1, 18)
            }
            engine._sdg_embeddings_matrix = np.array([engine._sdg_embeddings[i] for i in range(1, 18)])
            engine._sdg_numbers = list(range(1, 18))
            engine.sdg_reference.encode_text = Mock(return_value=normalized_embedding())
            engine.sdg_reference.get_sdg_name = Mock(return_value="Test SDG")

            yield engine

    def test_score_range(self, engine):
        """Test that scores are valid cosine similarity values."""
        result = engine.align_activity("Test activity")

        # Cosine similarity values are in [-1, 1] range
        # With real SentenceTransformer embeddings, they're typically in [0, 1]
        # but with random embeddings they can be negative
        for sdg_num, data in result["sdg_scores"].items():
            assert -1.0 <= data["score"] <= 1.0, f"SDG {sdg_num} score {data['score']} out of valid range [-1, 1]"

    def test_alignment_threshold(self, engine):
        """Test alignment threshold application."""
        result = engine.align_activity("Test activity")

        aligned = [s for s in result["sdg_scores"].values() if s["is_aligned"]]
        # Use get_threshold_for_sdg to check SDG-specific thresholds
        assert all(
            s["score"] >= engine.get_threshold_for_sdg(sdg_num)
            for sdg_num, s in result["sdg_scores"].items()
            if s["is_aligned"]
        )


class TestAlignmentEngineBatch:
    """Test batch processing."""

    @pytest.fixture
    def engine(self):
        """Create engine fixture."""
        with patch('src.sdg_reference.SentenceTransformer') as mock_transformer:
            mock_model = Mock()
            mock_model.encode.return_value = normalized_embedding()
            mock_transformer.return_value = mock_model

            engine = AlignmentEngine()
            engine._sdg_embeddings = {i: normalized_embedding() for i in range(1, 18)}
            engine._sdg_embeddings_matrix = np.array([engine._sdg_embeddings[i] for i in range(1, 18)])
            engine._sdg_numbers = list(range(1, 18))
            engine.sdg_reference.encode_text = Mock(return_value=normalized_embedding())
            engine.sdg_reference.get_sdg_name = Mock(return_value="SDG")

            yield engine

    def test_align_activities(self, engine):
        """Test batch activity alignment."""
        activities = [
            {"text": f"Activity {i}"}
            for i in range(5)
        ]

        results = engine.align_activities(activities, show_progress=False)
        assert len(results) == 5

    def test_align_activities_empty(self, engine):
        """Test with empty activity list."""
        results = engine.align_activities([], show_progress=False)
        assert results == []

    def test_get_alignment_matrix(self, engine):
        """Test alignment matrix generation."""
        results = {
            "activities": [
                {
                    "sdg_scores": {
                        i: {"score": 0.5}
                        for i in range(1, 18)
                    }
                }
            ]
        }

        matrix = engine.get_alignment_matrix(results)
        assert matrix.shape == (1, 17)
        assert np.allclose(matrix, 0.5)