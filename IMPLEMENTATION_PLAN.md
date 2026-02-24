# Implementation Plan — Clinician-in-the-loop SOAP Copilot

## Goal
Deliver a competition-ready demo that turns chat/transcription into a guided SOAP workflow with evidence-grounded Assessment, a structured Plan, and clinician confirmation gates.

## Scope (MVP)
- Inputs: typed chat (required), optional transcription text, optional images of tables/forms.
- Outputs: SOAP workspace, missing-info checklist, evidence panel with citations, structured Plan, Results log, de-identified learning card.
- Guardrails: documentation + evidence navigation only; clinician confirmation required for Assessment/Plan.

## Success Criteria
- Completeness: SOAP sections populated with minimal missing info for demo cases.
- Grounding: evidence summaries only from retrieved sources, with citations.
- Usability: clear phase gating and editable outputs.
- Reproducibility: deterministic demo corpus + seedable runs.

## Architecture (high level)
1) Ingest: chat/transcript + optional artifacts
2) State: SOAP workspace + missing-info checklist
3) LLM steps:
   - Extract/structure (S/O)
   - Generate targeted follow-up questions
   - Formulate retrieval queries (Assessment)
   - Summarize evidence with citations
   - Draft Plan with rationale + prerequisites
4) Retrieval: hybrid BM25 + embeddings over curated corpus
5) UI: chat + SOAP panes + evidence drawer

## Phases and Deliverables

### Phase 0 — Scope lock + data policy ✅ DONE
- [x] Decided final demo scope: multi-modal (text + images).
- [x] Corpus source: PubMed E-utilities API (live retrieval).
- [x] Defined synthetic demo cases (`app/demo/cases.ts`) + SOAP/PICO schema (`app/types.ts`).
- [x] Data policy: `SAFETY.md`, `LIMITATIONS.md`.

### Phase 1 — Corpus + indexing ⚠️ PARTIAL
- [x] PubMed E-utilities integration (`app/services/pubmedService.ts`): live search, XML parsing, PICO-to-query conversion.
- [x] Deterministic caching (localStorage, 24-hour TTL).
- [x] Rate limiting (3 req/sec compliance).
- [ ] **NOT DONE: Local corpus manifest** — No static corpus files; relies on live PubMed API.
- [ ] **NOT DONE: Hybrid BM25 + embeddings index** — Would require a curated local corpus and embedding model. PubMed API serves as the retrieval layer instead.
- Deliverables: `app/services/pubmedService.ts` (live retrieval module).

### Phase 2 — Core pipeline ✅ DONE
- [x] SOAP/EBP state machine with phase gating (`app/types.ts`, `app/App.tsx`).
- [x] Prompt templates with phase-specific instructions (`app/constants.ts`).
- [x] JSON extraction for PICO, references, appraisals, actions, outcomes.
- [x] Strict citation validator (`app/backend/validators/citation_validator.py`) — 77 tests passing.
- [x] Backend model inference (`app/backend/medgemma_backend.py`, `model_resolver.py`).
- Deliverables: `app/backend/validators/`, `app/constants.ts`.

### Phase 3 — UI + interaction ✅ DONE
- [x] 3-pane UI: Radial SOAP hub + Info panel + Chat panel.
- [x] Phase controls with visual radial progress (`RadialProgress.tsx`).
- [x] Editable PICO fields in InfoPanel.
- [x] Image upload for multimodal analysis (`ImageUpload.tsx`).
- [x] Model selector with MedGemma 4B/27B/Gemini options (`ModelSelector.tsx`).
- [x] Settings modal with demo case loader (`SettingsModal.tsx`).
- Deliverables: `app/components/`, `app/App.tsx`.

### Phase 4 — Evaluation + safety ✅ DONE
- [x] 3 demo cases with expected PICO and keywords (`app/demo/cases.ts`, `eval/eval_runner.py`).
- [x] Automated eval checks — ALL PASSING (77 tests):
  - [x] **Completeness checker**: PICO field completeness + workflow section population (`validators/completeness_checker.py`)
  - [x] **Citation validator**: Grounded-only citations, hallucination detection (`validators/citation_validator.py`)
  - [x] **Safety checker**: Prohibited prescriptive language, definitive diagnosis, hedging/disclaimer presence (`validators/safety_checker.py`)
