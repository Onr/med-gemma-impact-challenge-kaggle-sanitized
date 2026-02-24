# UI/UX Design: Circular SOAP Hub + Right Chat Panel

This UI keeps the patient at the center, but makes SOAP navigation explicit: the **patient hub is a single circle divided into clinical sectors** and surrounded by small “chips” (mini-circles) representing facts, evidence, and actions.

The right side is a dedicated **Chat panel** with **5 chat modes** that correspond to the workflow: **Full Context**, **S/O**, **Assessment**, **Plan**, **Results**.

## Visual Metaphor: “Patient Hub with SOAP Sectors”

### 1) Center: Patient Hub (single circle)
**The Patient Context + Phase Navigation**

- **Visual:** one central circle with an inner label: de-identified patient ID (e.g., “Pt-014”), age band (optional), visit state (Draft / In progress / Ready).
- **Division:** the circle is divided into **3 primary sectors**:
  - **S/O (Subjective + Objective)**
  - **A (Assessment)**
  - **P (Plan)**

Why 3 sectors: S and O are tightly coupled as “inputs,” while A and P represent reasoning and actions.

### 2) Results / Final Outcome
- **Test Results** are now integrated into **S/O** (Objective data) to simplify the main flow.
- A **Final Outcome Circle** is positioned at the bottom-right of the patient hub. Clicking this shows the final resolution, disposition, and quality metrics (not just intermediate labs).

## Mini-circles (“chips”) around each sector
Each sector has a cluster of small circles that are clickable and represent items inside that sector.

### S/O chips (facts)
Multiple small circles for:

- Symptoms, HPI timeline points
- Exam findings
- Vitals/labs values and trends
- Med list / allergies
- Artifact extracts (e.g., lab table screenshot → lab chips)

**Chip states:** Confirmed / Uncertain / Needs follow-up

### Assessment chips (hypotheses + evidence)
Multiple small circles for:

- Problem list items / differential hypotheses
- “Cannot-miss” reminders (as reminders, not directives)
- Evidence items: guideline cards, review papers, key trials (retrieved)

Each Assessment chip can show:
- confidence + last updated time
- “supported by” links to evidence chips (retrieved-only citations)

### Plan chips (actions)
Multiple small circles for:

- Diagnostic steps
- Therapeutic actions
- Monitoring + follow-up items
- Patient education / safety netting

Each Plan chip can show:
- owner (clinician / team)
- status (Draft / Ordered / Done)
- prerequisites missing (e.g., “need renal function”, “contraindications unknown”)

## Right Panel: Chat (5 modes)
The right panel is always visible and is the primary interaction surface.

### Chat mode selector
At the top of the panel, a segmented control:

1) **Full Context Chat** (default)
2) **S/O Chat**
3) **Assessment Chat**
4) **Plan Chat**
5) **Results Chat**

### What each chat does

- **Full Context Chat**
  - Orchestrates the whole case
  - Summarizes, detects contradictions, and proposes what to do next
  - Can “pull in” relevant snippets from other chats when needed

- **S/O Chat**
  - Focused on gathering facts
  - Asks targeted missing-information questions
  - Writes/updates S/O chips directly (with provenance: “from transcript”, “from clinician”, “from artifact”) 

- **Assessment Chat**
  - Runs the evidence-grounded dialogue
  - Triggers retrieval (guidelines/papers) and attaches evidence chips
  - Updates Assessment chips and documents “why this assessment” using retrieved snippets

- **Plan Chat**
  - Converts assessment into a structured plan
  - Negotiates constraints (resources, time, contraindications)
  - Updates Plan chips with rationale and dependencies

- **Results Chat**
  - Captures outcomes (new labs/imaging, response, adverse events, disposition)
  - Asks for commonly missing outcome fields
  - Updates the Results ring + logs outcome-linked chip updates

## Interaction rules (simple + explainable)

### Clicking behavior
- Clicking a **sector** (S/O, A, P) switches chat mode and highlights that sector’s chips.
- Clicking a **chip** opens a focused thread inside the current chat mode (still within that mode, not a separate “tool view”).
- Clicking the **Results ring** switches to Results chat.

### Evidence linking
- Evidence chips can link to Assessment chips (“supports/contradicts”) and to Plan chips (“rationale”).
- The UI never shows citations without a linked retrieved source.

### Iteration / loop-back
If new info arrives:

- Results can prompt a loop back to **Assessment** (new lab changes differential)
- Plan can prompt a loop back to **S/O** (missing contraindication/history)

The hub visually animates the “active loop” (e.g., subtle highlight from Results ring → Assessment sector).

## Layout Sketch (center hub + right chat)

```text
┌───────────────────────────────────────────┬───────────────────────────────┐
│                 PATIENT HUB (Center)      │  CHAT PANEL (Right)           │
│                                           │  [Full] [S/O] [A] [P] [R]     │
│                ┌───────────────┐          │                               │
│               /      S/O        \         │  Chat messages + prompts      │
│              /                   \        │  + quick answer chips         │
│             |    Patient Core     |       │  + “what’s missing?”          │
│              \        A          /        │  + “advance gate” checklist   │
│               \______P_________/          │                               │
│            (Results outer ring)           │                               │
│     chips cluster around each sector      │                               │
└───────────────────────────────────────────┴───────────────────────────────┘
```

## Mobile/Tablet adaptation
- Keep the hub full-screen.
- Chat becomes a swipe-up sheet with the same 5 mode selector.
- Chip clusters become scrollable arcs for each sector.
