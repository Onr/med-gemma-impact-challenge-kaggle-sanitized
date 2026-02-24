# Fix and Verification Plan

**Based on**: External Agent Test Report (OT Stroke Rehabilitation Case)
**Date**: 2026-02-06
**Status**: Tests written and passing (137/137)

---

## Issue-to-Fix Mapping

| # | Report Issue | Severity | Fix Applied | Test File | Test Count |
|---|-------------|----------|-------------|-----------|------------|
| 1 | Backend service not running | Critical | Improved error messages with troubleshooting steps | `test_backend_api.py` | 17 |
| 2 | No fallback/graceful degradation | High | `sendViaBackend` now shows backend URL, startup command, and alternative provider suggestion | `test_backend_api.py` | 4 (mock model) |
| 3 | Missing automatic PICO extraction | High | Added OT stroke case mock + extraction tests | `test_stroke_case.py` | 8 |
| 4 | No clarifying question system tested | High | Added trigger condition tests (score thresholds, gap identification) | `test_completeness_feedback.py` | 4 |
| 5 | Incomplete completeness feedback | Medium | Added `get_guidance()` method to CompletenessChecker | `test_completeness_feedback.py` | 3 |
| 6 | No "missing/uncertain" markers | Medium | Tests verify field-level quality + issue reporting | `test_completeness_feedback.py` | 6 |
| 7 | Text truncation in fields | Medium | Edge case tests for long text, unicode, whitespace | `test_completeness_feedback.py` | 5 |

---

## Files Changed

### Code Fixes
1. **`app/services/medGemmaService.ts`** (line ~284-295)
   - `sendViaBackend` catch block now distinguishes network errors from other errors
   - Network errors show: backend URL, startup command, health check curl, provider switch suggestion
   - Other errors include the error message for debugging

2. **`app/backend/validators/completeness_checker.py`** (new method)
   - Added `get_guidance(result)` method that returns prioritized list of what to fill next
   - Empty fields listed before minimal fields
   - Includes suggested word counts per PICO field

### New Test Files
3. **`app/backend/tests/test_backend_api.py`** (17 tests)
   - Health endpoint: status, device info, loaded models
   - Models endpoint: suggested models, local models list
   - Generate endpoint: schema validation, error handling, history, system prompt, images
   - Mock model: response flow, prefix stripping, generation errors
   - CORS: frontend origin acceptance

4. **`app/backend/tests/test_stroke_case.py`** (22 tests)
   - PICO extraction from OT stroke narrative (8 tests)
   - Completeness validation for stroke PICO (3 tests)
   - Safety validation for OT responses (4 tests)
   - Full 5-phase workflow with stroke case (3 tests)
   - Complex narrative edge cases (4 tests)

5. **`app/backend/tests/test_completeness_feedback.py`** (21 tests)
   - Field-level feedback: missing field identification, vague values, brief fields (6 tests)
   - Guidance generation: prioritization, empty vs minimal (3 tests)
   - Clarifying question triggers: thresholds, gap identification (4 tests)
   - Workflow completeness: progressive scoring, missing sections (3 tests)
   - Edge cases: long text, unicode, whitespace, None, missing keys (5 tests)

---

## Verification Steps

### Automated (CI-ready)

```bash
# Run full test suite (137 tests, ~3s, no GPU needed)
cd app/backend
python -m pytest tests/ -v

# Run only new tests
python -m pytest tests/test_backend_api.py tests/test_stroke_case.py tests/test_completeness_feedback.py -v

# Run mock evaluation (3 demo cases through full 5A workflow)
python eval/eval_runner.py --mock
```

### Manual Verification Checklist

#### Issue #1: Backend Connection Error
- [ ] Start frontend without backend (`npm run dev`)
- [ ] Send a message in chat
- [ ] Verify error shows: backend URL, startup command, health check, provider switch suggestion
- [ ] Confirm no generic "error connecting" message

#### Issue #2: Graceful Degradation
- [ ] With backend down, verify app doesn't crash
- [ ] Switch to Google AI provider in settings
- [ ] Confirm AI features work via Google AI path

#### Issue #3: PICO Extraction (OT Stroke Case)
- [ ] Start backend + frontend
- [ ] Paste the OT stroke case narrative into chat
- [ ] Verify PICO fields auto-populate with: stroke, hemiparesis, neglect, OT interventions, ADL outcomes
- [ ] Verify completeness shows 100%

#### Issue #4: Clarifying Questions
- [ ] Enter a vague case: "treatment for knee pain"
- [ ] Verify AI asks a focused follow-up question (e.g., "What is the patient's age and specific diagnosis?")
- [ ] Verify completeness shows < 50%

#### Issue #5: Completeness Feedback
- [ ] Fill only Patient and Intervention in PICO
- [ ] Verify completeness bar shows ~50%
- [ ] Verify `get_guidance()` would report Comparison and Outcome as missing

#### Issue #6: Missing/Uncertain Markers
- [ ] Verify field_checks in completeness result include quality level per field
- [ ] Fields with "unknown", "TBD" are flagged as EMPTY with reason

#### Issue #7: Text Handling
- [ ] Enter a very long (200+ word) patient description
- [ ] Verify it's accepted and rated as GOOD quality
- [ ] Verify unicode characters (cafe-au-lait, +/- signs) don't break checking

---

## Test Coverage Summary

| Test File | Tests | Area |
|-----------|-------|------|
| `test_validators.py` | 45 | Citation, completeness, safety validators |
| `test_eval.py` | 32 | Eval runner, JSON extraction, demo cases |
| `test_backend_api.py` | 17 | FastAPI endpoints, error handling, CORS |
| `test_stroke_case.py` | 22 | OT stroke case, PICO extraction, safety |
| `test_completeness_feedback.py` | 21 | Field guidance, clarifying questions, edge cases |
| **Total** | **137** | |

---

## Remaining Items (Not Addressed)

These items from the external report are UI/UX improvements that don't have backend test coverage:

| Issue | Type | Recommendation |
|-------|------|----------------|
| Phase navigation not obvious | UX | Add scroll-to-PICO animation when entering ASK phase |
| Chat input overlaps | CSS | Add max-height + overflow-y: auto to conversation area |
| No PICO confidence indicators | UI | Add colored badge (green/yellow/red) per PICO field in InfoPanel |
| No tooltip for completeness | UI | Add hover showing "75% - Comparison field optional" |
| No export/share | Feature | Future: Add PDF export for evidence summary |

These are frontend-only changes that should be addressed in a separate UI polish pass.
