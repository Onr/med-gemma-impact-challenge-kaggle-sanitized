# MedGemma EBP Copilot

MedGemma Evidence-Based Practice assistant for the kaggle med-gemma-impact-challenge.

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


## local backend

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

