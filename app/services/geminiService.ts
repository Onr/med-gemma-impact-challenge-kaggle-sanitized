
import { GoogleGenAI } from "@google/genai";
import { Message, Role, Phase } from "../types";
import { getSystemPrompt } from "../constants";

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

// Helper to extract JSON from response text
const extractJson = (text: string): { text: string; extractedData: any | null } => {
  // Regex to capture JSON block, handling optional "json" language tag and loose spacing
  // Matches ``` followed optionally by json, then captures content, then ```
  const jsonRegex = /```(?:json)?\s*(\{[\s\S]*?\})\s*```/i;
  const match = text.match(jsonRegex);

  if (match && match[1]) {
    try {
      const data = JSON.parse(match[1]);
      // Remove the entire code block from the text
      const cleanText = text.replace(jsonRegex, '').trim();
      return { text: cleanText, extractedData: data };
    } catch (e) {
      console.error("Failed to parse JSON from model response", e);
      // If parsing fails, try to return text without the broken block if possible, 
      // or just return original text.
    }
  }
  return { text: text, extractedData: null };
};

export const sendMessageToGemini = async (
  history: Message[],
  newMessage: string,
  role: Role,
  phase: Phase,
  patientContext: string
): Promise<{ text: string; extractedData: any | null }> => {
  try {
    const systemInstruction = getSystemPrompt(role, phase, patientContext);

    const contents = [
       ...history.map(m => ({
         role: m.role,
         parts: [{ text: m.content }]
       })),
       {
         role: 'user',
         parts: [{ text: newMessage }]
       }
    ];

    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: contents,
      config: {
        systemInstruction: systemInstruction,
        temperature: 0.7,
      }
    });

    const responseText = response.text || "I apologize, but I couldn't generate a response.";
    return extractJson(responseText);

  } catch (error) {
    console.error("Gemini API Error:", error);
    return {
      text: "I encountered an error connecting to the AI service. Please check your network or API key.",
      extractedData: null
    };
  }
};
