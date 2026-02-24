# Write-up Guide (≤ 3 pages) — MedGemma Impact Challenge

This guide is tailored to **this repo**: **MedGemma EBP Copilot** (Evidence-Based Practice workflow + optional medical image analysis).

Competition constraints (per Kaggle/local notes): **video ≤ 3 min**, **write-up ≤ 3 pages**, **reproducible code**, and **use at least one HAI‑DEF model**.

---

## Recommended 3-page structure (judge-aligned)

### 1) Title + one-liner (top of page 1)
- **Project name:** MedGemma EBP Copilot
- **One-liner:** A clinician-in-the-loop assistant that turns a clinical question into a structured PICO, retrieves evidence, appraises it, and produces a grounded plan summary with citations.
- **Links:** Video, repo, (optional) live demo.

### 2) Problem domain (15%) — “Why this matters”
Keep this short and concrete.
- Who: clinicians / trainees / evidence teams
- Pain: finding + synthesizing evidence is time-consuming; hard to document reasoning
- What goes wrong today: time loss, inconsistent evidence quality, poor traceability

### 3) Solution overview + user journey (human-centered)
Show the flow in 3–5 steps (include a small diagram or numbered list).
Example flow:
1. Enter patient context + question (or select demo case)
2. Model extracts/repairs **PICO**
3. System retrieves PubMed abstracts and shows **evidence cards**
4. Model drafts grounded synthesis + “what’s missing?” prompts
5. Clinician edits/accepts outputs

### 4) Effective use of HAI‑DEF (20%) — “What MedGemma does here”
Be explicit and specific.
- **Models:** MedGemma 4B multimodal for fast iterations and image+text; MedGemma 27B for deeper reasoning (optional selector).
- **Where used:**
  - PICO extraction + normalization
  - Query generation for retrieval
  - Evidence summarization with retrieved-only citations
  - Optional medical image analysis (X-ray / derm / pathology)
- **Grounding & safety controls (important for judges):**
  - Retrieval-first evidence workflow (PubMed)
  - Citation-only enforcement (see `app/backend/validators/citation_validator.py`)
  - Safety checks against prescriptive language (see `app/backend/validators/safety_checker.py`)

### 5) Product feasibility (20%) — architecture + reproducibility
Include a compact architecture description:
- React/Vite frontend (`app/`) with phase-based workflow UI
- Python FastAPI backend (`app/backend/medgemma_backend.py`) for model inference
- Retrieval via PubMed E-utilities (`app/services/pubmedService.ts`) + caching/rate limiting
- Validators + eval runner (tests + scripted cases)

Add a “Run it yourself” box (copy/paste):
```bash
# Frontend
cd app
npm install
npm run dev

# Backend
cd app/backend
pip install -r requirements.txt
python medgemma_backend.py
```
Mention env vars for cloud vs local backend (see `app/README.md`).

### 6) Impact potential (15%) — measurable + defensible
Judges want a plausible estimate, not marketing.
Include:
- What metric improves (time-to-evidence, transparency, documentation completeness)
- A conservative estimate with assumptions (e.g., “reduces evidence search time from ~20 min → ~5 min for common questions in a demo setting”)
- Where it might fail (limitations)

### 7) Execution & communication (30%) — show polish
Checklist:
- Clear screenshots with captions
- A single “golden path” demo scenario (one case) + a quick highlight of 1–2 extra features
- Avoid medical claims: position as **EBP workflow + documentation support**, not autonomous diagnosis/treatment

### 8) Limitations + safety (brief but explicit)
Borrow directly from `SAFETY.md` and `LIMITATIONS.md`.
- Demo only; human-in-the-loop required
- PubMed abstracts only; no full-text; applicability not guaranteed
- No patient data; use synthetic cases

---

## What to include to maximize score (practical tips)

### Make the “agentic workflow” visible
Even if you don’t target the special prize, judges like clear orchestration.
- Show state transitions: **ASK → ACQUIRE → APPRAISE → APPLY → ASSESS**
- Show model actions per phase (what inputs/outputs are structured)

### Show you took evaluation seriously
This repo already has evaluator scaffolding:
- Mention **77 tests** (if still true at submission time)
- Include 1 screenshot of an eval report or validator catching a bad citation

### Make reproducibility trivial
- “One command per component” run steps
- Include exact model IDs/paths for Kaggle (`/kaggle/input/...`) if you plan to run there

---

## 3-minute video outline (suggested)
1. (0:00–0:15) Problem + what the demo does
2. (0:15–1:45) Live demo: pick a case → PICO → retrieve → summarize with citations
3. (1:45–2:30) Show safety/grounding: cite-only + validator + limitations
4. (2:30–3:00) Impact + feasibility + what’s next

---

## Optional: Special award positioning (pick one)
- **Agentic Workflow Prize:** emphasize phase orchestration + structured intermediate artifacts + validators
- **Edge of AI Prize:** show 4B model running locally / on modest hardware and explain latency wins
- **Novel Task Prize:** emphasize multimodal EBP (image + question + evidence synthesis) or structured clinical reasoning artifacts
