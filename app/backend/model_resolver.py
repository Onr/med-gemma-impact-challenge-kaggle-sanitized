"""
Model resolver utilities for MedGemma backend.

Supports:
- Friendly aliases (medgemma-4b-it, etc.)
- Environment overrides for local/Kaggle paths
- KaggleHub handles via `kagglehub:` prefix
- Auto-detection of local models under /kaggle/input
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


ALIAS_TO_HF = {
    "medgemma-4b-it": "google/medgemma-4b-it",
    "medgemma-27b-text": "google/medgemma-27b-it",
    "medgemma-27b-mm": "google/medgemma-27b-mm-it",
}

HF_TO_ENV_OVERRIDES = {
    "google/medgemma-4b-it": [
        "MEDGEMMA_4B_MODEL_ID",
        "MEDGEMMA_MM_MODEL_ID",
        "MEDGEMMA_MODEL_ID",
    ],
    "google/medgemma-1.5-4b-it": [
        "MEDGEMMA_4B_MODEL_ID",
        "MEDGEMMA_MM_MODEL_ID",
        "MEDGEMMA_MODEL_ID",
    ],
    "google/medgemma-27b-it": [
        "MEDGEMMA_27B_TEXT_MODEL_ID",
        "MEDGEMMA_TEXT_MODEL_ID",
        "MEDGEMMA_MODEL_ID",
    ],
    "google/medgemma-27b-mm-it": [
        "MEDGEMMA_27B_MM_MODEL_ID",
        "MEDGEMMA_MM_MODEL_ID",
        "MEDGEMMA_MODEL_ID",
    ],
}

# Also allow overrides when callers pass the alias directly
ALIAS_TO_ENV_OVERRIDES = {
    "medgemma-4b-it": HF_TO_ENV_OVERRIDES["google/medgemma-1.5-4b-it"],
    "medgemma-27b-text": HF_TO_ENV_OVERRIDES["google/medgemma-27b-it"],
    "medgemma-27b-mm": HF_TO_ENV_OVERRIDES["google/medgemma-27b-mm-it"],
}


def _env_override_for(model_id: str) -> Optional[str]:
    for env_key in HF_TO_ENV_OVERRIDES.get(model_id, []):
        value = os.getenv(env_key)
        if value:
            return value
    for env_key in ALIAS_TO_ENV_OVERRIDES.get(model_id, []):
        value = os.getenv(env_key)
        if value:
            return value
    return None


def _find_hf_dir(root: Path) -> Optional[str]:
    if (root / "config.json").exists():
        return str(root)
    for cfg in root.rglob("config.json"):
        try:
            if cfg.is_file() and cfg.stat().st_size > 0:
                return str(cfg.parent)
        except Exception:
            continue
    return None


def _download_kagglehub(handle: str) -> str:
    try:
        import kagglehub  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "kagglehub is not installed. Install it or remove the kagglehub: prefix."
        ) from exc

    downloaded_path = Path(kagglehub.model_download(handle))
    hf_dir = _find_hf_dir(downloaded_path)
    if not hf_dir:
        raise RuntimeError(
            "KaggleHub download did not include a HuggingFace-style config.json. "
            "This is likely a Keras-native checkpoint; Transformers cannot load it."
        )
    return hf_dir


def _scan_kaggle_input(model_id: str) -> Optional[str]:
    kaggle_input = Path("/kaggle/input")
    if not kaggle_input.exists():
        return None

    candidates = [cfg.parent for cfg in kaggle_input.rglob("config.json")]
    if not candidates:
        return None

    model_id_lower = model_id.lower()
    keywords = []
    if "1.5-4b" in model_id_lower or "4b" in model_id_lower:
        keywords = ["4b", "1.5", "4b-it"]
    elif "27b-mm" in model_id_lower or "27b mm" in model_id_lower:
        keywords = ["27b", "mm"]
    elif "27b" in model_id_lower:
        keywords = ["27b", "text", "it"]

    def score(path: Path) -> int:
        name = str(path).lower()
        return sum(1 for kw in keywords if kw in name)

    best = max(candidates, key=score)
    if score(best) > 0:
        return str(best)

    # If only one candidate exists, use it as a best-effort fallback.
    if len(candidates) == 1:
        return str(candidates[0])

    return None


def resolve_model_id(model_id: str) -> str:
    """Resolve model_id to a concrete HF ID or local path."""
    # Alias mapping
    model_id = ALIAS_TO_HF.get(model_id, model_id)

    # Environment overrides (local/Kaggle paths)
    override = _env_override_for(model_id)
    if override:
        return override

    # Explicit KaggleHub handle
    if model_id.startswith("kagglehub:"):
        handle = model_id.split(":", 1)[1]
        return _download_kagglehub(handle)

    # Local path provided directly
    if Path(model_id).exists():
        return model_id

    # If on Kaggle, try to match a local folder under /kaggle/input
    local_match = _scan_kaggle_input(model_id)
    if local_match:
        return local_match

    return model_id
