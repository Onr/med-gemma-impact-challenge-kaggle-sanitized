# Selected Idea — Clinician-in-the-loop SOAP Copilot (Chat → Evidence → Results → Learning)

## One-liner
An agentic, clinician-in-the-loop copilot that starts from chat (or transcription + artifacts), **phase-gates** documentation through **S → O → A → P**, runs **retrieval-grounded evidence dialogue** in Assessment, and closes the loop with **Results + de-identified Learning/Logging**—asking targeted questions and looping back whenever new facts or evidence change the plan.

## Who it helps
- Medical clinicians doing real-time documentation and reasoning: primary care, urgent care, hospitalists, specialists
- Trainees during supervised case review (with guardrails)
- Clinical documentation teams (turn conversations into structured notes + citations)

## Core product concept
This is not “a single summary.” It’s a **guided clinical workflow**:

- **Chat-first intake** is the front door.
- The assistant maintains a structured “SOAP workspace” alongside the chat.
- Each phase has a “missing information checklist” and a “ready to advance” gate.
- The **Assessment** phase is where retrieval + evidence-grounded dialogue happens (papers/guidelines are brought into the conversation and cited).
- The process is **cyclical**: clinicians can move forward, jump backward, and repeat until outcomes/results are captured.

## Inputs (multi-modal)
- **Chat** (typed clinician notes, questions, incremental updates)
- **Transcription** (audio → text) for quick capture
- **Artifacts** (optional): images/screenshots of discharge instructions, lab tables, EKG printouts, charts, forms
- **Structured entries** (optional): vitals, labs, meds, diagnoses, problem list

## Workflow (S → O → A → P → Results → Learning)

### 0) Intake / Context
**Goal:** establish the encounter context and what the clinician wants.

- Assistant asks: setting (ED/clinic/inpatient), chief concern, urgency, constraints (time, resources), what output is desired (note, consult, follow-up plan).
- Assistant creates the initial “SOAP workspace” with placeholders.

### 1) S — Subjective (dialogue-driven)
**Goal:** capture symptoms and history in a structured, reviewable format.

- Assistant extracts: chief complaint, HPI timeline, PMH/PSH, meds/allergies, ROS highlights, social history, patient goals.
- If information is missing, it asks targeted questions (e.g., onset/duration, severity, triggers, red flags, baseline function).
- Clinician can answer in chat or via quick form chips (“Yes/No/Unknown”, ranges, timestamps).

### 2) O — Objective (artifact-aware)
**Goal:** capture measurable/observable facts.

- Assistant extracts: vitals, exam findings, labs, imaging summaries, medication list reconciliation.
- From artifacts, the assistant performs **document/feature extraction** (not diagnosis): values, dates, units, trends, table readout, “unable to read” flags.
- Missing-data prompts are explicit (units, reference ranges, time since onset/intervention, baseline comparisons).

### 3) A — Assessment (evidence-grounded dialogue)
**Goal:** arrive at a clinician-reviewed assessment using a transparent evidence workflow.

- Assistant produces a draft:
  - problem list / differential (as hypotheses, with uncertainty)
  - key supporting vs contradicting findings
  - risk flags / “cannot miss” considerations (framed as reminders, not directives)
- The clinician and assistant can go back-and-forth to refine the assessment.

**This is where retrieval happens:**
- The assistant proposes focused clinical questions (PICO-style or guideline questions).
- It retrieves and ranks **guidelines + reviews + key trials** from a reproducible corpus.
- It brings retrieved sources into the chat as a “research panel”:
  - short, grounded summaries
  - applicability notes (“population match”, contraindications, setting constraints)
  - disagreements/limitations (if sources conflict)
  - strict “cite-only-what-was-retrieved” discipline

**Advance gate:** “Assessment ready” requires clinician confirmation (checkbox or explicit message).

### 4) P — Plan (shared, editable)
**Goal:** transform assessment into a concrete, trackable plan.

- Assistant drafts a plan with sections: diagnostics, therapeutics, monitoring, follow-up, patient education, safety netting.
- Every plan item has:
  - rationale (optionally linked to evidence)
  - prerequisites (labs, contraindications, missing data)
  - what success/failure looks like
- Clinician can negotiate changes in chat; the plan updates live.

### 5) Results (what happened + outcomes)
**Goal:** record what was done and what changed.

- Capture: interventions performed, new test results, response, adverse events, disposition.
- Assistant asks for outcome fields that are commonly forgotten: symptom change, functional change, key numbers (e.g., vitals/labs), patient-reported outcomes, follow-up completed.

### 6) Learning / Logging (continuous improvement)
**Goal:** make the next similar case faster, without storing identifiers.

- Generate a de-identified case log:
  - strip names/MRN/addresses; coarse age bands; remove exact dates/locations
  - store structured features (problem list, key findings, plan elements, outcomes)
- Create a “Learning card” (clinician-approved):
  - what information was missing most often
  - what evidence changed the assessment/plan
  - what would be done differently next time

## The iterative loop (key behavior)
At any point, new information can force a loop:

- **Plan → back to S/O:** if the clinician realizes the history/exam is incomplete
- **Results → back to A/P:** if new labs/imaging change the working diagnosis or next steps
- The UI keeps versions so clinicians can see what changed and why.

## What the demo produces (MVP outputs)
- A clinician-reviewed **SOAP note** with a problem list
- A “Missing info” checklist that shows what was asked and what remains unknown
- An **Assessment evidence panel** with citations (retrieved-only)
- A structured Plan with trackable items
- A Results section capturing outcomes
- A de-identified log + learning card

## UI sketch (simple, competition-friendly)
- Left: clinician **chat + transcription** stream
- Center/right: **SOAP workspace** with “Advance to next phase” controls
- Right drawer: **Evidence panel** (retrieved papers/guidelines, snippets, citations)
- Top: “Missing info” badge and “Ready to advance” checklist

## Implementation sketch (HAI-DEF / MedGemma-first)
- **Models**
  - MedASR (optional): audio → text
  - MedGemma multimodal: extraction, summarization, question generation, evidence synthesis, artifact reading
- **Retrieval**
  - Deterministic demo corpus (open-access abstracts/guidelines) + caching
  - Hybrid retrieval (BM25 + embeddings) with filters (year/type/population)
- **Grounding discipline**
  - Evidence responses must be supported by retrieved snippets; citations are mandatory
  - Uncertainty is explicit; “insufficient information” is a first-class outcome

## Guardrails (keep it safe and judge-friendly)
- Position as **documentation + evidence navigation**, not autonomous medical decision-making
- Require clinician confirmation before finalizing Assessment/Plan
- De-identification by default for logs; use only synthetic/public demo data

## Fit to judging criteria
- **Agentic workflow:** strong (phase gating, missing-info questions, evidence retrieval, iterative loop)
- **HAI-DEF alignment:** strong (ASR + MedGemma + retrieval pipeline)
- **Impact potential:** high if the demo shows time saved + improved note completeness + transparent citations
