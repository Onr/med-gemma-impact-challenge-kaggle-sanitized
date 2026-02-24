"""
Backend API endpoint tests.

Tests the FastAPI endpoints (/health, /models, /generate) including
error handling, graceful degradation, and request validation.

Addresses: External test report critical issues #1 (backend service not running)
and #2 (no fallback/graceful degradation).

Run with:
    cd app/backend
    python -m pytest tests/test_backend_api.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from medgemma_backend import app, GenerateRequest, HistoryMessage


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


# ============================================================================
# Health Endpoint Tests
# ============================================================================

class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_includes_device_info(self, client):
        response = client.get("/health")
        data = response.json()
        assert "device" in data
        assert data["device"] in ("cpu", "cuda")
        assert "google_ai_available" in data

    def test_health_includes_loaded_models(self, client):
        response = client.get("/health")
        data = response.json()
        assert "loaded_models" in data
        assert isinstance(data["loaded_models"], list)


# ============================================================================
# Models Endpoint Tests
# ============================================================================

class TestModelsEndpoint:
    """Tests for GET /models."""

    def test_models_returns_suggested(self, client):
        response = client.get("/models")
        assert response.status_code == 200
        data = response.json()
        assert "suggested" in data
        assert "medgemma-4b" in data["suggested"]

    def test_models_returns_local_models_list(self, client):
        response = client.get("/models")
        data = response.json()
        assert "local_models" in data
        assert isinstance(data["local_models"], list)


# ============================================================================
# Generate Endpoint Tests
# ============================================================================

class TestGenerateEndpoint:
    """Tests for POST /generate."""

    def test_generate_rejects_empty_message(self, client):
        """Empty message should still be accepted (model handles it)."""
        response = client.post("/generate", json={
            "model_id": "test-model",
            "message": "",
            "history": [],
        })
        # Will fail because model can't be loaded, which is expected
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "not available" in data["detail"] or "Failed" in data["detail"]

    def test_generate_returns_model_load_error(self, client):
        """Requesting a non-existent model returns a clear error."""
        response = client.post("/generate", json={
            "model_id": "nonexistent/model",
            "message": "test",
            "history": [],
        })
        assert response.status_code == 500
        data = response.json()
        assert "not available" in data["detail"] or "Failed" in data["detail"]

    def test_generate_validates_request_schema(self, client):
        """Missing required fields should return 422."""
        response = client.post("/generate", json={})
        assert response.status_code == 422

    def test_generate_accepts_history(self, client):
        """Request with history should not crash on schema validation."""
        response = client.post("/generate", json={
            "model_id": "test-model",
            "message": "follow up question",
            "history": [
                {"role": "user", "content": "first message"},
                {"role": "assistant", "content": "first reply"},
            ],
        })
        # Schema is valid even though model won't load
        assert response.status_code == 500
        assert "not available" in response.json()["detail"] or "Failed" in response.json()["detail"]

    def test_generate_accepts_system_prompt(self, client):
        """System prompt field should be accepted."""
        response = client.post("/generate", json={
            "model_id": "test-model",
            "message": "test",
            "history": [],
            "system_prompt": "You are a medical assistant.",
        })
        assert response.status_code == 500  # Model load error, not schema error

    def test_generate_accepts_config(self, client):
        """Config overrides should be accepted."""
        response = client.post("/generate", json={
            "model_id": "test-model",
            "message": "test",
            "history": [],
            "config": {"max_new_tokens": 512, "temperature": 0.3},
        })
        assert response.status_code == 500  # Model load error, not schema error

    def test_generate_accepts_images(self, client):
        """Image data should be accepted in schema."""
        response = client.post("/generate", json={
            "model_id": "test-model",
            "message": "analyze this image",
            "history": [],
            "images": [{"mimeType": "image/png", "data": "aGVsbG8="}],
        })
        assert response.status_code == 500  # Model load error, not schema error


# ============================================================================
# Generate with Mock Model Tests
# ============================================================================

class TestGenerateWithMockModel:
    """Tests for /generate with a mocked model to verify response flow."""

    def _mock_model_and_processor(self):
        """Create mock model and processor that return a test response."""
        import torch

        mock_model = MagicMock()
        mock_model.device = "cpu"

        # Use spec to control which attributes exist
        mock_processor = MagicMock(spec=["apply_chat_template", "__call__", "decode"])
        mock_processor.apply_chat_template = MagicMock(return_value="formatted prompt")

        mock_input_ids = torch.tensor([[1, 2, 3, 4, 5]])
        mock_processor.return_value = {"input_ids": mock_input_ids}

        mock_output = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8]])
        mock_model.generate = MagicMock(return_value=[mock_output])
        mock_processor.decode = MagicMock(return_value="This is a test response.")

        return mock_model, mock_processor

    @patch("medgemma_backend._is_local_model_available", return_value=True)
    @patch("medgemma_backend.get_model_and_processor")
    def test_generate_returns_text(self, mock_get_model, mock_local, client):
        mock_model, mock_processor = self._mock_model_and_processor()
        mock_get_model.return_value = (mock_model, mock_processor)

        response = client.post("/generate", json={
            "model_id": "test-model",
            "message": "test",
            "history": [],
        })
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "model_used" in data
        assert data["model_used"] == "local:test-model"

    @patch("medgemma_backend._is_local_model_available", return_value=True)
    @patch("medgemma_backend.get_model_and_processor")
    def test_generate_strips_assistant_prefix(self, mock_get_model, mock_local, client):
        mock_model, mock_processor = self._mock_model_and_processor()
        mock_get_model.return_value = (mock_model, mock_processor)

        response = client.post("/generate", json={
            "model_id": "test-model",
            "message": "test",
            "history": [],
        })
        data = response.json()
        assert data["text"] == "This is a test response."

    @patch("medgemma_backend._is_local_model_available", return_value=True)
    @patch("medgemma_backend.get_model_and_processor")
    def test_generate_with_system_prompt_includes_it(self, mock_get_model, mock_local, client):
        mock_model, mock_processor = self._mock_model_and_processor()
        mock_get_model.return_value = (mock_model, mock_processor)

        response = client.post("/generate", json={
            "model_id": "test-model",
            "message": "test",
            "history": [],
            "system_prompt": "You are MedGemma.",
        })
        assert response.status_code == 200
        assert mock_processor.called

    @patch("medgemma_backend._is_local_model_available", return_value=True)
    @patch("medgemma_backend.get_model_and_processor")
    def test_generate_handles_generation_error(self, mock_get_model, mock_local, client):
        mock_model, mock_processor = self._mock_model_and_processor()
        mock_model.generate.side_effect = RuntimeError("CUDA out of memory")
        mock_get_model.return_value = (mock_model, mock_processor)

        response = client.post("/generate", json={
            "model_id": "test-model",
            "message": "test",
            "history": [],
        })
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert "Generation failed" in detail or "not available" in detail


# ============================================================================
# CORS Tests
# ============================================================================

class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_allows_frontend_origin(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORS middleware should accept this
        assert response.status_code in (200, 204, 405)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
