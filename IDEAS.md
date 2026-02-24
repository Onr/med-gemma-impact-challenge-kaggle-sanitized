# MedGemma Impact Challenge — Project Ideas (Draft)

Purpose: keep a shortlist of **implementable** demo apps aligned to the Kaggle judging criteria:

- Effective use of HAI‑DEF models (20%)
- Problem domain (15%)
- Impact potential (15%)
- Product feasibility (20%)
- Execution & communication (30%)

Below are three candidate directions (starting from your notes), with what to build, how to implement, and how each maps to the judging rubric.

---

## Idea 1 — Offline Combat Medic Intake + Triage Helper (information gathering first)

### One‑liner
An **offline-first field intake assistant** that guides a combat medic through structured questions, captures vitals/symptoms/injury mechanism, and produces a **triage summary + prioritized next actions** (within non-diagnostic guardrails).

### Who it helps
- Combat medics / first responders in low-connectivity environments
- Downstream clinicians receiving a structured handoff

### What the demo does (MVP)
- Step-by-step guided intake (chat UI + forms) tailored to trauma and acute care.
- Converts free-text and checkbox inputs into a structured “handoff note” (e.g., MIST/AMPLE style).
- Generates:
  - **Triage category suggestion** (with uncertainty + rationale tied to observed findings)
  - **Immediate action checklist** (e.g., airway, bleeding control, shock signs)
  - **Evacuation/handoff summary** (concise, standardized)
- Optional: takes a photo (wound/skin) for **description** (not diagnosis) and documentation.

### Implementation sketch
- **Models**
  - MedGemma (text-only or multimodal) for reasoning, summarization, structured extraction.
  - Optional: a small embedding model (or MedGemma embeddings if available) to retrieve guidance snippets.
- **Core workflow**
  1. Intake wizard collects structured data (vitals, injury mechanism, symptoms, meds/allergies).
  2. MedGemma transforms inputs into:
     - structured JSON (handoff fields)
     - plain-language summary
     - “next steps” checklist
  3. Safety layer enforces “decision support only”: must always ask for missing red-flag info; never provide definitive diagnosis; outputs “seek urgent care” triggers when needed.
- **Edge/offline**
  - Package as a local web app (e.g., `FastAPI` + `sqlite` + simple React/HTML) running on a laptop.
  - Keep inference local (best match for “Edge of AI” special award).
- **Evidence / grounding**
  - Use a small, **public** set of trauma guidelines/checklists (open, redistributable) or link-only retrieval with clear citations in the UI.

### Fit to judging criteria
- **HAI‑DEF use (high):** MedGemma drives structured extraction + summarization + guided questioning.
- **Problem domain (high):** acute trauma + handoff quality is a clear unmet need.
- **Impact potential (high):** reduces omission errors; improves handoff speed/quality; works without connectivity.
- **Feasibility (medium-high):** MVP is mostly UX + prompt/guardrails; optional photo handling is extra.
- **Execution (medium):** strong if the demo is polished and shows realistic scenarios + audit logs.

### Risks / guardrails to bake in early
- Avoid “diagnose and treat” framing; position as **documentation + checklist + escalation prompts**.
- Include explicit “not medical advice / not a medical device” disclaimer and “seek urgent help” triggers.
- Use conservative language and uncertainty estimates; show “why I’m asking this question” and “what info is missing”.

### Special award fit
- **The Edge of AI Prize:** strong (offline-first).
- **Agentic Workflow Prize:** moderate (guided workflow + safety checks + structured output can be framed as an agentic loop).

---

## Idea 2 — Medical Transcription → Evidence Navigator (papers + guidelines + “source of truth”)

### One‑liner
Given a medical transcript (or note), generate a **clinical question list**, then retrieve and rank **relevant papers/guidelines**, and produce an evidence-backed brief with citations and “what applies / what doesn’t”.

### Who it helps
- Clinicians, researchers, students during case review / M&M / consult notes
- Documentation teams converting conversations into action items + evidence

### What the demo does (MVP)
- Input: pasted transcript / note (optionally recorded audio).
- Output:
  - Cleaned summary (SOAP-style or problem list)
  - Extracted entities (conditions, meds, labs, procedures)
  - Suggested PICO-style questions (Patient/Problem, Intervention, Comparator, Outcome)
  - Retrieved evidence list (guidelines + recent reviews + key trials)
  - A short evidence brief with **inline citations** + “strength of evidence” hints

