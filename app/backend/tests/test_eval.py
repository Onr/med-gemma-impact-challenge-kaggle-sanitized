"""
Tests for the evaluation runner.

Run with:
    cd app/backend
    python -m pytest tests/test_eval.py -v
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from eval.eval_runner import (
    EvalRunner,
    extract_json,
    DEMO_CASES,
    MOCK_RESPONSES,
    EvalReport,
    CaseResult,
)


# ============================================================================
# JSON Extraction Tests
# ============================================================================

class TestJsonExtraction:
    """Tests for the extract_json function."""

    def test_extract_pico_json(self):
        text = '''Here is the PICO:

```json
{
  "type": "PICO_UPDATE",
  "data": {
    "patient": "adults with diabetes",
    "intervention": "semaglutide",
    "comparison": "placebo",
    "outcome": "weight loss",
    "completeness": 100
  }
}
```

That looks complete.'''
        clean, data = extract_json(text)
        assert data is not None
        assert data["type"] == "PICO_UPDATE"
        assert data["data"]["patient"] == "adults with diabetes"
        assert "```" not in clean

    def test_extract_reference_json(self):
        text = '''Found references:

```json
{
  "type": "REFERENCE_UPDATE",
  "data": [
    {"id": "1", "title": "Study A", "source": "NEJM", "year": "2023", "type": "RCT", "relevance": "High"}
  ]
}
```'''
        clean, data = extract_json(text)
        assert data is not None
        assert data["type"] == "REFERENCE_UPDATE"
        assert len(data["data"]) == 1

    def test_no_json_returns_none(self):
        text = "This is just plain text with no JSON blocks."
        clean, data = extract_json(text)
        assert data is None
        assert clean == text

    def test_invalid_json_returns_none(self):
        text = '''```json
{invalid json here}
```'''
        clean, data = extract_json(text)
        assert data is None

    def test_json_without_language_tag(self):
        text = '''```
{
  "type": "PHASE_CHANGE",
  "data": "ACQUIRE"
}
```'''
        clean, data = extract_json(text)
        assert data is not None
        assert data["type"] == "PHASE_CHANGE"


# ============================================================================
# Mock Response Tests
# ============================================================================

class TestMockResponses:
    """Verify that mock responses are well-formed."""

    def test_all_phases_have_mock_responses(self):
        """Every phase should have at least a default mock response."""
        for phase in ["ASK", "ACQUIRE", "APPRAISE", "APPLY", "ASSESS"]:
            assert phase in MOCK_RESPONSES, f"Missing mock response for {phase}"

    def test_ask_phase_has_case_specific_responses(self):
        """ASK phase should have responses for each demo case."""
        ask_responses = MOCK_RESPONSES["ASK"]
        for case in DEMO_CASES:
            assert case["id"] in ask_responses, \
                f"Missing ASK mock response for case {case['id']}"

    def test_mock_responses_contain_json(self):
        """Mock responses should contain extractable JSON blocks."""
        for phase, responses in MOCK_RESPONSES.items():
            for key, text in responses.items():
                _, data = extract_json(text)
                assert data is not None, \
                    f"Mock response for {phase}/{key} has no extractable JSON"

    def test_ask_responses_produce_pico_update(self):
        """ASK phase mock responses should produce PICO_UPDATE JSON."""
        for case_id, text in MOCK_RESPONSES["ASK"].items():
            _, data = extract_json(text)
            assert data is not None
            assert data.get("type") == "PICO_UPDATE", \
                f"ASK response for {case_id} doesn't produce PICO_UPDATE"
            pico = data.get("data", {})
            assert pico.get("patient"), f"Missing patient in {case_id}"
            assert pico.get("intervention"), f"Missing intervention in {case_id}"

    def test_acquire_response_produces_references(self):
        _, data = extract_json(MOCK_RESPONSES["ACQUIRE"]["default"])
        assert data["type"] == "REFERENCE_UPDATE"
        assert len(data["data"]) >= 1

    def test_appraise_response_produces_appraisals(self):
        _, data = extract_json(MOCK_RESPONSES["APPRAISE"]["default"])
        assert data["type"] == "APPRAISAL_UPDATE"
        assert len(data["data"]) >= 1

    def test_apply_response_produces_actions(self):
        _, data = extract_json(MOCK_RESPONSES["APPLY"]["default"])
        assert data["type"] == "APPLY_UPDATE"
        assert len(data["data"]) >= 1

    def test_assess_response_produces_outcomes(self):
        _, data = extract_json(MOCK_RESPONSES["ASSESS"]["default"])
        assert data["type"] == "ASSESS_UPDATE"
        assert len(data["data"]) >= 1


# ============================================================================
# Demo Case Definitions Tests
# ============================================================================

class TestDemoCases:
    """Verify demo case definitions are complete."""

    def test_all_cases_have_required_fields(self):
        required = ["id", "title", "initial_message", "expected_pico", "expected_keywords"]
        for case in DEMO_CASES:
            for field in required:
                assert field in case, f"Case {case.get('id', '?')} missing '{field}'"

    def test_expected_pico_has_all_fields(self):
        pico_fields = ["patient", "intervention", "comparison", "outcome"]
        for case in DEMO_CASES:
            for field in pico_fields:
                assert field in case["expected_pico"], \
                    f"Case {case['id']} expected_pico missing '{field}'"
                assert case["expected_pico"][field], \
                    f"Case {case['id']} expected_pico.{field} is empty"

    def test_case_ids_are_unique(self):
        ids = [c["id"] for c in DEMO_CASES]
        assert len(ids) == len(set(ids)), "Duplicate case IDs"

    def test_minimum_case_count(self):
        assert len(DEMO_CASES) >= 3, "Need at least 3 demo cases"


# ============================================================================
# Eval Runner Tests (Mock Mode)
# ============================================================================

class TestEvalRunner:
    """Tests for the EvalRunner in mock mode."""

    def setup_method(self):
        self.runner = EvalRunner(mock=True)

    def test_run_single_case(self):
        case = DEMO_CASES[0]
        result = self.runner.run_case(case)
        assert isinstance(result, CaseResult)
        assert result.case_id == case["id"]
        assert len(result.phase_results) == 5  # All 5 EBP phases

    def test_run_all_cases(self):
        report = self.runner.run_all()
        assert isinstance(report, EvalReport)
        assert report.total_cases == len(DEMO_CASES)
        assert len(report.cases) == len(DEMO_CASES)

    def test_mock_cases_pass(self):
        """All mock cases should pass (mock responses are designed to pass)."""
        report = self.runner.run_all()
        for case in report.cases:
            assert case.passed, \
                f"Case {case.case_id} failed: {[i for pr in case.phase_results for i in pr.issues]}"
        assert report.overall_passed

    def test_phase_results_have_json(self):
        """Each phase should extract JSON from mock responses."""
        case = DEMO_CASES[0]
        result = self.runner.run_case(case)
        for pr in result.phase_results:
            assert pr.json_extracted, \
                f"Phase {pr.phase} didn't extract JSON"

    def test_completeness_populated(self):
        """After running all phases, completeness should be good."""
        case = DEMO_CASES[0]
        result = self.runner.run_case(case)
        assert result.completeness_result is not None
        score = result.completeness_result.get("score", 0)
        assert score > 0.5, f"Completeness score too low: {score}"

    def test_safety_checks_run(self):
        """Each phase result should have safety check data."""
        case = DEMO_CASES[0]
        result = self.runner.run_case(case)
        for pr in result.phase_results:
            assert pr.safety_result is not None, \
                f"Phase {pr.phase} missing safety result"

    def test_duration_tracked(self):
        case = DEMO_CASES[0]
        result = self.runner.run_case(case)
        assert result.duration_seconds >= 0

    def test_report_summary(self):
        report = self.runner.run_all()
        summary = report.summary
        assert "PASS" in summary or "FAIL" in summary
        assert str(report.total_cases) in summary


# ============================================================================
# State Accumulation Tests
# ============================================================================

class TestStateAccumulation:
    """Tests for the _update_state method."""

    def setup_method(self):
        self.runner = EvalRunner(mock=True)

    def test_pico_update(self):
        state = {"pico": {}, "references": [], "appraisals": [], "applyPoints": [], "assessPoints": []}
        self.runner._update_state(state, {
            "type": "PICO_UPDATE",
            "data": {"patient": "adults", "intervention": "therapy"}
        })
        assert state["pico"]["patient"] == "adults"

    def test_reference_update(self):
        state = {"pico": {}, "references": [], "appraisals": [], "applyPoints": [], "assessPoints": []}
        self.runner._update_state(state, {
            "type": "REFERENCE_UPDATE",
            "data": [{"id": "1", "title": "Study A"}]
        })
        assert len(state["references"]) == 1

    def test_appraisal_update(self):
        state = {"pico": {}, "references": [], "appraisals": [], "applyPoints": [], "assessPoints": []}
        self.runner._update_state(state, {
            "type": "APPRAISAL_UPDATE",
            "data": [{"title": "Design", "verdict": "Positive"}]
        })
        assert len(state["appraisals"]) == 1

    def test_apply_update(self):
        state = {"pico": {}, "references": [], "appraisals": [], "applyPoints": [], "assessPoints": []}
        self.runner._update_state(state, {
            "type": "APPLY_UPDATE",
            "data": [{"action": "Start PT", "rationale": "Evidence supports"}]
        })
        assert len(state["applyPoints"]) == 1

    def test_assess_update(self):
        state = {"pico": {}, "references": [], "appraisals": [], "applyPoints": [], "assessPoints": []}
        self.runner._update_state(state, {
            "type": "ASSESS_UPDATE",
            "data": [{"metric": "HbA1c", "target": "<7%", "frequency": "3 months"}]
        })
        assert len(state["assessPoints"]) == 1

    def test_unknown_type_ignored(self):
        state = {"pico": {}, "references": [], "appraisals": [], "applyPoints": [], "assessPoints": []}
        self.runner._update_state(state, {
            "type": "UNKNOWN_TYPE",
            "data": {"foo": "bar"}
        })
        # Nothing should change
        assert state["pico"] == {}
        assert len(state["references"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
