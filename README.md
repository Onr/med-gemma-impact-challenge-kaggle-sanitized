# MedGemma EBP Copilot

Public, lean version of the MedGemma Evidence-Based Practice assistant.

## What is included

- Frontend app (React + Vite) in `app/`
- Optional Python backend in `app/backend/` for local MedGemma/HuggingFace serving

## Quick start (frontend)

```bash
cd app
npm install
npm run dev
```

Open the local URL printed by Vite (usually `http://localhost:5173`).

## Environment setup

Create `app/.env.local`:

```env
# Cloud API mode
VITE_GOOGLE_API_KEY=your_google_ai_api_key
VITE_GOOGLE_MODEL_ID=gemini-2.0-flash

# Optional: use local backend instead of cloud
# VITE_USE_LOCAL_BACKEND=true
# VITE_BACKEND_URL=http://localhost:8000
```

## Optional local backend

```bash
cd app/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python medgemma_backend.py
```

Then set in `app/.env.local`:

```env
VITE_USE_LOCAL_BACKEND=true
VITE_BACKEND_URL=http://localhost:8000
```

## Build

```bash
cd app
npm run build
npm run preview
```

## Notes

- This repository is intentionally minimized for public sharing.
- Add your own API keys locally; never commit secrets.