### Vision / multimodal extension (Gamma-first)
If you want this idea to stand out and leverage the “gamma” vision stack, make the Evidence Navigator accept **case artifacts as images** (not just text): phone photos of discharge instructions, screenshots of lab trends, EKG printouts, or a representative clinical image (CXR/derm/path) used strictly for *context extraction*.

- **What the vision add-on does (MVP+)**
  - Input: one or more images + a short free-text context (“what is the question?”).
  - Output:
    - “What I can read/see” extraction (e.g., meds/labs from an image, axes/intervals from an EKG strip) with uncertainty
    - A structured problem list + search queries derived from both text and image context
    - Optional “figure/table understanding”: convert a chart/table screenshot into normalized data (CSV/JSON) that can drive retrieval filters (age range, lab thresholds, time course)

- **Models (preferred; Gamma/HAI‑DEF)**
  - **MedGemma multimodal (4B or 27B)** for image+text understanding, grounded extraction, and query planning.
  - **MedSigLIP** (if available separately in the environment) for image embeddings to power:
    - similar-case retrieval (within a small curated demo set)
    - clustering and “find related images” in the UI
  - Specialty encoders (optional, task-specific, if allowed):
    - **CXR Foundation** for chest X-ray retrieval/embedding
    - **Derm Foundation** for dermatology image retrieval/embedding
    - **Path Foundation** for histopathology image retrieval/embedding

- **Guardrails specific to vision**
  - Position vision as **document/feature extraction and context building**, not diagnosis.
  - Make “cannot determine from image” a first-class outcome; show uncertainty.
  - If you include medical images, constrain outputs to: description, quality issues, and what additional info is needed.

- **Optional external provider plug-ins (only if rules allow; not the core path)**
  - Add a provider interface to compare outputs across:
    - Google Gemini (vision)
    - OpenAI (vision)
    - Anthropic (vision)
  - Keep the “official” submission path **fully runnable with MedGemma + HAI‑DEF models** so it’s reproducible and aligned to judging.

### Clinician workflow: structured logging + “hypothesis space” (agentic)
Make the UI explicitly clinician-in-the-loop: clinicians input patient results (labs, imaging findings, symptoms, timelines, outcomes), and the agent’s job is to **summarize and ask the next best questions** so the case can be logged in a structured way for future analysis.

- **Structured capture loop**
  - Clinician pastes/enters results (or uploads artifacts) → agent generates a concise summary + a structured schema (problem list, key measurements, time course, interventions, outcomes).
  - Agent asks targeted follow-ups to reduce ambiguity (“units?”, “baseline value?”, “time since intervention?”, “contraindications?”).
  - A “ready to log” step produces a **de-identified** record (remove names/MRN/dates/locations; age bands; optional hashing) so cases can be stored **anonymously** for later.

- **Hypothesis space (doctor-authored experiments)**
  - Clinicians can write lightweight “experiments” / hypotheses in a workspace:
    - a short description (“If X, then Y…”) and what evidence would support/refute it
    - inclusion/exclusion-style criteria (rule-based + LLM-assisted) and required missing fields
  - Given a new patient record, the agent:
    - proposes which hypotheses/experiments the patient *may* fit (as a **draft pre-screen**)
    - highlights missing fields and asks follow-up questions needed to confirm/deny fit
    - suggests pre-hoc questions (before outcomes) and post-hoc checks (after outcomes) to test whether the hypothesis looks supported

- **Important guardrails (keep it competition-safe)**
  - Frame this as **research support and documentation**, not “enroll this patient” or clinical decision-making.
  - Require explicit clinician review for any “match” and display uncertainty.
  - Add disclaimers about privacy/consent and (in real use) IRB/ethics review; keep the demo dataset synthetic or fully public.

### Implementation sketch
- **Models**
  - MedASR (optional) to convert audio → text.
  - MedGemma to: summarize, extract structured data, generate search queries, draft evidence brief.
  - Retrieval: PubMed / clinical guideline sources (must be public + reproducible).
