# Local-Only MedGemma Setup

This guide explains how to run MedGemma **completely locally** without any cloud APIs.

## Quick Answer: Yes, It Works Locally! ✅

The app can run 100% locally using:
- **HuggingFace Transformers** for model inference
- **Local model files** (downloaded or from Kaggle datasets)
- **Python backend** (FastAPI) serving the frontend

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    LOCAL SETUP                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐      ┌───────────────────────┐   │
│  │   Frontend   │ ───► │   Python Backend      │   │
│  │   (React)    │      │   (FastAPI)           │   │
│  │   Port 5173  │      │   Port 8000           │   │
│  └──────────────┘      └───────────────────────┘   │
│                               │                     │
│                               ▼                     │
│                        ┌──────────────────┐        │
│                        │   MedGemma Model │        │
│                        │   (HuggingFace)  │        │
│                        │   Local Files    │        │
│                        └──────────────────┘        │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## Option 1: Quick Test (No Frontend, No GPU)

Test the workflow with simulated responses:

```bash
cd app/backend

# Run mock test (no dependencies needed beyond Python)
python quick_test.py

# Run full EBP workflow simulation
python test_medgemma_local.py --mock

# Interactive mode
python test_medgemma_local.py --mock --interactive
```

---

## Option 2: Test with Real Model (GPU Required)

### Step 1: Install Dependencies

```bash
cd app/backend
pip install -r requirements.txt

# Or manually:
pip install torch transformers accelerate pillow
```

### Step 2: Set Up HuggingFace Token (for gated models)

MedGemma models require approval. Get access at:
https://huggingface.co/google/medgemma-1.5-4b-it

```bash
# Option A: Environment variable
export HF_TOKEN=hf_your_token_here

# Option B: HuggingFace CLI login
huggingface-cli login
```

### Step 3: Run Tests

```bash
# Check environment
python quick_test.py --check

# Test with real model
python quick_test.py --model google/medgemma-1.5-4b-it

# Full workflow test
python test_medgemma_local.py --model google/medgemma-1.5-4b-it

# Interactive mode
python test_medgemma_local.py --model google/medgemma-1.5-4b-it --interactive
```

---

## Option 3: Full Stack (Frontend + Backend)

### Step 1: Start Backend

```bash
cd app/backend

# Install dependencies
pip install -r requirements.txt

# Set HF token
export HF_TOKEN=hf_your_token_here

# Optional: Preload model for faster first request
export PRELOAD_MODEL=google/medgemma-1.5-4b-it

# Start server
python medgemma_backend.py
```

Backend will be available at `http://localhost:8000`

### Step 2: Configure Frontend for Local Backend

Create/edit `app/.env.local`:

```env
# Use custom backend instead of Google AI API
VITE_BACKEND_URL=http://localhost:8000
VITE_USE_LOCAL_BACKEND=true

# Optional: override model IDs/paths
# VITE_MEDGEMMA_4B_MODEL_ID=/kaggle/input/medgemma-4b-it
# VITE_MEDGEMMA_27B_TEXT_MODEL_ID=/kaggle/input/medgemma-27b-it
# VITE_MEDGEMMA_27B_MM_MODEL_ID=/kaggle/input/medgemma-27b-mm-it
```

Or modify `app/services/medGemmaService.ts`:

```typescript
// Change default config
const defaultConfig: MedGemmaConfig = {
  provider: 'custom-backend',  // Changed from 'google-ai'
  backendUrl: 'http://localhost:8000',
};
```

### Step 3: Start Frontend

```bash
cd app
npm install
npm run dev
```

Frontend will be at `http://localhost:5173`

---

## Option 4: Kaggle Environment

If you have models as Kaggle datasets:

```bash
# Models are typically at /kaggle/input/model-name/
export MEDGEMMA_4B_MODEL_ID=/kaggle/input/medgemma-4b-it/

# Run test
python test_medgemma_local.py --model /kaggle/input/medgemma-4b-it/

# Or start backend
export PRELOAD_MODEL=/kaggle/input/medgemma-4b-it/
python medgemma_backend.py
```

If you prefer KaggleHub downloads, you can use a `kagglehub:` handle:

```bash
# Example handle (adjust to the model you have access to)
python test_medgemma_local.py --model kagglehub:keras/medgemma/keras/medgemma_1.5_instruct_4b
```

Note: KaggleHub models may be Keras-native; the backend expects a HuggingFace-style folder
with a `config.json`. If you see a "no config.json" error, use a Transformers-compatible
checkpoint instead.

---

## Available Test Scripts

| Script | Purpose | GPU Required? |
|--------|---------|---------------|
| `quick_test.py` | Minimal sanity check | No (with --mock) |
| `quick_test.py --check` | Environment verification | No |
| `quick_test.py --model X` | Single model test | Yes |
| `test_medgemma_local.py --mock` | Full EBP workflow (simulated) | No |
| `test_medgemma_local.py --model X` | Full EBP workflow (real) | Yes |
| `test_medgemma_local.py --interactive` | Interactive chat | Depends |
| `medgemma_backend.py` | Full API server | Yes |

---

## Model Options

| Model | HuggingFace ID | VRAM Required |
|-------|----------------|---------------|
| MedGemma 4B | `google/medgemma-1.5-4b-it` | ~10GB |
| MedGemma 27B | `google/medgemma-27b-it` | ~60GB |

For limited VRAM, use quantization:

```python
from transformers import BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16
)

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb_config,
    device_map="auto"
)
```

---

## Troubleshooting

### "Cannot find module 'torch'"
```bash
pip install torch
```

### "CUDA out of memory"
- Use smaller model (4B instead of 27B)
- Enable 4-bit quantization (see above)
- Use CPU (slower): `--device cpu`

### "401 Unauthorized" from HuggingFace
- Request model access at HuggingFace
- Set `HF_TOKEN` environment variable

### "Model not found"
- Check the model ID is correct
- For local paths, ensure the directory contains `config.json`

---

## Summary

| What You Want | What to Run |
|---------------|-------------|
| Just test the workflow | `python test_medgemma_local.py --mock` |
| Test with real AI | `python test_medgemma_local.py --model google/medgemma-1.5-4b-it` |
| Interactive chat | `python test_medgemma_local.py --mock --interactive` |
| Full app locally | Backend + Frontend (see Option 3) |
