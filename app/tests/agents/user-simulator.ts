/**
 * User Simulator Agent
 * 
 * Uses Gemini Flash to simulate realistic clinician interactions
 * with the EBP Copilot, generating follow-up messages and
 * evaluating whether to continue the conversation.
 */

import { callGeminiFlash, parseJsonFromResponse } from './gemini-client';
import { GeneratedStory } from './story-generator';

export interface SimulatedInteraction {
    userMessage: string;
    intent: 'ask_question' | 'provide_info' | 'request_clarification' | 'move_phase' | 'end_session';
    expectedBehavior: string;
    assertionsToCheck: string[];
}

export interface ConversationState {
    story: GeneratedStory;
    messages: Array<{ role: 'user' | 'assistant'; content: string }>;
    currentPhase: 'ASK' | 'ACQUIRE' | 'APPRAISE' | 'APPLY' | 'ASSESS';
    picoExtracted: boolean;
    referencesRetrieved: boolean;
    turnCount: number;
}

const USER_SIMULATOR_PROMPT = `You are simulating a busy clinician interacting with an EBP (Evidence-Based Practice) AI assistant.

You should behave realistically:
- Ask focused clinical questions
- Provide additional patient details when asked
- Request clarification if the AI's response is unclear
- Move to the next phase when ready
- End the session when you have enough information

Based on the current conversation state, generate the next user message.

Output JSON:
{
  "userMessage": "The message you would send",
  "intent": "ask_question|provide_info|request_clarification|move_phase|end_session",
  "expectedBehavior": "What you expect the AI to do",
  "assertionsToCheck": ["Things to verify in the AI's response"]
}`;

/**
 * Generate the next user message in a simulation
 */
export async function generateNextUserMessage(
    state: ConversationState
): Promise<SimulatedInteraction | null> {
    const contextPrompt = `
SCENARIO: ${state.story.title}
CLINICAL CONTEXT: ${state.story.clinicalContext}
CURRENT PHASE: ${state.currentPhase}
TURN: ${state.turnCount}
PICO EXTRACTED: ${state.picoExtracted}
REFERENCES RETRIEVED: ${state.referencesRetrieved}

CONVERSATION HISTORY:
${state.messages.map(m => `${m.role.toUpperCase()}: ${m.content}`).join('\n\n')}

Generate the next realistic user message. Consider:
- If PICO is not extracted, provide more details
- If in ACQUIRE phase and refs retrieved, ask about evidence quality
- If in APPRAISE, ask about limitations
- If turn count > 8, consider ending the session
`;

    const response = await callGeminiFlash(USER_SIMULATOR_PROMPT, contextPrompt, {
        temperature: 0.7,
    });

    return parseJsonFromResponse<SimulatedInteraction>(response);
}

/**
 * Initialize a new conversation state from a story
 */
export function initializeConversation(story: GeneratedStory): ConversationState {
    return {
        story,
        messages: [
            { role: 'user', content: story.initialMessage }
        ],
        currentPhase: 'ASK',
        picoExtracted: false,
        referencesRetrieved: false,
        turnCount: 1,
    };
}

/**
 * Update conversation state after AI response
 */
export function updateConversationState(
    state: ConversationState,
    aiResponse: string,
    newPhase?: ConversationState['currentPhase']
): ConversationState {
    return {
        ...state,
        messages: [...state.messages, { role: 'assistant', content: aiResponse }],
        currentPhase: newPhase || state.currentPhase,
        picoExtracted: state.picoExtracted || aiResponse.includes('PICO_UPDATE'),
        referencesRetrieved: state.referencesRetrieved || aiResponse.includes('REFERENCES'),
        turnCount: state.turnCount + 1,
    };
}

/**
 * Run a full simulated conversation
 */
export async function runSimulation(
    story: GeneratedStory,
    aiResponder: (message: string, state: ConversationState) => Promise<string>,
    maxTurns: number = 10
): Promise<ConversationState> {
    let state = initializeConversation(story);

    // Get initial AI response
    const initialResponse = await aiResponder(story.initialMessage, state);
    state = updateConversationState(state, initialResponse);

    while (state.turnCount < maxTurns) {
        // Generate next user message
        const nextInteraction = await generateNextUserMessage(state);

        if (!nextInteraction || nextInteraction.intent === 'end_session') {
            break;
        }

        // Add user message
        state.messages.push({ role: 'user', content: nextInteraction.userMessage });
        state.turnCount++;

        // Get AI response
        const aiResponse = await aiResponder(nextInteraction.userMessage, state);
        state = updateConversationState(state, aiResponse);

        // Rate limiting
        await new Promise(resolve => setTimeout(resolve, 500));
    }

    return state;
}
