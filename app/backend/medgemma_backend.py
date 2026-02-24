"""
MedGemma Backend Service

Unified backend that supports:
1. Local HuggingFace models (MedGemma weights on disk / Kaggle)
2. Google AI API (Gemma models via cloud when local weights unavailable)

The backend auto-detects: if a local model path exists, it uses HuggingFace
Transformers; otherwise it routes to Google AI API with the best available
Gemma model.

Usage:
    pip install fastapi uvicorn transformers accelerate pillow torch google-genai
    GOOGLE_API_KEY=... python medgemma_backend.py

The frontend app connects by setting:
    VITE_USE_LOCAL_BACKEND=true
    VITE_BACKEND_URL=http://localhost:8000
"""

import os
import base64
import io
import logging
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from model_resolver import resolve_model_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medgemma-backend")

# Lazy imports for heavy libs
transformers = None
torch = None
Image = None
genai_client = None

def ensure_torch():
    global torch
    if torch is None:
        import torch as _torch
        torch = _torch

def ensure_transformers():
    global transformers, Image
    ensure_torch()
    if transformers is None:
        import transformers as tf
        transformers = tf
    if Image is None:
        from PIL import Image as PILImage
        Image = PILImage


def _init_genai_client():
    """Initialize Google AI client from environment."""
    global genai_client
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("VITE_GOOGLE_API_KEY")
    if api_key and genai_client is None:
        try:
            from google import genai
            genai_client = genai.Client(api_key=api_key)
            logger.info("Google AI API client initialized")
        except ImportError:
            logger.warning("google-genai not installed; cloud models unavailable")
        except Exception as e:
            logger.warning(f"Failed to init Google AI client: {e}")

_init_genai_client()


# === Device config (lazy – only when torch needed) ===
def _get_device_info():
    ensure_torch()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and torch.cuda.is_bf16_supported():
        dtype = torch.bfloat16
    elif device == "cuda":
        dtype = torch.float16
    else:
        dtype = torch.float32
    return device, dtype


# Model cache for local HF models
_loaded_models = {}
_loaded_processors = {}

# Map frontend model IDs to Google AI API model names
GOOGLE_AI_MODEL_MAP = {
    "google/medgemma-1.5-4b-it": "gemma-3-4b-it",
    "google/medgemma-4b-it": "gemma-3-4b-it",
    "google/medgemma-27b-it": "gemma-3-27b-it",
    "google/medgemma-27b-mm-it": "gemma-3-27b-it",
    "medgemma-4b-it": "gemma-3-4b-it",
    "medgemma-27b-text": "gemma-3-27b-it",
    "medgemma-27b-mm": "gemma-3-27b-it",
    "gemini-flash": "gemini-2.5-flash",
    "gemini-2.5-flash": "gemini-2.5-flash",
    "gemini-2.0-flash": "gemini-2.0-flash",
    "gemini-3-flash-preview": "gemini-2.5-flash",
}

# Models that should prefer local inference when available
LOCAL_PREFERRED_MODELS = {
    "google/medgemma-4b-it",
    "google/medgemma-1.5-4b-it",
    "medgemma-4b-it",
}

# Models too large for local GPU (20GB) that always use cloud API
CLOUD_ONLY_MODELS = {
    "google/medgemma-27b-it",
    "google/medgemma-27b-mm-it",
    "medgemma-27b-text",
    "medgemma-27b-mm",
    "gemini-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-3-flash-preview",
}

# Default cloud model when no specific mapping found
DEFAULT_CLOUD_MODEL = os.getenv("GOOGLE_CLOUD_MODEL", "gemma-3-4b-it")


# === Pydantic Models ===
class ImageData(BaseModel):
    mimeType: str
    data: str  # base64

class HistoryMessage(BaseModel):
    role: str
    content: str

class GenerateRequest(BaseModel):
    model_id: str
    history: List[HistoryMessage] = []
    message: str
    images: Optional[List[ImageData]] = None
    system_prompt: Optional[str] = None
    config: Optional[dict] = None

class GenerateResponse(BaseModel):
    text: str
    model_used: str


