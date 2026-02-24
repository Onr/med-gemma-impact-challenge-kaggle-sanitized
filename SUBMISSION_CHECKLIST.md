# MedGemma Impact Challenge — Submission Checklist

This repo is a **demo app** (MedGemma EBP Copilot) intended for the **Kaggle MedGemma Impact Challenge**.

## 0) Hard requirements (must-have)
- [ ] **Use at least one HAI‑DEF model** (e.g., MedGemma 4B / 27B). Make this explicit in the write-up.
- [ ] **Kaggle Writeup submission** (hackathon format; typically 1 final writeup per team).
- [ ] **Video demo ≤ 3 minutes** (link in writeup).
- [ ] **Write-up ≤ 3 pages** (PDF or embedded writeup content per Kaggle writeups UI).
- [ ] **Reproducible code**: public repo + clear steps to reproduce the demo and any results.

## 1) Competition/admin items
- [ ] Confirm **final deadline** on Kaggle (timeline can change).
- [ ] Confirm **team size ≤ 5**.
- [ ] Decide whether to opt into **one** special award (Kaggle may random-pick if multiple are selected):
  - [ ] Agentic Workflow Prize
  - [ ] Edge of AI Prize
  - [ ] Novel Task Prize
- [ ] Check **external data/tools compliance** (must be publicly available / reasonably accessible). For this repo: PubMed E‑utilities is public and rate-limited.
- [ ] Ensure any attached Kaggle Resources are intended to become public after the deadline.

## 2) “Score well” checklist mapped to judging rubric

### A) Effective use of HAI‑DEF models (20%)
- [ ] Name the specific HAI‑DEF models used (e.g., `google/medgemma-1.5-4b-it`, `medgemma-27b-it`, `medgemma-27b-mm-it`).
- [ ] Explain **where** the model is used in the workflow (PICO extraction, evidence synthesis, multimodal image understanding, etc.).
- [ ] Show grounding controls (in this repo: **citation validator**, retrieval-only citations, safety checker).

### B) Problem domain (15%)
- [ ] State the unmet need clearly (e.g., clinicians struggle to translate questions → evidence → decisions under time pressure).
- [ ] Describe the user journey (who uses it, when, what decisions it supports).

### C) Impact potential (15%)
- [ ] Provide a **defensible impact estimate** (time saved per consult, improved note completeness, fewer missed contraindications, etc.).
- [ ] Include the assumptions + limitations of the estimate.

### D) Product feasibility (20%)
- [ ] Include a simple architecture diagram + deployment story (local, Kaggle, or cloud API).
- [ ] Report performance considerations (caching, rate limiting, model size tradeoffs).
- [ ] Include evaluation/validation evidence (tests, scripted demo cases, failure modes).

### E) Execution & communication (30%)
- [ ] Write-up is scannable (1-page executive summary + details; visuals; minimal jargon).
- [ ] Video shows the end-to-end workflow (not a slide deck): user input → model steps → outputs.
- [ ] Repo has **copy/paste** quickstart; no missing env vars; sensible defaults.

## 3) Project-specific completion tasks (this repo)
- [ ] Verify app runs end-to-end:
  - [ ] Frontend: `cd app && npm install && npm run dev`
  - [ ] Backend: `cd app/backend && pip install -r requirements.txt && python medgemma_backend.py`
- [ ] Run backend tests / eval (document outputs in write-up):
  - [ ] `cd app/backend && python -m pytest -q`
  - [ ] `cd app/backend && python eval/eval_runner.py --mock`
- [ ] Capture 3–6 screenshots (UI + evidence panel + citation validation behavior).
- [ ] Record a ≤3 min demo video (see `writeup/WRITEUP_GUIDE.md` for outline).
- [ ] Ensure safety framing is clear (see `SAFETY.md` + `LIMITATIONS.md`).

## 4) Submission assembly (final)
- [ ] Prepare final **Writeup PDF/Content** (≤3 pages).
- [ ] Upload/link the **video**.
- [ ] Link the **public GitHub repo** and (optional) live demo.
- [ ] Final pass: does the write-up explicitly answer each judging category?
