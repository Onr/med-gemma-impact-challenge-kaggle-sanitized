"""Tests for local MedGemma model routing and inference."""
import pytest
import torch
from unittest.mock import patch, MagicMock


class TestLocalModelDetection:
    """Test that local model availability is detected correctly."""

    @patch("medgemma_backend.resolve_model_id", return_value="google/medgemma-4b-it")
    def test_medgemma_4b_detected_via_hf_cache(self, mock_resolve):
        from medgemma_backend import _is_local_model_available

        with patch("medgemma_backend.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            with patch(
                "huggingface_hub.try_to_load_from_cache",
                return_value="/home/user/.cache/huggingface/hub/models--google--medgemma-4b-it/config.json",
            ):
                assert _is_local_model_available("google/medgemma-4b-it") is True

    @patch("medgemma_backend.resolve_model_id", return_value="google/medgemma-4b-it")
    def test_non_local_model_returns_false(self, mock_resolve):
        from medgemma_backend import _is_local_model_available

        with patch("medgemma_backend.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            with patch(
                "huggingface_hub.try_to_load_from_cache", return_value=None
            ):
                assert _is_local_model_available("google/medgemma-4b-it") is False


class TestSmartRouting:
    """Test that models route to local GPU vs cloud API correctly."""

    def test_cloud_only_models_skip_local(self):
        from medgemma_backend import CLOUD_ONLY_MODELS
        assert "medgemma-27b-text" in CLOUD_ONLY_MODELS
        assert "medgemma-27b-mm" in CLOUD_ONLY_MODELS
        assert "gemini-flash" in CLOUD_ONLY_MODELS

    def test_local_preferred_models(self):
        from medgemma_backend import LOCAL_PREFERRED_MODELS
        assert "google/medgemma-4b-it" in LOCAL_PREFERRED_MODELS
        assert "medgemma-4b-it" in LOCAL_PREFERRED_MODELS

    @patch("medgemma_backend._is_local_model_available", return_value=False)
    @patch("medgemma_backend.genai_client")
    def test_27b_routes_to_cloud(self, mock_gc, mock_local, client):
        mock_response = MagicMock()
        mock_response.text = "Cloud 27B response."
        mock_gc.models.generate_content.return_value = mock_response
        mock_gc.__bool__ = lambda self: True

        response = client.post("/generate", json={
            "model_id": "medgemma-27b-text",
            "message": "test",
            "history": [],
        })
        assert response.status_code == 200
        data = response.json()
        assert "google-ai:" in data["model_used"]

    @patch("medgemma_backend._is_local_model_available", return_value=True)
    @patch("medgemma_backend.get_model_and_processor")
    def test_4b_routes_to_local(self, mock_get_model, mock_local, client):
        mock_model = MagicMock()
        mock_model.device = "cpu"

        mock_processor = MagicMock(spec=["apply_chat_template", "decode"])
        mock_input_ids = torch.tensor([[1, 2, 3, 4, 5]])
        mock_processor.apply_chat_template = MagicMock(
            return_value={"input_ids": mock_input_ids}
        )
        mock_output = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8]])
        mock_model.generate = MagicMock(return_value=[mock_output])
        mock_processor.decode = MagicMock(return_value="Local 4B response.")
        mock_get_model.return_value = (mock_model, mock_processor)

        response = client.post("/generate", json={
            "model_id": "medgemma-4b-it",
            "message": "test",
            "history": [],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["model_used"] == "local:medgemma-4b-it"


class TestMedGemmaMessageFormat:
    """Test that MedGemma structured content format is used correctly."""

    @patch("medgemma_backend._is_local_model_available", return_value=True)
    @patch("medgemma_backend.get_model_and_processor")
    def test_medgemma_uses_structured_content(self, mock_get_model, mock_local, client):
        mock_model = MagicMock()
        mock_model.device = "cpu"

        mock_processor = MagicMock(spec=["apply_chat_template", "decode"])
        mock_input_ids = torch.tensor([[1, 2, 3]])
        mock_processor.apply_chat_template = MagicMock(
            return_value={"input_ids": mock_input_ids}
        )
        mock_output = torch.tensor([[1, 2, 3, 4, 5]])
        mock_model.generate = MagicMock(return_value=[mock_output])
        mock_processor.decode = MagicMock(return_value="Response.")
        mock_get_model.return_value = (mock_model, mock_processor)

        response = client.post("/generate", json={
            "model_id": "google/medgemma-4b-it",
            "message": "What is PICO?",
            "history": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}],
            "system_prompt": "You are a medical assistant.",
        })
        assert response.status_code == 200

        # Verify apply_chat_template was called with structured content
        call_args = mock_processor.apply_chat_template.call_args
        messages = call_args[0][0]

        # System message uses structured content
        assert messages[0]["role"] == "system"
        assert messages[0]["content"][0]["type"] == "text"

        # History messages use structured content
        assert messages[1]["role"] == "user"
        assert messages[1]["content"][0]["type"] == "text"
        assert messages[1]["content"][0]["text"] == "hi"

        # User message uses structured content
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"][0]["type"] == "text"
        assert messages[-1]["content"][0]["text"] == "What is PICO?"

    @patch("medgemma_backend._is_local_model_available", return_value=True)
    @patch("medgemma_backend.get_model_and_processor")
    def test_medgemma_apply_chat_template_kwargs(self, mock_get_model, mock_local, client):
        """Ensure tokenize=True and return_dict=True are passed."""
        mock_model = MagicMock()
        mock_model.device = "cpu"

        mock_processor = MagicMock(spec=["apply_chat_template", "decode"])
        mock_input_ids = torch.tensor([[1, 2, 3]])
        mock_processor.apply_chat_template = MagicMock(
            return_value={"input_ids": mock_input_ids}
        )
        mock_output = torch.tensor([[1, 2, 3, 4]])
        mock_model.generate = MagicMock(return_value=[mock_output])
        mock_processor.decode = MagicMock(return_value="Ok.")
        mock_get_model.return_value = (mock_model, mock_processor)

        client.post("/generate", json={
            "model_id": "medgemma-4b-it",
            "message": "test",
            "history": [],
        })

        call_kwargs = mock_processor.apply_chat_template.call_args[1]
        assert call_kwargs["tokenize"] is True
        assert call_kwargs["return_dict"] is True
        assert call_kwargs["return_tensors"] == "pt"
        assert call_kwargs["add_generation_prompt"] is True


class TestModelResolverUpdates:
    """Test updated model resolver aliases."""

    def test_medgemma_4b_alias_maps_to_new_id(self):
        from model_resolver import ALIAS_TO_HF
        assert ALIAS_TO_HF["medgemma-4b-it"] == "google/medgemma-4b-it"

    def test_medgemma_4b_env_override(self):
        from model_resolver import HF_TO_ENV_OVERRIDES
        assert "google/medgemma-4b-it" in HF_TO_ENV_OVERRIDES


@pytest.fixture
def client():
    from medgemma_backend import app
    from fastapi.testclient import TestClient
    return TestClient(app)
