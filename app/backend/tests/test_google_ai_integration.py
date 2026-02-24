"""
Tests for MedGemma backend with Google AI API integration.

Verifies:
- Health endpoint reports google_ai_available
- Generate routes to Google AI API when local model unavailable
- Generate uses local model when available
- Proper error handling

Run with:
    cd app/backend
    python -m pytest tests/test_google_ai_integration.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock


# === Fixtures ===

@pytest.fixture
def client():
    """Create a test client with Google AI mocked."""
    from medgemma_backend import app
    return TestClient(app)


@pytest.fixture
def mock_genai_client():
    """Mock the genai_client global."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a test response from Gemma."
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


# === Health Endpoint ===

class TestHealthWithGoogleAI:

    def test_health_reports_google_ai_field(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "google_ai_available" in data

    def test_health_reports_loaded_models(self, client):
        response = client.get("/health")
        data = response.json()
        assert "loaded_models" in data
        assert isinstance(data["loaded_models"], list)


# === Models Endpoint ===

class TestModelsWithGoogleAI:

    @patch("medgemma_backend.genai_client")
    def test_models_includes_cloud_models(self, mock_gc, client):
        mock_gc.__bool__ = lambda self: True
        response = client.get("/models")
        assert response.status_code == 200
        data = response.json()
        assert "cloud_models" in data

    def test_models_includes_suggested(self, client):
        response = client.get("/models")
        data = response.json()
        assert "suggested" in data
        assert "medgemma-4b" in data["suggested"]


# === Generate via Google AI ===

class TestGenerateGoogleAI:

    @patch("medgemma_backend._is_local_model_available", return_value=False)
    @patch("medgemma_backend.genai_client")
    def test_generate_routes_to_google_ai(self, mock_gc, mock_local, client):
        mock_response = MagicMock()
        mock_response.text = "Test response from cloud model."
        mock_gc.models.generate_content.return_value = mock_response
        # Make genai_client truthy
        mock_gc.__bool__ = lambda self: True

        response = client.post("/generate", json={
            "model_id": "google/medgemma-1.5-4b-it",
            "message": "test medical question",
            "history": [],
        })
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert data["text"] == "Test response from cloud model."
        assert "google-ai:" in data["model_used"]

    @patch("medgemma_backend._is_local_model_available", return_value=False)
    @patch("medgemma_backend.genai_client")
    def test_generate_passes_system_prompt(self, mock_gc, mock_local, client):
        mock_response = MagicMock()
        mock_response.text = "Response with system prompt."
        mock_gc.models.generate_content.return_value = mock_response
        mock_gc.__bool__ = lambda self: True

        response = client.post("/generate", json={
            "model_id": "medgemma-4b-it",
            "message": "test",
            "history": [],
            "system_prompt": "You are a medical EBP copilot.",
        })
        assert response.status_code == 200
        # For Gemma models, system prompt is prepended to user message
        call_kwargs = mock_gc.models.generate_content.call_args
        contents = call_kwargs.kwargs.get("contents") or call_kwargs[1].get("contents")
        user_text = contents[-1]["parts"][-1]["text"]
        assert "medical EBP copilot" in user_text

    @patch("medgemma_backend._is_local_model_available", return_value=False)
    @patch("medgemma_backend.genai_client")
    def test_generate_passes_history(self, mock_gc, mock_local, client):
        mock_response = MagicMock()
        mock_response.text = "Follow-up response."
        mock_gc.models.generate_content.return_value = mock_response
        mock_gc.__bool__ = lambda self: True

        response = client.post("/generate", json={
            "model_id": "medgemma-4b-it",
            "message": "follow-up",
            "history": [
                {"role": "user", "content": "first question"},
                {"role": "model", "content": "first answer"},
            ],
        })
        assert response.status_code == 200
        call_kwargs = mock_gc.models.generate_content.call_args
        contents = call_kwargs.kwargs.get("contents") or call_kwargs[1].get("contents")
        # History + new message = 3 items
        assert len(contents) == 3

    @patch("medgemma_backend._is_local_model_available", return_value=False)
    @patch("medgemma_backend.genai_client")
    def test_generate_maps_model_to_cloud(self, mock_gc, mock_local, client):
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_gc.models.generate_content.return_value = mock_response
        mock_gc.__bool__ = lambda self: True

        response = client.post("/generate", json={
            "model_id": "google/medgemma-1.5-4b-it",
            "message": "test",
            "history": [],
        })
        assert response.status_code == 200
        call_kwargs = mock_gc.models.generate_content.call_args
        model = call_kwargs.kwargs.get("model") or call_kwargs[1].get("model")
        assert model == "gemma-3-4b-it"

    @patch("medgemma_backend._is_local_model_available", return_value=False)
    @patch("medgemma_backend.genai_client", new=None)
    def test_generate_fails_without_cloud_or_local(self, mock_local, client):
        response = client.post("/generate", json={
            "model_id": "google/medgemma-1.5-4b-it",
            "message": "test",
            "history": [],
        })
        assert response.status_code == 500
        data = response.json()
        assert "not available locally" in data["detail"]


# === Generate via Local Model ===

class TestGenerateLocal:

    @patch("medgemma_backend._is_local_model_available", return_value=True)
    @patch("medgemma_backend.get_model_and_processor")
    def test_generate_prefers_local_model(self, mock_get_model, mock_local, client):
        import torch

        mock_model = MagicMock()
        mock_model.device = "cpu"

        # MedGemma uses apply_chat_template with tokenize=True, return_dict=True
        mock_processor = MagicMock(spec=["apply_chat_template", "__call__", "decode"])
        mock_input_ids = torch.tensor([[1, 2, 3, 4, 5]])
        mock_processor.apply_chat_template = MagicMock(return_value={"input_ids": mock_input_ids})

        mock_output = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8]])
        mock_model.generate = MagicMock(return_value=[mock_output])
        mock_processor.decode = MagicMock(return_value="Local model response.")

        mock_get_model.return_value = (mock_model, mock_processor)

        response = client.post("/generate", json={
            "model_id": "google/medgemma-4b-it",
            "message": "test",
            "history": [],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["model_used"] == "local:google/medgemma-4b-it"
        mock_get_model.assert_called_once()

    @patch("medgemma_backend._is_local_model_available", return_value=True)
    @patch("medgemma_backend.get_model_and_processor")
    @patch("medgemma_backend.genai_client")
    def test_generate_falls_back_to_cloud_on_local_error(
        self, mock_gc, mock_get_model, mock_local, client
    ):
        mock_get_model.side_effect = RuntimeError("Model load failed")
        mock_response = MagicMock()
        mock_response.text = "Cloud fallback response."
        mock_gc.models.generate_content.return_value = mock_response
        mock_gc.__bool__ = lambda self: True

        response = client.post("/generate", json={
            "model_id": "google/medgemma-4b-it",
            "message": "test",
            "history": [],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Cloud fallback response."
        assert "google-ai:" in data["model_used"]

class TestModelMapping:

    def test_medgemma_maps_to_gemma(self):
        from medgemma_backend import GOOGLE_AI_MODEL_MAP
        assert GOOGLE_AI_MODEL_MAP["google/medgemma-1.5-4b-it"] == "gemma-3-4b-it"
        assert GOOGLE_AI_MODEL_MAP["google/medgemma-4b-it"] == "gemma-3-4b-it"
        assert GOOGLE_AI_MODEL_MAP["google/medgemma-27b-it"] == "gemma-3-27b-it"

    def test_gemini_maps_correctly(self):
        from medgemma_backend import GOOGLE_AI_MODEL_MAP
        assert GOOGLE_AI_MODEL_MAP["gemini-2.5-flash"] == "gemini-2.5-flash"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