- [x] Eval runner with mock + real model modes, JSON report output (`eval/eval_runner.py`).
- [x] `SAFETY.md` and `LIMITATIONS.md` documented.
- Deliverables: `app/backend/validators/`, `app/backend/eval/`, `app/backend/tests/`.

### Phase 5 — Packaging for Kaggle ⚠️ PARTIAL
- [x] Backend setup guide (`app/backend/LOCAL_SETUP.md`).
- [x] Model resolution for Kaggle environment (`model_resolver.py`).
- [x] Example notebook (`gamma-model-examples.ipynb`).
- [x] `app/README.md` documentation.
- [ ] **NOT DONE: End-to-end Kaggle demo notebook** — Need a `demo.ipynb` that runs the full EBP workflow from a single notebook cell, suitable for Kaggle submission.
- [ ] **NOT DONE: Static screenshots or recorded demo** — For submission documentation.

## Key Implementation Details
- Models: MedGemma for extraction/synthesis; optional ASR if transcript input is used.
- Retrieval: BM25 (fast) + embeddings (semantic) with metadata filters (year/type/population).
- Grounding: cite-only enforcement; if no evidence, return “insufficient evidence.”
- Safety: avoid prescriptive treatment; emphasize clinician review.

## Risks + Mitigations
- Hallucinated citations: enforce retrieval-only validator and unit tests.
- Demo latency: precompute embeddings and cache responses.
- Scope creep: lock MVP (text-only if needed) and defer multimodal.

## MVP Checklist
- [x] SOAP schema + state machine — `app/types.ts`, `app/App.tsx`, `app/constants.ts`
- [~] Evidence corpus + hybrid index — PubMed live API works; no local BM25/embeddings (see Remaining Work)
- [x] Prompts + citation validator — `app/constants.ts`, `app/backend/validators/citation_validator.py`
- [x] UI with phase gating — `app/components/RadialProgress.tsx`, full React UI
- [x] Demo cases + eval checks — 3 cases, 77 tests passing, eval runner with reports
- [~] Kaggle-ready notebook — Backend setup done; end-to-end demo notebook still needed

## Remaining Work (Not Yet Implemented)

### 1. Hybrid BM25 + Embeddings Index (Low Priority)
The original plan called for a local corpus with BM25 + embedding retrieval. Currently, the system uses live PubMed E-utilities API instead, which provides real, up-to-date references. A local index would improve:
- Offline operation (no internet needed)
- Deterministic results (same query = same results)
- Speed (no network latency)

**To implement:** Curate ~100-200 key articles as a local JSON corpus, add `rank_bm25` for keyword matching, and optionally embed with a small model (e.g., `all-MiniLM-L6-v2`).

### 2. End-to-End Kaggle Demo Notebook (Medium Priority)
Need a `demo.ipynb` that:
- Installs dependencies
- Loads MedGemma model (from `/kaggle/input/` or HuggingFace)
- Runs the 3 demo cases through the EBP workflow
- Displays formatted PICO, references, appraisals, actions, outcomes
- Runs the eval suite and shows the report

### 3. Static Screenshots / Demo Recording (Low Priority)
For competition submission documentation:
- Screenshots of the UI in each EBP phase
- Example of image analysis (X-ray case)
- Short screen recording of the workflow

## Test Suite Summary

Run all tests:
```bash
cd app/backend
python -m pytest tests/ -v        # 77 tests
python eval/eval_runner.py --mock  # Full eval report
```

| Test File | Tests | Description |
|-----------|-------|-------------|
| `tests/test_validators.py` | 46 | Citation, completeness, safety validators |
| `tests/test_eval.py` | 31 | JSON extraction, mock responses, eval runner, state management |
| `eval/eval_runner.py --mock` | 3 cases | Full workflow evaluation with all validators |
