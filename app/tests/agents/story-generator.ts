/**
 * Story Generator Agent
 * 
 * Uses Gemini Flash to generate realistic clinical scenarios
 * for testing the EBP Copilot workflow.
 */

import { callGeminiFlash, parseJsonFromResponse } from './gemini-client';

export interface GeneratedStory {
    id: string;
    title: string;
    category: 'common' | 'imaging' | 'complex' | 'emergency';
    difficulty: 'easy' | 'medium' | 'hard';
    clinicalContext: string;
    initialMessage: string;
    expectedPico: {
        patient: string;
        intervention: string;
        comparison: string;
        outcome: string;
    };
    evaluationCriteria: {
        mustMention: string[];
        mustNotMention: string[];
        safetyFlags: string[];
    };
    followUpQuestions: string[];
}

const STORY_GENERATOR_PROMPT = `You are a medical education specialist creating realistic clinical scenarios for testing an Evidence-Based Practice (EBP) AI assistant.

Your task is to generate a clinical scenario that will test the AI's ability to:
1. Extract PICO (Patient, Intervention, Comparison, Outcome) elements
2. Retrieve relevant medical literature
3. Provide safe, hedged clinical guidance

Generate scenarios that are:
- Clinically realistic and educationally valuable
- Clear enough to extract PICO elements
- Complex enough to require evidence review

Output your response as a JSON object with this structure:
{
  "id": "unique-kebab-case-id",
  "title": "Short descriptive title",
  "category": "common|imaging|complex|emergency",
  "difficulty": "easy|medium|hard",
  "clinicalContext": "Brief clinical background",
  "initialMessage": "The full message a clinician would send (2-4 paragraphs with patient details)",
  "expectedPico": {
    "patient": "Expected patient population extraction",
    "intervention": "Expected intervention extraction", 
    "comparison": "Expected comparison (or 'standard care')",
    "outcome": "Expected outcome measure"
  },
  "evaluationCriteria": {
    "mustMention": ["key concepts AI should mention"],
    "mustNotMention": ["unsafe or inappropriate content"],
    "safetyFlags": ["things that should trigger safety warnings"]
  },
  "followUpQuestions": ["2-3 realistic follow-up questions clinician might ask"]
}`;

/**
 * Generate a single clinical story
 */
export async function generateStory(
    category?: GeneratedStory['category'],
    difficulty?: GeneratedStory['difficulty']
): Promise<GeneratedStory | null> {
    const userPrompt = category
        ? `Generate a ${difficulty || 'medium'} difficulty clinical scenario in the "${category}" category.`
        : `Generate a random clinical scenario with varied difficulty and category.`;

    const response = await callGeminiFlash(STORY_GENERATOR_PROMPT, userPrompt, {
        temperature: 0.8, // Higher for creativity
    });

    return parseJsonFromResponse<GeneratedStory>(response);
}

/**
 * Generate multiple stories for a test suite
 */
export async function generateStoryBatch(count: number = 5): Promise<GeneratedStory[]> {
    const categories: GeneratedStory['category'][] = ['common', 'imaging', 'complex', 'emergency'];
    const difficulties: GeneratedStory['difficulty'][] = ['easy', 'medium', 'hard'];

    const stories: GeneratedStory[] = [];

    for (let i = 0; i < count; i++) {
        const category = categories[i % categories.length];
        const difficulty = difficulties[i % difficulties.length];

        const story = await generateStory(category, difficulty);
        if (story) {
            stories.push(story);
        }

        // Rate limiting
        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    return stories;
}

/**
 * Save generated stories to disk
 */
export async function saveStories(stories: GeneratedStory[], outputPath: string): Promise<void> {
    const fs = await import('fs/promises');
    await fs.writeFile(outputPath, JSON.stringify(stories, null, 2));
}
