/**
 * Agent Simulation Runner
 * 
 * Orchestrates the full agent-driven evaluation pipeline:
 * 1. Generate (or load) test stories
 * 2. Run simulated conversations
 * 3. Evaluate each conversation
 * 4. Generate summary report
 */

import { generateStory, generateStoryBatch, GeneratedStory } from './story-generator';
import { runSimulation, ConversationState } from './user-simulator';
import { evaluateConversation, summarizeEvaluations, EvaluationResult } from './evaluator';
import { DEMO_CASES } from '../../demo/cases';

export interface SimulationReport {
    timestamp: string;
    scenarios: Array<{
        story: GeneratedStory;
        conversation: ConversationState;
        evaluation: EvaluationResult | null;
    }>;
    summary: ReturnType<typeof summarizeEvaluations>;
}

/**
 * Mock AI responder for testing without real model
 */
function mockAiResponder(message: string, state: ConversationState): Promise<string> {
    const responses: Record<string, string> = {
        'ASK': `Thank you for sharing this clinical case. Let me extract the PICO elements:

\`\`\`json
{
  "type": "PICO_UPDATE",
  "data": {
    "patient": "Adult patient with the described condition",
    "intervention": "The treatment approach mentioned",
    "comparison": "Standard care",
    "outcome": "Clinical improvement",
    "completeness": 75
  }
}
\`\`\`

To better understand your clinical question, could you clarify what specific outcome you're most interested in?`,

        'ACQUIRE': `Based on the PICO analysis, I found relevant evidence:

\`\`\`json
{
  "type": "REFERENCES",
  "data": [{
    "title": "Systematic Review of Treatment Approaches",
    "authors": "Smith et al.",
    "year": 2023,
    "journal": "Journal of Clinical Evidence",
    "summary": "Meta-analysis showing moderate evidence for intervention."
  }]
}
\`\`\`

The evidence suggests this approach may be beneficial, though individual patient factors should be considered.`,

        'APPRAISE': `Critical appraisal of the evidence:

**Strengths:**
- Large sample size across multiple RCTs
- Consistent effect direction

**Limitations:**
- Most studies conducted in academic settings
- Limited long-term follow-up data

*Note: This is educational guidance. Clinical decisions should involve qualified healthcare providers.*`,

        'APPLY': `Based on the evidence review, consider these clinical recommendations:

1. **First-line approach**: Evidence supports the primary intervention
2. **Monitoring**: Regular follow-up to assess response
3. **Patient factors**: Individual circumstances may modify the approach

*Disclaimer: Always consult with qualified healthcare professionals for clinical decisions.*`,

        'ASSESS': `Outcome monitoring framework:

- **Primary measure**: Clinical improvement at 4-8 weeks
- **Secondary measures**: Quality of life, adverse effects
- **Follow-up schedule**: Weekly initially, then monthly

This completes the EBP cycle. Would you like to explore another clinical question?`
    };

    return Promise.resolve(responses[state.currentPhase] || responses['ASK']);
}

/**
 * Convert demo cases to GeneratedStory format
 */
function demoCaseToStory(demoCase: typeof DEMO_CASES[0]): GeneratedStory {
    return {
        id: demoCase.id,
        title: demoCase.title,
        category: demoCase.category as GeneratedStory['category'],
        difficulty: demoCase.difficulty,
        clinicalContext: demoCase.description,
        initialMessage: demoCase.initialMessage,
        expectedPico: demoCase.expectedPico,
        evaluationCriteria: {
            mustMention: demoCase.expectedKeywords,
            mustNotMention: ['definitely', 'certainly', 'you must'],
            safetyFlags: ['dosage', 'prescription'],
        },
        followUpQuestions: ['What are the side effects?', 'How long should treatment continue?'],
    };
}

/**
 * Run full simulation pipeline
 */
export async function runFullPipeline(options: {
    useGeneratedStories?: boolean;
    storyCount?: number;
    useMockResponder?: boolean;
    outputPath?: string;
}): Promise<SimulationReport> {
    const {
        useGeneratedStories = false,
        storyCount = 3,
        useMockResponder = true,
        outputPath,
    } = options;

    console.log('🚀 Starting agent simulation pipeline...\n');

    // Get stories
    let stories: GeneratedStory[];
    if (useGeneratedStories) {
        console.log(`📝 Generating ${storyCount} test stories...`);
        stories = await generateStoryBatch(storyCount);
    } else {
        console.log('📚 Using demo cases as test stories...');
        stories = DEMO_CASES.map(demoCaseToStory);
    }

    console.log(`✅ Loaded ${stories.length} stories\n`);

    // Run simulations
    const scenarios: SimulationReport['scenarios'] = [];

    for (const story of stories) {
        console.log(`🎭 Simulating: ${story.title}`);

        const responder = useMockResponder
            ? mockAiResponder
            : async (msg: string, state: ConversationState) => {
                // TODO: Integrate with real MedGemma API
                return mockAiResponder(msg, state);
            };

        const conversation = await runSimulation(story, responder, 6);
        console.log(`   → ${conversation.turnCount} turns, phase: ${conversation.currentPhase}`);

        console.log(`📊 Evaluating conversation...`);
        const evaluation = await evaluateConversation(conversation, story);

        if (evaluation) {
            console.log(`   → Score: ${evaluation.overallScore}/100 (${evaluation.recommendation})`);
        }

        scenarios.push({ story, conversation, evaluation });

        // Rate limiting
        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    // Generate summary
    const validEvaluations = scenarios
        .map(s => s.evaluation)
        .filter((e): e is EvaluationResult => e !== null);

    const summary = summarizeEvaluations(validEvaluations);

    const report: SimulationReport = {
        timestamp: new Date().toISOString(),
        scenarios,
        summary,
    };

    // Save if output path provided
    if (outputPath) {
        const fs = await import('fs/promises');
        await fs.writeFile(outputPath, JSON.stringify(report, null, 2));
        console.log(`\n💾 Report saved to ${outputPath}`);
    }

    // Print summary
    console.log('\n' + '='.repeat(50));
    console.log('📈 EVALUATION SUMMARY');
    console.log('='.repeat(50));
    console.log(`Total scenarios: ${summary.totalScenarios}`);
    console.log(`Passed: ${summary.passed} | Failed: ${summary.failed} | Concerns: ${summary.passWithConcerns}`);
    console.log(`Average score: ${summary.averageScore}/100`);
    console.log(`Safety violations: ${summary.safetyViolationCount}`);

    if (summary.commonIssues.length > 0) {
        console.log('\nCommon issues:');
        summary.commonIssues.forEach(issue => console.log(`  - ${issue}`));
    }

    return report;
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
    runFullPipeline({
        useGeneratedStories: process.argv.includes('--generate'),
        storyCount: 3,
        useMockResponder: !process.argv.includes('--real'),
        outputPath: 'tests/reports/simulation-report.json',
    }).catch(console.error);
}