- **Core workflow**
  1. (Optional) MedASR transcribes audio.
  2. MedGemma produces structured extraction + PICO questions.
  3. Retrieval pipeline (BM25 + embeddings + filters by year/type).
  4. MedGemma writes a brief that **only cites retrieved sources** (RAG discipline).
- **Reproducibility**
  - Provide a “frozen” demo corpus (small set of open-access abstracts/guidelines) so the demo runs deterministically without API keys.
  - Optionally add a “live mode” using public endpoints with clear caching and rate-limit handling.

### Fit to judging criteria
- **HAI‑DEF use (high):** MedASR + MedGemma is a compelling multi-model HAI‑DEF workflow.
- **Problem domain (high):** evidence overload is a known pain; improving evidence access is valuable.
- **Impact potential (medium-high):** depends on how well you scope (e.g., one specialty) and measure time saved.
- **Feasibility (medium):** retrieval quality + citation discipline + UI polish take time; still very doable for a hackathon MVP.
- **Execution (high potential):** judges love clean citations, grounded outputs, and a crisp demo story.

### Risks / guardrails
- Hallucinated citations: enforce “cite only retrieved docs”; show retrieved snippets.
- Medical advice: present as “evidence navigation and drafting,” not prescribing decisions.
- Licensing: ensure any cached corpus is legally redistributable (open access / permissive).

### Special award fit
- **Agentic Workflow Prize:** strong (multi-step: transcribe → extract → plan queries → retrieve → synthesize).
- **Novel Task Prize:** possible if you add a unique twist (e.g., “case-to-guideline mismatch detector”).

---

## Idea 3 — HAI‑DEF Setup & Use Copilot (clinician/practitioner enablement)

### One‑liner
A “clinic-ready starter kit” app that helps a practitioner **set up MedGemma/HAI‑DEF locally**, choose safe workflows (summarization, drafting, extraction), and generates **templated prompts + guardrails + evaluation checklists**.

### Who it helps
- Small clinics / researchers who want local, private workflows
- Developers integrating HAI‑DEF quickly with sensible defaults

### What the demo does (MVP)
- Interactive “wizard” that:
  - Detects hardware (CPU/GPU), suggests model size and runtime settings
  - Provides one-click example workflows:
    - note summarization
    - ICD/CPT suggestion (as “draft, review required”)
    - structured extraction to a JSON schema
  - Generates:
    - prompt templates (with safety language)
    - test set checklist (what to evaluate before use)
    - deployment guidance (local-only, logging, PHI handling)

### Implementation sketch
- **Models**
  - MedGemma used as the interactive tutor + prompt/template generator + extractor.
- **Core workflow**
  1. “Setup assistant” collects environment info and desired workflow.
  2. App generates config + runnable commands + sample inputs/outputs.
  3. встроенные (“built-in”) mini evaluation: a few test cases with rubric-style scoring.
- **Reproducible code**
  - Container + `Makefile`/scripts that run the demo end-to-end.

### Fit to judging criteria
- **HAI‑DEF use (medium):** it uses MedGemma, but the “impact” is more enablement than direct patient-facing value.
- **Problem domain (medium):** developer enablement is real, but “health impact” may feel indirect.
- **Impact potential (medium):** could be compelling if framed as “accelerates safe adoption” + privacy-first local workflows.
- **Feasibility (high):** easiest to ship polished; strong documentation story.
- **Execution (high):** can look very professional with great UX and reproducible setup.

### Special award fit
- **Edge of AI Prize:** strong if everything runs local/offline and targets modest hardware.
- **Agentic Workflow Prize:** moderate (setup agent + eval agent loops).

---

## Quick comparison (rough)

| Idea | Judge score ceiling | Build difficulty | Best special award |
|---|---:|---:|---|
| Offline intake + triage helper | High | Medium | Edge of AI |
| Transcript → evidence navigator | High | Medium | Agentic Workflow / Novel Task |
| Setup & use copilot | Medium-High | Low-Medium | Edge of AI |

---

## Suggested next step (pick 1 to implement first)

If you want **maximum competitiveness**, start with **Idea 2** (clear demo narrative + citations + agentic pipeline) or **Idea 1** (offline-first + strong real-world constraints).

If you want **fastest polished submission**, start with **Idea 3** and make it extremely reproducible, then optionally add a small “evidence navigator” module.