# === Local Model helpers ===
def _is_local_model_available(model_id: str) -> bool:
    """Check if a model can be loaded locally (HF cache or local path)."""
    resolved = resolve_model_id(model_id)
    p = Path(resolved)
    # Direct local path
    if p.exists() and (p / "config.json").exists():
        return True
    # Check if it's an HF hub model already cached
    if model_id in LOCAL_PREFERRED_MODELS or resolved in LOCAL_PREFERRED_MODELS:
        try:
            from huggingface_hub import try_to_load_from_cache
            result = try_to_load_from_cache(resolved, "config.json")
            if result is not None and isinstance(result, str):
                return True
        except Exception:
            pass
    return False


def get_model_and_processor(model_id: str):
    """Load and cache a local HuggingFace model/processor."""
    ensure_transformers()

    resolved_id = resolve_model_id(model_id)
    if resolved_id != model_id:
        logger.info(f"Resolved model_id '{model_id}' -> '{resolved_id}'")

    # Normalize medgemma aliases to the canonical HF ID
    canonical = {
        "medgemma-4b-it": "google/medgemma-4b-it",
        "google/medgemma-1.5-4b-it": "google/medgemma-4b-it",
    }
    resolved_id = canonical.get(resolved_id, resolved_id)
    model_id = resolved_id

    if model_id in _loaded_models:
        return _loaded_models[model_id], _loaded_processors[model_id]

    device, dtype = _get_device_info()
    logger.info(f"Loading local model: {model_id} (device={device}, dtype={dtype})")

    is_multimodal = any(kw in model_id.lower() for kw in ['4b', 'mm', 'vision', 'multimodal'])

    if is_multimodal:
        for cls_name in ['AutoModelForImageTextToText', 'AutoModelForVision2Seq', 'AutoModelForCausalLM']:
            try:
                ModelClass = getattr(transformers, cls_name)
                break
            except AttributeError:
                continue
        else:
            raise RuntimeError("No suitable multimodal model class found")
        processor = transformers.AutoProcessor.from_pretrained(model_id)
    else:
        ModelClass = transformers.AutoModelForCausalLM
        processor = transformers.AutoTokenizer.from_pretrained(model_id)

    model = ModelClass.from_pretrained(
        model_id,
        device_map="auto" if device == "cuda" else None,
        torch_dtype=dtype if device == "cuda" else None,
    )

    _loaded_models[model_id] = model
    _loaded_processors[model_id] = processor
    logger.info(f"Model loaded on {device} with dtype {dtype}")
    return model, processor


def decode_base64_image(image_data: ImageData):
    """Decode base64 image to PIL Image."""
    ensure_transformers()
    image_bytes = base64.b64decode(image_data.data)
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


# === Google AI API generation ===
async def generate_via_google_ai(request: GenerateRequest) -> GenerateResponse:
    """Generate using Google AI API (Gemma / Gemini models)."""
    if genai_client is None:
        raise RuntimeError(
            "Google AI API not configured. Set GOOGLE_API_KEY environment variable."
        )

    cloud_model = GOOGLE_AI_MODEL_MAP.get(request.model_id, DEFAULT_CLOUD_MODEL)
    logger.info(f"Using Google AI API model: {cloud_model} (requested: {request.model_id})")

    # Gemma models don't support system_instruction; prepend to first user message
    is_gemma = "gemma" in cloud_model.lower() and "gemini" not in cloud_model.lower()

    # Build conversation contents
    contents = []
    system_text = request.system_prompt or ""

    for msg in request.history:
        role = "user" if msg.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.content}]})

    # Build current user message parts
    user_parts = []
    if request.images:
        for img in request.images:
            user_parts.append({
                "inline_data": {"mime_type": img.mimeType, "data": img.data}
            })

    # For Gemma, prepend system prompt to first user message
    if is_gemma and system_text:
        msg_text = f"[System Instructions]\n{system_text}\n[End Instructions]\n\n{request.message}"
    else:
        msg_text = request.message
    user_parts.append({"text": msg_text})
    contents.append({"role": "user", "parts": user_parts})

    gen_config = request.config or {}
    temperature = gen_config.get("temperature", 0.7)
    max_tokens = gen_config.get("max_new_tokens", 1024)

    config = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }
    if not is_gemma and system_text:
        config["system_instruction"] = system_text

    try:
        response = genai_client.models.generate_content(
            model=cloud_model,
            contents=contents,
            config=config,
        )
        text = response.text or "I apologize, but I couldn't generate a response."
    except Exception as e:
        logger.error(f"Google AI API error: {e}")
        raise RuntimeError(f"Google AI API call failed: {e}")

    return GenerateResponse(text=text, model_used=f"google-ai:{cloud_model}")


