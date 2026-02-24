<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# MedGemma EBP Copilot

An Evidence-Based Practice (EBP) assistant powered by MedGemma, Google's medical AI model.

## Features

- **PICO Framework**: Structured clinical question formulation
- **Multi-Phase EBP Workflow**: ASK → ACQUIRE → APPRAISE → APPLY → ASSESS
- **Medical Image Analysis**: Upload X-rays, dermoscopy, pathology images for AI analysis
- **Model Selection**: Choose between MedGemma 4B (fast) and 27B (advanced) models
- **Voice Input**: Speech-to-text for hands-free operation

## Run Locally

### Option 1: Google AI API (Cloud)

**Prerequisites:** Node.js, Gemini/MedGemma API key

1. Install dependencies:
   ```bash
   npm install
   ```

2. Set the `VITE_GOOGLE_API_KEY` in `.env.local` to your Google AI API key:
   ```
   VITE_GOOGLE_API_KEY=your_api_key_here
   VITE_GOOGLE_MODEL_ID=gemini-2.0-flash
   ```

3. Run the app:
   ```bash
   npm run dev
   ```

### Option 2: Local/Kaggle Backend (HuggingFace Models)

For running MedGemma locally or on Kaggle with HuggingFace Transformers:

1. **Start the backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   
   # Optional: Set HuggingFace token for gated models
   export HF_TOKEN=your_huggingface_token
   
   # Optional: Preload a model
   export PRELOAD_MODEL=google/medgemma-1.5-4b-it
   
   python medgemma_backend.py
   ```

2. **Configure the frontend** to use the custom backend (via `.env.local`):
   ```env
   VITE_USE_LOCAL_BACKEND=true
   VITE_BACKEND_URL=http://localhost:8000
   ```
   Optional: override model IDs/paths (use local paths on Kaggle):
   ```env
   VITE_MEDGEMMA_4B_MODEL_ID=/kaggle/input/medgemma-4b-it
   VITE_MEDGEMMA_27B_TEXT_MODEL_ID=/kaggle/input/medgemma-27b-it
   VITE_MEDGEMMA_27B_MM_MODEL_ID=/kaggle/input/medgemma-27b-mm-it
   ```

3. **Run the frontend:**
   ```bash
   npm install
   npm run dev
   ```

## Available MedGemma Models

| Model | Type | Best For |
|-------|------|----------|
| MedGemma 4B | Multimodal | Fast image + text analysis |
| MedGemma 27B (Text) | Text-only | Complex clinical reasoning |
| MedGemma 27B (MM) | Multimodal | Advanced image understanding |
| Gemini Flash | Multimodal | Fallback / general use |

## Kaggle Model Notes

- If you mount Kaggle Models as datasets, they usually appear under `/kaggle/input/...`.
- Set the `VITE_MEDGEMMA_*_MODEL_ID` environment variables to those local paths so the frontend sends a local path to the backend.
- The backend also accepts `kagglehub:` handles (e.g., `kagglehub:your/handle`) if you prefer to download via KaggleHub.

## Image Analysis Support

The app supports analysis of:
- **Chest X-rays**: Radiological findings, abnormality detection
- **Dermoscopy**: Skin lesion assessment, ABCDE criteria
- **Histopathology**: Tissue architecture, cellular features
- **General medical images**: CT, MRI, clinical photos

## Project Structure

```
app/
├── components/
│   ├── ChatPanel.tsx      # Main chat interface with image upload
│   ├── ImageUpload.tsx    # Medical image upload component
│   ├── ModelSelector.tsx  # AI model selection
│   └── ...
├── services/
│   ├── medGemmaService.ts # MedGemma API integration
│   └── geminiService.ts   # Legacy Gemini service
├── backend/
│   ├── medgemma_backend.py # Python FastAPI backend
│   └── requirements.txt
└── types.ts               # TypeScript interfaces
```

## API Reference

### MedGemma Service

```typescript
import { 
  sendMessageToMedGemma, 
  analyzeImage,
  MEDGEMMA_MODELS 
} from './services/medGemmaService';

// Send message with optional images
const response = await sendMessageToMedGemma(
  history,
  { text: "What do you see?", images: [{ mimeType: 'image/png', data: base64Data }] },
  Role.PHYSICIAN,
  Phase.ASK,
  patientContext,
  'medgemma-4b-it'
);

// Standalone image analysis
const result = await analyzeImage(
  { mimeType: 'image/jpeg', data: base64XrayData },
  'xray',
  'Patient with chronic cough'
);
```
