/**
 * MedGemma Service
 * 
 * Supports both Google AI API (cloud) and custom backend (for HuggingFace/Kaggle deployments)
 */

import { GoogleGenAI, Part } from "@google/genai";
import { Message, Role, Phase } from "../types";
import { getSystemPrompt } from "../constants";

// --- Configuration ---
export type ModelProvider = 'google-ai' | 'custom-backend';

export interface MedGemmaConfig {
  provider: ModelProvider;
  // For Google AI API
  googleApiKey?: string;
  googleModelId?: string;
  // For custom backend (HuggingFace inference server, etc.)
  backendUrl?: string;
}

const env = import.meta.env;
const useLocalBackend = env.VITE_USE_LOCAL_BACKEND === 'true' || !!env.VITE_BACKEND_URL;

// Resolve backend URL dynamically: if user accesses the frontend remotely
// (e.g., via Tailscale/LAN IP), use that same hostname for the backend.
const resolveBackendUrl = (): string => {
  if (env.VITE_BACKEND_URL) return env.VITE_BACKEND_URL;
  const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  return `http://${host}:8000`;
};
const modelIdOverrides: Partial<Record<'medgemma-4b-it' | 'medgemma-27b-text' | 'medgemma-27b-mm', string | undefined>> =
  useLocalBackend ? {
    'medgemma-4b-it': env.VITE_MEDGEMMA_4B_MODEL_ID,
    'medgemma-27b-text': env.VITE_MEDGEMMA_27B_TEXT_MODEL_ID,
    'medgemma-27b-mm': env.VITE_MEDGEMMA_27B_MM_MODEL_ID
  } : {};

// Available MedGemma models
export const MEDGEMMA_MODELS = {
  // Via Google AI API (if available)
  'medgemma-4b-it': {
    id: modelIdOverrides['medgemma-4b-it'] || 'google/medgemma-4b-it',
    name: 'MedGemma 4B (Local GPU)',
    supportsImages: true,
    description: 'Local multimodal model for medical text + image'
  },
  'medgemma-27b-text': {
    id: modelIdOverrides['medgemma-27b-text'] || 'google/medgemma-27b-it',
    name: 'MedGemma 27B (Text)',
    supportsImages: false,
    description: 'Largest text-only model for complex reasoning'
  },
  'medgemma-27b-mm': {
    id: modelIdOverrides['medgemma-27b-mm'] || 'google/medgemma-27b-mm-it',
    name: 'MedGemma 27B (Multimodal)',
    supportsImages: true,
    description: 'Largest multimodal model'
  },
  // Fallback to Gemini if MedGemma not available
  'gemini-flash': {
    id: 'gemini-3-flash-preview',
    name: 'Gemini Flash (Fallback)',
    supportsImages: true,
    description: 'General Gemini model with medical prompting'
  }
} as const;

export type ModelKey = keyof typeof MEDGEMMA_MODELS;

// --- Default Config ---
const defaultConfig: MedGemmaConfig = (() => {
  if (useLocalBackend) {
    return {
      provider: 'custom-backend',
      backendUrl: resolveBackendUrl(),
      googleApiKey: env.VITE_GOOGLE_API_KEY || env.VITE_API_KEY,
      googleModelId: env.VITE_GOOGLE_MODEL_ID || 'gemini-2.0-flash'
    };
  }
  return {
    provider: 'google-ai',
    googleApiKey: env.VITE_GOOGLE_API_KEY || env.VITE_API_KEY,
    googleModelId: env.VITE_GOOGLE_MODEL_ID || 'gemini-2.0-flash'
  };
})();

let currentConfig: MedGemmaConfig = { ...defaultConfig };
let aiClient: GoogleGenAI | null = null;

// --- Initialize/Update Config ---
export const initMedGemma = (config: Partial<MedGemmaConfig>) => {
  currentConfig = { ...currentConfig, ...config };
  if (currentConfig.googleApiKey) {
    aiClient = new GoogleGenAI({ apiKey: currentConfig.googleApiKey });
  }
};