# === Local HF generation ===
async def generate_via_local(request: GenerateRequest) -> GenerateResponse:
    """Generate using local HuggingFace model."""
    ensure_torch()
    model, processor = get_model_and_processor(request.model_id)

    has_images = request.images and len(request.images) > 0
    is_medgemma = any(kw in request.model_id.lower() for kw in ['medgemma', '4b-it'])

    # Build chat messages - MedGemma needs structured content format
    messages = []
    if request.system_prompt:
        if is_medgemma:
            messages.append({"role": "system", "content": [{"type": "text", "text": request.system_prompt}]})
        else:
            messages.append({"role": "system", "content": request.system_prompt})

    for msg in request.history:
        if is_medgemma:
            messages.append({"role": msg.role, "content": [{"type": "text", "text": msg.content}]})
        else:
            messages.append({"role": msg.role, "content": msg.content})

    # Build current user message
    if is_medgemma:
        user_content = []
        if has_images:
            for img in request.images:
                user_content.append({"type": "image", "image": decode_base64_image(img)})
        user_content.append({"type": "text", "text": request.message})
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": request.message})

    gen_config = request.config or {}
    max_new_tokens = gen_config.get("max_new_tokens", 1024)
    temperature = gen_config.get("temperature", 0.7)

    # Use apply_chat_template for tokenization
    if is_medgemma and hasattr(processor, 'apply_chat_template'):
        inputs = processor.apply_chat_template(
            messages, tokenize=True, return_tensors="pt",
            return_dict=True, add_generation_prompt=True
        )
        inputs = {k: v.to(model.device) if hasattr(v, 'to') else v for k, v in inputs.items()}
    elif hasattr(processor, 'apply_chat_template'):
        full_prompt = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        if has_images and hasattr(processor, 'image_processor'):
            images = [decode_base64_image(img) for img in request.images]
            inputs = processor(
                text=full_prompt,
                images=images if len(images) > 1 else images[0],
                return_tensors="pt",
            )
            inputs = {k: v.to(model.device) if hasattr(v, 'to') else v for k, v in inputs.items()}
        else:
            tokenizer = processor if not hasattr(processor, 'tokenizer') else processor.tokenizer
            inputs = tokenizer(full_prompt, return_tensors="pt")
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
    else:
        # Fallback raw prompt
        full_prompt = ""
        if request.system_prompt:
            full_prompt += f"System: {request.system_prompt}\n\n"
        for msg in request.history:
            role_label = "User" if msg.role == "user" else "Assistant"
            full_prompt += f"{role_label}: {msg.content}\n\n"
        full_prompt += f"User: {request.message}\nAssistant:"
        tokenizer = processor if not hasattr(processor, 'tokenizer') else processor.tokenizer
        inputs = tokenizer(full_prompt, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

    with torch.inference_mode():
        input_len = inputs["input_ids"].shape[-1]
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else None,
        )

        # Decode only newly generated tokens
        new_tokens = outputs[0][input_len:]
        tokenizer = processor if not hasattr(processor, 'tokenizer') else processor.tokenizer
        if hasattr(tokenizer, 'decode'):
            text = tokenizer.decode(new_tokens, skip_special_tokens=True)
        elif hasattr(processor, 'batch_decode'):
            text = processor.batch_decode(outputs[:, input_len:], skip_special_tokens=True)[0]
        else:
            text = processor.decode(outputs[0], skip_special_tokens=True)

    return GenerateResponse(text=text.strip(), model_used=f"local:{request.model_id}")


