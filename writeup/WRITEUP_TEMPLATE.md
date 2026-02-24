# MedGemma EBP Copilot — Kaggle Write-up (DRAFT TEMPLATE, ≤3 pages)

## Links
- Video (≤3 min): <ADD LINK>
- Code (this repo): <ADD LINK>
- Live demo (optional): <ADD LINK>

## Team
- <NAME> — <ROLE>
- <NAME> — <ROLE>

## 1) Problem (Domain + unmet need) (15%)
**Context:** <1–2 sentences>

**Why it matters:** <1–2 sentences>

**Current pain:**
- <bullet>
- <bullet>

## 2) Solution (User journey) (15% + communication)
**What the app does:** <1 paragraph>

**Workflow:**
1. ASK: <what user inputs>
2. ACQUIRE: <how evidence is retrieved>
3. APPRAISE: <how evidence is summarized/scored>
4. APPLY: <how outputs become an actionable note/plan>
5. ASSESS: <what outcomes/feedback are captured>

**Human-in-the-loop:** <how the clinician stays in control>

## 3) Effective use of HAI‑DEF (20%)
**Models used (HAI‑DEF):**
- MedGemma <variant> (where used)
- MedGemma <variant> (where used)

**What MedGemma produces (structured artifacts):**
- PICO JSON
- Retrieval queries
- Evidence summaries w/ citations
- Optional image interpretation (demo-only)

**Grounding/safety controls:**
- Retrieval-first evidence panel
- Cite-only enforcement (validator)
- Safety checker + disclaimers

## 4) Product feasibility (20%)
**Architecture:**
- Frontend: React/Vite (`app/`)
- Backend: FastAPI (`app/backend/medgemma_backend.py`)
- Retrieval: PubMed E‑utilities (`app/services/pubmedService.ts`)
- Evaluation: validators + eval runner (`app/backend/validators/`, `app/backend/eval/`)

**Reproducibility (quickstart):**
```bash
cd app
npm install
npm run dev

cd app/backend
pip install -r requirements.txt
python medgemma_backend.py
```

**Performance considerations:** <latency, caching, rate limits>

## 5) Impact potential (15%)
**Claim:** <what improves>

**Estimate (defensible):**
- Baseline: <X>
- With tool: <Y>
- Assumptions: <bullets>

## 6) Evaluation & evidence of quality (supports feasibility + execution)
- Tests: <e.g., 77 tests>
- Demo cases: <list>
- Example failure caught: <citation validator screenshot / description>

## 7) Limitations & safety (explicit)
- Demo-only / research tool
- Abstracts only (PubMed)
- Not medical advice; clinician oversight required

## Appendix (optional, if space)
- Screenshots
- Small architecture diagram
- Prompting/validator details
