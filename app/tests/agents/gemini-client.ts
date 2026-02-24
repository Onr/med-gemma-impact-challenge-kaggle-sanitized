/**
 * Gemini Flash Client for Agent Operations
 * 
 * Provides a typed interface to Gemini Flash API for agent tasks:
 * - Story generation
 * - User simulation  
 * - Response evaluation
 */

import { GoogleGenAI } from '@google/genai';

// Use environment variable or fallback
const API_KEY = process.env.VITE_GOOGLE_API_KEY || process.env.GOOGLE_API_KEY || '';

const ai = new GoogleGenAI({ apiKey: API_KEY });

export interface AgentConfig {
    model?: string;
    temperature?: number;
    maxTokens?: number;
}

const DEFAULT_CONFIG: AgentConfig = {
    model: 'gemini-2.0-flash',
    temperature: 0.7,
    maxTokens: 4096,
};

/**
 * Send a prompt to Gemini Flash and get structured response
 */
export async function callGeminiFlash(
    systemPrompt: string,
    userPrompt: string,
    config: Partial<AgentConfig> = {}
): Promise<string> {
    const mergedConfig = { ...DEFAULT_CONFIG, ...config };

    try {
        const response = await ai.models.generateContent({
            model: mergedConfig.model!,
            contents: [
                { role: 'user', parts: [{ text: `${systemPrompt}\n\n${userPrompt}` }] }
            ],
            config: {
                temperature: mergedConfig.temperature,
                maxOutputTokens: mergedConfig.maxTokens,
            }
        });

        return response.text || '';
    } catch (error) {
        console.error('Gemini Flash API error:', error);
        throw error;
    }
}

/**
 * Parse JSON from LLM response (handles markdown code blocks)
 */
export function parseJsonFromResponse<T>(response: string): T | null {
    try {
        // Try direct parse first
        return JSON.parse(response);
    } catch {
        // Try extracting from markdown code block
        const jsonMatch = response.match(/```(?:json)?\s*([\s\S]*?)```/);
        if (jsonMatch) {
            try {
                return JSON.parse(jsonMatch[1].trim());
            } catch {
                return null;
            }
        }
        return null;
    }
}