# === FastAPI App ===
app = FastAPI(
    title="MedGemma Backend",
    description="Backend service for MedGemma model inference (local + cloud)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    ensure_torch()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    gpu_name = torch.cuda.get_device_name(0) if device == "cuda" else None
    vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1) if device == "cuda" else 0
    return {
        "status": "ok",
        "device": device,
        "gpu": gpu_name,
        "vram_gb": vram_gb,
        "google_ai_available": genai_client is not None,
        "loaded_models": list(_loaded_models.keys()),
        "local_medgemma_available": _is_local_model_available("google/medgemma-4b-it"),
    }


@app.get("/models")
async def list_models():
    """List available models."""
    local_models = []
    kaggle_input = Path("/kaggle/input")
    if kaggle_input.exists():
        for config_file in kaggle_input.rglob("config.json"):
            local_models.append(str(config_file.parent))

    cloud_models = list(set(GOOGLE_AI_MODEL_MAP.values())) if genai_client else []

    return {
        "local_models": local_models[:20],
        "cloud_models": cloud_models,
        "suggested": {
            "medgemma-4b": "google/medgemma-1.5-4b-it",
            "medgemma-27b-text": "google/medgemma-27b-it",
            "medgemma-27b-mm": "google/medgemma-27b-mm-it",
        },
    }


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate text – auto-routes to local model or Google AI API.
    
    Routing logic:
    - MedGemma 4B: use local GPU (RTX A4500, 20GB)
    - MedGemma 27B / Gemini: use Google AI API (too large for local GPU)
    """
    # Cloud-only models go straight to API
    if request.model_id in CLOUD_ONLY_MODELS:
        if genai_client is not None:
            try:
                return await generate_via_google_ai(request)
            except Exception as e:
                logger.error(f"Google AI API failed for cloud-only model: {e}")
                raise HTTPException(status_code=500, detail=f"Cloud API failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Model '{request.model_id}' requires Google AI API but GOOGLE_API_KEY not set."
        )

    # Try local model first for local-preferred models
    if _is_local_model_available(request.model_id):
        try:
            return await generate_via_local(request)
        except Exception as e:
            logger.warning(f"Local model failed: {e}; falling back to cloud")

    # Fall back to Google AI API
    if genai_client is not None:
        try:
            return await generate_via_google_ai(request)
        except Exception as e:
            logger.error(f"Google AI API also failed: {e}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    raise HTTPException(
        status_code=500,
        detail=(
            f"Model '{request.model_id}' not available locally and Google AI API not configured. "
            "Set GOOGLE_API_KEY or download local model weights."
        ),
    )


@app.post("/analyze-image")
async def analyze_image(
    image: ImageData,
    image_type: str = "general",
    context: Optional[str] = None,
):
    """Specialized endpoint for image analysis."""
    prompts = {
        "xray": f"Analyze this chest X-ray image. Identify any abnormalities, key findings, and provide a structured radiological assessment. {f'Clinical context: {context}' if context else ''}",
        "dermatology": f"Analyze this dermatological image. Describe the lesion characteristics (ABCDE criteria if applicable), potential differential diagnoses, and recommended next steps. {f'Clinical context: {context}' if context else ''}",
        "pathology": f"Analyze this histopathology image. Describe the tissue architecture, cellular features, and any pathological findings. {f'Clinical context: {context}' if context else ''}",
        "general": f"Analyze this medical image. Describe what you observe and any clinically relevant findings. {f'Clinical context: {context}' if context else ''}",
    }

    request = GenerateRequest(
        model_id=os.getenv("MEDGEMMA_MM_MODEL_ID", "google/medgemma-1.5-4b-it"),
        message=prompts.get(image_type, prompts["general"]),
        images=[image],
        config={"max_new_tokens": 512, "temperature": 0.3},
    )
    return await generate(request)


if __name__ == "__main__":
    import uvicorn

    preload_model = os.getenv("PRELOAD_MODEL")
    if preload_model:
        logger.info(f"Preloading model: {preload_model}")
        get_model_and_processor(preload_model)

    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting MedGemma backend on port {port}")
    logger.info(f"Google AI API: {'available' if genai_client else 'NOT configured (set GOOGLE_API_KEY)'}")
    uvicorn.run(app, host="0.0.0.0", port=port)