// Initialize on module load
initMedGemma({});

// --- Helper: Convert image to base64 for API ---
export const imageToBase64 = async (file: File): Promise<{ mimeType: string; data: string }> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // Remove data URL prefix (e.g., "data:image/png;base64,")
      const base64 = result.split(',')[1];
      resolve({
        mimeType: file.type,
        data: base64
      });
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};

// --- Helper: Extract JSON from response ---
const extractJson = (text: string): { text: string; extractedData: any | null } => {
  const jsonRegex = /```(?:json)?\s*(\{[\s\S]*?\})\s*```/i;
  const match = text.match(jsonRegex);

  if (match && match[1]) {
    try {
      const data = JSON.parse(match[1]);
      const cleanText = text.replace(jsonRegex, '').trim();
      return { text: cleanText, extractedData: data };
    } catch (e) {
      console.error("Failed to parse JSON from model response", e);
    }
  }
  return { text: text, extractedData: null };
};

// --- Image Analysis Prompt Templates ---
export const getImageAnalysisPrompt = (imageType: 'xray' | 'dermatology' | 'pathology' | 'general', context?: string) => {
  const prompts: Record<string, string> = {
    xray: `Analyze this chest X-ray image. Identify any abnormalities, key findings, and provide a structured radiological assessment. ${context ? `Clinical context: ${context}` : ''}`,
    dermatology: `Analyze this dermatological image. Describe the lesion characteristics (ABCDE criteria if applicable), potential differential diagnoses, and recommended next steps. ${context ? `Clinical context: ${context}` : ''}`,
    pathology: `Analyze this histopathology image. Describe the tissue architecture, cellular features, and any pathological findings. ${context ? `Clinical context: ${context}` : ''}`,
    general: `Analyze this medical image. Describe what you observe and any clinically relevant findings. ${context ? `Clinical context: ${context}` : ''}`
  };
  return prompts[imageType] || prompts.general;
};

// --- Main API: Send Message with Optional Images ---
export interface MessageInput {
  text: string;
  images?: Array<{ mimeType: string; data: string }>;
}

export const sendMessageToMedGemma = async (
  history: Message[],
  newMessage: MessageInput,
  role: Role,
  phase: Phase,
  patientContext: string,
  modelKey: ModelKey = 'gemini-flash'
): Promise<{ text: string; extractedData: any | null }> => {
  
  const modelConfig = MEDGEMMA_MODELS[modelKey];
  
  // Validate image support
  if (newMessage.images?.length && !modelConfig.supportsImages) {
    return {
      text: `The selected model (${modelConfig.name}) does not support image analysis. Please switch to a multimodal model.`,
      extractedData: null
    };
  }

  // Route to appropriate provider
  if (currentConfig.provider === 'google-ai') {
    return sendViaGoogleAI(history, newMessage, role, phase, patientContext, modelConfig.id);
  } else {
    return sendViaBackend(history, newMessage, role, phase, patientContext, modelConfig.id);
  }
};

// --- Google AI API Implementation ---
const sendViaGoogleAI = async (
  history: Message[],
  newMessage: MessageInput,
  role: Role,
  phase: Phase,
  patientContext: string,
  modelId: string
): Promise<{ text: string; extractedData: any | null }> => {
  
  if (!aiClient) {
    return {
      text: "AI client not initialized. Please check your API key.",
      extractedData: null
    };
  }

  try {
    const systemInstruction = getSystemPrompt(role, phase, patientContext);

    // Build message parts (text + optional images)
    const userParts: Part[] = [];
    
    // Add images first if present
    if (newMessage.images?.length) {
      for (const img of newMessage.images) {
        userParts.push({
          inlineData: {
            mimeType: img.mimeType,
            data: img.data
          }
        });
      }
    }
    
    // Add text
    userParts.push({ text: newMessage.text });

    // Build conversation contents
    const contents = [
      ...history.map(m => ({
        role: m.role,
        parts: [{ text: m.content }]
      })),
      {
        role: 'user' as const,
        parts: userParts
      }
    ];

    const response = await aiClient.models.generateContent({
      model: modelId,
      contents: contents,
      config: {
        systemInstruction: systemInstruction,
        temperature: 0.7,
      }
    });

    const responseText = response.text || "I apologize, but I couldn't generate a response.";
    return extractJson(responseText);

  } catch (error) {
    console.error("MedGemma API Error:", error);
    return {
      text: "I encountered an error connecting to the AI service. Please check your network or API key.",
      extractedData: null
    };
  }
};

