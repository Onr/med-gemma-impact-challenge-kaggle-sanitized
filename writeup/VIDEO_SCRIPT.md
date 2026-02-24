# 3-minute Demo Video Script (Draft)

**Target length:** 2:45–3:00  
**Goal:** show end-to-end user journey + grounding/safety + impact

## 0:00–0:15 — Hook / problem
- “Clinicians often need to turn a question into evidence fast, but the workflow is fragmented and hard to document.”
- “This demo shows MedGemma powering a structured Evidence-Based Practice workflow with traceable citations.”

## 0:15–0:30 — What this is
- “This is MedGemma EBP Copilot: ASK → ACQUIRE → APPRAISE → APPLY → ASSESS.”
- “It’s a demo tool for research/education—not medical advice.”

## 0:30–1:40 — Live golden path demo
1. Select a synthetic demo case (or paste a de-identified question).
2. Show the assistant producing a **PICO** (Population/Intervention/Comparison/Outcome).
3. Show “ACQUIRE”: PubMed retrieval results.
4. Show “APPRAISE/APPLY”: evidence cards + grounded summary with citations.
5. Make one small user edit (e.g., adjust PICO outcome) and show updated retrieval/synthesis.

## 1:40–2:15 — Grounding + safety
- “We enforce retrieval-first behavior: the assistant should only cite what we retrieved.”
- Briefly show the citation validator catching a bad/unretrieved citation (or mention it if time).
- “We also include a safety checker and clear disclaimers.”

## 2:15–2:40 — Feasibility / how it runs
- “Frontend is React/Vite; backend is a small FastAPI server.”
- “It can run with a cloud API key or with local MedGemma weights (including Kaggle-mounted model paths).”

## 2:40–3:00 — Impact + close
- “In a demo setting, this can cut evidence search + documentation time by reducing context switching and making citations traceable.”
- “Next steps: stronger evaluation on more cases, expanded evidence sources, and usability studies.”
