"""Tests for backend FastAPI app — all endpoints."""

import io
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from fastapi.testclient import TestClient

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Override database to in-memory SQLite before importing app
os.environ["DATABASE_URL"] = "sqlite:///./backend/test_sdg_analyzer.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["RATE_LIMIT_MAX"] = "1000"  # disable rate limiting in tests
os.environ["RATE_LIMIT_WINDOW"] = "1"  # short window so buckets clear between tests

from backend.app.main import app
from backend.app.dependencies import init_db, SessionLocal, engine
from backend.app.models.base import Base


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def _register(client, email="test@example.com", password="TestPass1"):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def _login(client, email="test@example.com", password="TestPass1"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _auth_headers(client, email="test@example.com", password="TestPass1"):
    _register(client, email, password)  # ensure user exists
    resp = _login(client, email, password)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Health
# =============================================================================

def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# =============================================================================
# Auth — Register
# =============================================================================

def test_register_success(client):
    resp = _register(client)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email(client):
    _register(client)
    resp = _register(client)
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"].lower()


def test_register_short_password(client):
    resp = _register(client, password="1234567")
    assert resp.status_code == 422
    assert "8 characters" in resp.json()["detail"]


# =============================================================================
# Auth — Login
# =============================================================================

def test_login_success(client):
    _register(client)
    resp = _login(client)
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    _register(client)
    resp = _login(client, password="WrongPass1")
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = _login(client, email="no@user.com")
    assert resp.status_code == 401


# =============================================================================
# Auth — Me
# =============================================================================

def test_me_authenticated(client):
    headers = _auth_headers(client)
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


def test_me_unauthenticated(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 403


def test_me_invalid_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


# =============================================================================
# Reference Endpoints
# =============================================================================

def test_reference_sdgs(client):
    resp = client.get("/api/reference/sdgs")
    assert resp.status_code == 200
    sdgs = resp.json()["sdgs"]
    assert len(sdgs) == 17
    assert sdgs[0]["number"] == 1
    assert sdgs[0]["name"] == "No Poverty"
    assert "color" in sdgs[0]


def test_reference_colors(client):
    resp = client.get("/api/reference/sdgs/colors")
    assert resp.status_code == 200
    colors = resp.json()["colors"]
    assert len(colors) == 17
    assert colors["1"] == "#E5243B"


def test_reference_simple(client):
    resp = client.get("/api/reference/sdgs/simple")
    assert resp.status_code == 200
    sdgs = resp.json()["sdgs"]
    assert len(sdgs) == 17
    assert sdgs["1"]["name"] == "No Poverty"


# =============================================================================
# Analysis — Upload (sync mock)
# =============================================================================

def _make_pdf_bytes():
    """Create minimal PDF bytes for upload tests."""
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n%%EOF"


def test_upload_requires_auth(client):
    resp = client.post("/api/analysis/upload")
    assert resp.status_code == 403


@patch("backend.app.services.analysis_service._process_pdf_backend")
def test_upload_pdf_sync(mock_process, client):
    mock_process.return_value = {
        "source": "test.pdf",
        "metadata": {"year": "2024", "state": "NSW"},
        "activities": [{
            "activity_text": "Build park",
            "word_count": 2,
            "section_type": "general",
            "relevance_score": 0.8,
            "top_sdg": 11,
            "top_sdg_name": "Sustainable Cities",
            "top_score": 0.75,
            "num_aligned": 3,
            "sdg_scores": {11: {"score": 0.75, "is_aligned": True}},
        }],
        "report_alignment": {
            "total_activities": 1,
            "mean_alignment_score": 0.75,
            "mean_scores": {i: 0.1 for i in range(1, 18)},
            "top_sdgs": [{"sdg": 11, "name": "Sustainable Cities", "mean_score": 0.75, "coverage": 0.5}],
            "gaps": [],
        },
    }

    headers = _auth_headers(client)
    pdf_bytes = _make_pdf_bytes()
    resp = client.post(
        "/api/analysis/upload",
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
        params={
            "model_name": "test-model",
            "similarity_threshold": 0.6,
            "use_hybrid": True,
            "ensemble_mode": "weighted",
            "min_words": 10,
            "max_words": 300,
            "top_activities": 0,
            "enable_bias_corrections": True,
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["original_filename"] == "test.pdf"
    assert "id" in data


def test_upload_non_pdf(client):
    headers = _auth_headers(client)
    resp = client.post(
        "/api/analysis/upload",
        files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


# =============================================================================
# Analysis — Job Status
# =============================================================================

def test_job_status_not_found(client):
    headers = _auth_headers(client)
    resp = client.get("/api/analysis/jobs/nonexistent-id", headers=headers)
    assert resp.status_code == 404


def test_job_status_wrong_user(client):
    headers1 = _auth_headers(client, email="user1@test.com")

    # Upload as user1
    pdf_bytes = _make_pdf_bytes()
    with patch("backend.app.routers.analysis.run_analysis_sync"):
        upload_resp = client.post(
            "/api/analysis/upload",
            files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=headers1,
        )
    analysis_id = upload_resp.json()["id"]

    # Try to access as user2
    headers2 = _auth_headers(client, email="user2@test.com")
    resp = client.get(f"/api/analysis/jobs/{analysis_id}", headers=headers2)
    assert resp.status_code == 404


# =============================================================================
# Analysis — Results Endpoints
# =============================================================================

def test_results_not_completed(client):
    headers = _auth_headers(client)
    pdf_bytes = _make_pdf_bytes()
    with patch("backend.app.routers.analysis.run_analysis_sync"):
        upload_resp = client.post(
            "/api/analysis/upload",
            files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=headers,
        )
    analysis_id = upload_resp.json()["id"]

    # Results not available yet (queued, no result)
    resp = client.get(f"/api/analysis/results/{analysis_id}/summary", headers=headers)
    assert resp.status_code == 409


def test_activities_pagination(client):
    headers = _auth_headers(client)
    pdf_bytes = _make_pdf_bytes()

    with patch("backend.app.routers.analysis.run_analysis_sync"):
        upload_resp = client.post(
            "/api/analysis/upload",
            files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=headers,
        )
    analysis_id = upload_resp.json()["id"]

    resp = client.get(
        f"/api/analysis/results/{analysis_id}/activities",
        params={"page": 1, "page_size": 50},
        headers=headers,
    )
    assert resp.status_code == 409  # Not completed yet


# =============================================================================
# Analysis — List & Delete
# =============================================================================

def test_list_analyses(client):
    headers = _auth_headers(client)
    resp = client.get("/api/analysis", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_analyses_requires_auth(client):
    resp = client.get("/api/analysis")
    assert resp.status_code == 403


def test_delete_analysis_not_found(client):
    headers = _auth_headers(client)
    resp = client.delete("/api/analysis/nonexistent-id", headers=headers)
    assert resp.status_code == 404


# =============================================================================
# Results — Compare
# =============================================================================

def test_compare_requires_auth(client):
    resp = client.post("/api/results/compare", json={"analysis_ids": ["id1", "id2"]})
    assert resp.status_code == 403


def test_compare_needs_at_least_two(client):
    headers = _auth_headers(client)
    resp = client.post("/api/results/compare", json={"analysis_ids": ["id1"]}, headers=headers)
    assert resp.status_code == 400
    assert "2 analysis" in resp.json()["detail"]


def test_compare_missing_ids(client):
    headers = _auth_headers(client)
    resp = client.post(
        "/api/results/compare",
        json={"analysis_ids": ["00000000-0000-0000-0000-000000000000", "11111111-1111-1111-1111-111111111111"]},
        headers=headers,
    )
    assert resp.status_code == 404


# =============================================================================
# Export Endpoints
# =============================================================================

def test_export_csv_unavailable(client):
    headers = _auth_headers(client)
    resp = client.get("/api/analysis/results/nonexistent/export/csv", headers=headers)
    assert resp.status_code == 404


def test_export_json_unavailable(client):
    headers = _auth_headers(client)
    resp = client.get("/api/analysis/results/nonexistent/export/json", headers=headers)
    assert resp.status_code == 404
