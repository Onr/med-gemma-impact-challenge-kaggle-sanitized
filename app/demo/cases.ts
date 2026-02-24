/**
 * Demo Medical Cases for MedGemma EBP Copilot
 * 
 * Three realistic clinical scenarios to demonstrate the workflow:
 * 1. Diabetes management (common condition)
 * 2. Chest X-ray interpretation (image-based)
 * 3. Complex differential diagnosis
 */

import { Phase, Role, PicoData } from '../types';

export interface DemoCase {
    id: string;
    title: string;
    description: string;
    category: 'common' | 'imaging' | 'complex';
    difficulty: 'easy' | 'medium' | 'hard';
    suggestedRole: Role;
    initialMessage: string;
    expectedPico: PicoData;
    expectedKeywords: string[];
    notes: string;
}

export const DEMO_CASES: DemoCase[] = [
    // =========================================================================
    // Case 1: Common Condition - Type 2 Diabetes & GLP-1 Agonists
    // =========================================================================
    {
        id: 'diabetes-glp1',
        title: 'GLP-1 Agonists for Weight Loss in T2DM',
        description: 'Elderly diabetic patient considering GLP-1 receptor agonists for weight loss and glycemic control',
        category: 'common',
        difficulty: 'easy',
        suggestedRole: Role.PHYSICIAN,
        initialMessage: `I have a 68-year-old male patient with type 2 diabetes mellitus (HbA1c 8.2%), BMI 34, currently on metformin 1000mg BID. He's interested in losing weight and has heard about "those new diabetes shots" for weight loss. 

He has a history of mild CKD (eGFR 55), no cardiovascular events but moderate risk. His insurance has approved semaglutide.

I'm wondering if GLP-1 agonists would be beneficial compared to adding a sulfonylurea or SGLT2 inhibitor. What does the evidence say about weight loss and cardiovascular outcomes?`,
        expectedPico: {
            patient: 'elderly patients with type 2 diabetes and obesity, with mild CKD',
            intervention: 'GLP-1 receptor agonists (semaglutide)',
            comparison: 'sulfonylurea or SGLT2 inhibitors',
            outcome: 'weight loss and cardiovascular outcomes',
            completeness: 100
        },
        expectedKeywords: ['semaglutide', 'GLP-1', 'weight loss', 'cardiovascular', 'diabetes', 'HbA1c'],
        notes: 'Well-defined PICO, good PubMed coverage, clear clinical decision point'
    },

    // =========================================================================
    // Case 2: Image-Based - Chest X-ray Interpretation
    // =========================================================================
    {
        id: 'chest-xray-pneumonia',
        title: 'Community-Acquired Pneumonia Management',
        description: 'Patient presenting with respiratory symptoms, requiring imaging interpretation and treatment decision',
        category: 'imaging',
        difficulty: 'medium',
        suggestedRole: Role.PHYSICIAN,
        initialMessage: `45-year-old female presents to urgent care with 4 days of productive cough (yellow-green sputum), fever (101.2°F), and right-sided pleuritic chest pain. 

Vital signs: HR 98, RR 22, SpO2 94% on room air, BP 118/72
Physical exam: Decreased breath sounds and dullness to percussion right lower lobe, crackles present

I've ordered a chest X-ray which shows right lower lobe consolidation. CURB-65 score is 1 (respiratory rate only).

Should this patient be treated as outpatient with oral antibiotics, or does she need admission? What antibiotic regimen would be most appropriate?`,
        expectedPico: {
            patient: 'adults with community-acquired pneumonia (CURB-65 score 1)',
            intervention: 'outpatient oral antibiotic therapy',
            comparison: 'inpatient IV antibiotic therapy',
            outcome: 'treatment success and complications',
            completeness: 100
        },
        expectedKeywords: ['pneumonia', 'community-acquired', 'CURB-65', 'antibiotics', 'outpatient'],
        notes: 'Demonstrates image discussion capability, clear treatment guidelines exist'
    },

    // =========================================================================
    // Case 3: Complex Differential - Chronic Fatigue with Multiple Findings
    // =========================================================================
    {
        id: 'fatigue-differential',
        title: 'Unexplained Chronic Fatigue Workup',
        description: 'Complex differential diagnosis requiring systematic evidence-based approach',
        category: 'complex',
        difficulty: 'hard',
        suggestedRole: Role.PHYSICIAN,
        initialMessage: `32-year-old female presenting with progressive fatigue over 6 months, not improved with rest. She reports brain fog, muscle aches, and occasional joint pain without swelling. No fever, weight loss is 5 lbs unintentional.

PMH: Hashimoto's thyroiditis on levothyroxine 75mcg (TSH 2.1 last month)
Social: Teacher, high stress job, poor sleep quality, no substances

Labs: 
- CBC: Hgb 11.2, MCV 82, otherwise normal
- CMP: Normal
- TSH 2.1, Free T4 1.0
- Ferritin 18 ng/mL (low normal)
- Vitamin D 22 ng/mL (insufficient)
- ANA negative, ESR 12, CRP 0.4

She's frustrated because "everything looks normal." How should I approach the workup? Should I check for fibromyalgia, chronic fatigue syndrome, or continue testing?`,
        expectedPico: {
            patient: 'young women with chronic fatigue and Hashimoto thyroiditis',
            intervention: 'systematic diagnostic workup (iron/vitamin D repletion, fibromyalgia screening)',
            comparison: 'empiric symptomatic treatment',
            outcome: 'diagnosis rate and symptom improvement',
            completeness: 100
        },
        expectedKeywords: ['fatigue', 'fibromyalgia', 'chronic fatigue syndrome', 'iron deficiency', 'vitamin D', 'Hashimoto'],
        notes: 'Tests complex reasoning, multiple differential diagnoses, incomplete evidence base'
    }
];

/**
 * Get a demo case by ID
 */
export const getDemoCase = (id: string): DemoCase | undefined => {
    return DEMO_CASES.find(c => c.id === id);
};

/**
 * Get all demo cases for a specific category
 */
export const getDemoCasesByCategory = (category: DemoCase['category']): DemoCase[] => {
    return DEMO_CASES.filter(c => c.category === category);
};