// --- Custom Backend Implementation (for HuggingFace/Kaggle) ---
const sendViaBackend = async (
  history: Message[],
  newMessage: MessageInput,
  role: Role,
  phase: Phase,
  patientContext: string,
  modelId: string
): Promise<{ text: string; extractedData: any | null }> => {
  
  if (!currentConfig.backendUrl) {
    return {
      text: "Backend URL not configured. Please set backendUrl in the config.",
      extractedData: null
    };
  }

  try {
    const response = await fetch(currentConfig.backendUrl + '/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model_id: modelId,
        history: history.map(m => ({ role: m.role, content: m.content })),
        message: newMessage.text,
        images: newMessage.images,
        system_prompt: getSystemPrompt(role, phase, patientContext),
        config: {
          max_new_tokens: 1024,
          temperature: 0.7,
        }
      })
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof data?.detail === 'string' ? data.detail : '';
      throw new Error(`Backend returned ${response.status}${detail ? `: ${detail}` : ''}`);
    }
    return extractJson(data.text || data.generated_text || '');

  } catch (error) {
    console.error("Backend API Error:", error);
    if (currentConfig.googleApiKey && aiClient) {
      try {
        const fallbackModel = env.VITE_GOOGLE_MODEL_ID || 'gemini-2.0-flash';
        const fallback = await sendViaGoogleAI(history, newMessage, role, phase, patientContext, fallbackModel);
        return {
          text: `Backend unavailable; used cloud model fallback.\n\n${fallback.text}`,
          extractedData: fallback.extractedData
        };
      } catch (fallbackError) {
        console.error("Fallback Google AI Error:", fallbackError);
      }
    }
    const isNetworkError = error instanceof TypeError && (error as TypeError).message === 'Failed to fetch';
    const errorDetail = isNetworkError
      ? `**Backend service is not reachable** at \`${currentConfig.backendUrl}\`.\n\n` +
        `Troubleshooting:\n` +
        `1. Start the backend: \`cd app/backend && python medgemma_backend.py\`\n` +
        `2. Verify it's running: \`curl ${currentConfig.backendUrl}/health\`\n` +
        `3. Or switch to Google AI provider in settings if no local GPU is available.`
      : `I encountered an error connecting to the backend service. ${error instanceof Error ? error.message : 'Unknown error'}`;
    return {
      text: errorDetail,
      extractedData: null
    };
  }
};

// --- Specialized Image Analysis ---
export const analyzeImage = async (
  imageData: { mimeType: string; data: string },
  imageType: 'xray' | 'dermatology' | 'pathology' | 'general',
  additionalContext?: string,
  modelKey: ModelKey = 'medgemma-4b-it'
): Promise<{ text: string; findings: any | null }> => {
  
  const prompt = getImageAnalysisPrompt(imageType, additionalContext);
  
  const result = await sendMessageToMedGemma(
    [], // No history for standalone analysis
    { text: prompt, images: [imageData] },
    Role.PHYSICIAN,
    Phase.ASK,
    additionalContext || '',
    modelKey
  );

  return {
    text: result.text,
    findings: result.extractedData
  };
};

// Export for backward compatibility
export const sendMessageToGemini = async (
  history: Message[],
  newMessage: string,
  role: Role,
  phase: Phase,
  patientContext: string
) => sendMessageToMedGemma(
  history,
  { text: newMessage },
  role,
  phase,
  patientContext,
  'gemini-flash'
);
