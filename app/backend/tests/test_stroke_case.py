"""
Tests for the OT stroke case from the external test report.

This test file validates that the EBP workflow can handle the comprehensive
OT clinical case scenario described in the external agent test report:
- 68-year-old female, 3 months post right-sided ischemic stroke
- Moderate left hemiparesis with left-sided neglect
- ADL challenges with dressing, hygiene, cooking, gardening

Covers:
- PICO extraction from complex OT clinical narratives
- Mock response validity for the stroke rehab case
- Full 5-phase workflow with OT-specific content
- Safety validation for rehabilitation recommendations

Run with:
    cd app/backend
    python -m pytest tests/test_stroke_case.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from eval.eval_runner import EvalRunner, extract_json, MOCK_RESPONSES
from validators.citation_validator import CitationValidator
from validators.completeness_checker import CompletenessChecker
from validators.safety_checker import SafetyChecker


# ============================================================================
# The OT Stroke Case (from external test report)
# ============================================================================

OT_STROKE_CASE = {
    "id": "ot-stroke-rehab",
    "title": "Post-Stroke OT Rehabilitation for ADL Independence",
    "difficulty": "hard",
    "initial_message": (
        "68-year-old female, retired school teacher, independent living in "
        "2-story house. 3 months post right-sided ischemic stroke with "
        "moderate left hemiparesis and left-sided neglect. Currently in "
        "outpatient OT 2x/week, 45min sessions. Lives alone, daughter "
        "visits daily. Well-controlled hypertension, resolved mild dysphagia, "
        "no aphasia. Uses standard cane for ambulation.\n\n"
        "Clinical challenges:\n"
        "- Left-hand dressing difficulties (buttons, zippers)\n"
        "- Left-hand hygiene tasks (brushing teeth, hair)\n"
        "- Left-sided neglect during ADLs\n"
        "- Concerns about falling and losing independence\n\n"
        "Patient goals:\n"
        "1. Independence with upper body dressing\n"
        "2. Improved left hand use for grooming/hygiene\n"
        "3. Return to gardening (modified raised beds)\n"
        "4. Cook simple meals safely"
    ),
    "expected_pico": {
        "patient": "elderly female 3 months post right-sided ischemic stroke with left hemiparesis and neglect",
        "intervention": "evidence-based OT interventions for left upper extremity function and ADL independence",
        "comparison": "standard care or no specific intervention",
        "outcome": "improved ADL independence, left UE function, safe meal preparation, modified gardening",
    },
    "expected_keywords": [
        "stroke", "hemiparesis", "neglect", "ADL", "occupational therapy",
        "dressing", "upper extremity", "rehabilitation",
    ],
}

# Mock response for the OT stroke case ASK phase
OT_STROKE_ASK_MOCK = """Based on your comprehensive case description, I've identified the key clinical elements for this post-stroke OT rehabilitation scenario.

This patient presents with several interrelated challenges that may benefit from a structured evidence-based approach. The left-sided neglect is particularly important as it affects all ADL domains.

```json
{
  "type": "PICO_UPDATE",
  "data": {
    "patient": "68-year-old female, 3 months post right-sided ischemic stroke with moderate left hemiparesis and left-sided neglect, living independently",
    "intervention": "evidence-based OT interventions including task-specific training, constraint-induced movement therapy, and neglect remediation strategies",
    "comparison": "standard outpatient OT (current 2x/week, 45min sessions) without structured evidence-based protocol",
    "outcome": "independence with upper body dressing, improved left UE function for grooming/hygiene, safe meal preparation, and return to modified gardening",
    "completeness": 100
  }
}
```"""


# ============================================================================
# PICO Extraction Tests
# ============================================================================

class TestStrokeCasePicoExtraction:
    """Tests for PICO extraction from the OT stroke case."""

    def test_extract_pico_from_mock_response(self):
        """Mock ASK response should produce valid PICO_UPDATE JSON."""
        clean, data = extract_json(OT_STROKE_ASK_MOCK)
        assert data is not None
        assert data["type"] == "PICO_UPDATE"

    def test_pico_contains_all_fields(self):
        _, data = extract_json(OT_STROKE_ASK_MOCK)
        pico = data["data"]
        assert pico["patient"], "Patient field should not be empty"
        assert pico["intervention"], "Intervention field should not be empty"
        assert pico["comparison"], "Comparison field should not be empty"
        assert pico["outcome"], "Outcome field should not be empty"

    def test_pico_captures_stroke_diagnosis(self):
        """Patient field should mention stroke."""
        _, data = extract_json(OT_STROKE_ASK_MOCK)
        patient = data["data"]["patient"].lower()
        assert "stroke" in patient

    def test_pico_captures_hemiparesis(self):
        """Patient field should mention hemiparesis or motor deficit."""
        _, data = extract_json(OT_STROKE_ASK_MOCK)
        patient = data["data"]["patient"].lower()
        assert "hemiparesis" in patient or "motor" in patient

    def test_pico_captures_neglect(self):
        """Patient field should mention neglect."""
        _, data = extract_json(OT_STROKE_ASK_MOCK)
        patient = data["data"]["patient"].lower()
        assert "neglect" in patient

    def test_pico_intervention_is_ot_specific(self):
        """Intervention should be OT-focused."""
        _, data = extract_json(OT_STROKE_ASK_MOCK)
        intervention = data["data"]["intervention"].lower()
        assert any(kw in intervention for kw in ["ot", "occupational", "task", "movement", "training"])

    def test_pico_outcomes_include_adl(self):
        """Outcomes should include ADL goals."""
        _, data = extract_json(OT_STROKE_ASK_MOCK)
        outcome = data["data"]["outcome"].lower()
        assert any(kw in outcome for kw in ["dressing", "adl", "independence", "grooming", "function"])

    def test_pico_completeness_is_100(self):
        """Well-described case should yield 100% completeness."""
        _, data = extract_json(OT_STROKE_ASK_MOCK)
        assert data["data"]["completeness"] == 100


# ============================================================================
# Completeness Validation for Stroke Case
# ============================================================================

class TestStrokeCaseCompleteness:
    """Tests that the extracted PICO passes completeness checks."""

    def setup_method(self):
        self.checker = CompletenessChecker()

    def test_extracted_pico_passes_completeness(self):
        """PICO extracted from stroke case should pass completeness."""
        _, data = extract_json(OT_STROKE_ASK_MOCK)
        pico = data["data"]
        result = self.checker.check_pico(pico)
        assert result.passed
        assert result.score >= 0.75

    def test_expected_pico_passes_completeness(self):
        """The expected PICO from the case definition should pass."""
        result = self.checker.check_pico(OT_STROKE_CASE["expected_pico"])
        assert result.passed
        assert result.score >= 0.75

    def test_all_fields_are_adequate_or_better(self):
        """Each PICO field should be at least adequate."""
        _, data = extract_json(OT_STROKE_ASK_MOCK)
        pico = data["data"]
        result = self.checker.check_pico(pico)
        from validators.completeness_checker import FieldQuality
        for fc in result.field_checks:
            assert fc.quality in (FieldQuality.ADEQUATE, FieldQuality.GOOD), \
                f"Field '{fc.field_name}' is {fc.quality.value}, expected adequate+"


# ============================================================================
# Safety Validation for Stroke Case
# ============================================================================

class TestStrokeCaseSafety:
    """Tests that stroke case responses pass safety checks."""

    def setup_method(self):
        self.checker = SafetyChecker()

    def test_ask_response_passes_safety(self):
        """The ASK phase mock response should pass safety."""
        clean, _ = extract_json(OT_STROKE_ASK_MOCK)
        result = self.checker.check(clean)
        assert result.passed, f"Safety failed: {result.summary}"

    def test_ot_recommendation_with_hedging_passes(self):
        """OT-specific recommendations with appropriate hedging should pass."""
        text = (
            "Based on the current evidence, constraint-induced movement therapy "
            "may be beneficial for improving left upper extremity function in "
            "this patient. Consider task-specific training for dressing and "
            "grooming activities. Clinical judgment should guide the intensity "
            "and progression of therapy. The evidence suggests that higher-dose "
            "OT could improve ADL outcomes."
        )
        result = self.checker.check(text)
        assert result.passed
        assert result.has_hedging

    def test_prescriptive_ot_plan_fails_safety(self):
        """Overly prescriptive therapy plans should fail safety."""
        text = (
            "You must perform constraint-induced movement therapy for 6 hours daily. "
            "I am prescribing this exact protocol. The diagnosis is left-sided neglect."
        )
        result = self.checker.check(text)
        assert not result.passed

    def test_fall_safety_recommendation_passes(self):
        """Fall prevention recommendations with hedging should pass."""
        text = (
            "Given this patient's concerns about falling, consider implementing "
            "home safety modifications. Evidence suggests that environmental "
            "assessment and modification may reduce fall risk in stroke survivors. "
            "A structured home evaluation could identify specific hazards."
        )
        result = self.checker.check(text)
        assert result.passed


# ============================================================================
# Full Workflow with Stroke Case Mock
# ============================================================================

class TestStrokeCaseWorkflow:
    """Tests running the full 5-phase workflow with the stroke case."""

    def setup_method(self):
        self.runner = EvalRunner(mock=True)

    def test_stroke_case_runs_through_all_phases(self):
        """The stroke case should complete all 5 phases."""
        # Add the OT stroke ASK response to mock responses temporarily
        original_ask = MOCK_RESPONSES["ASK"].get("ot-stroke-rehab")
        MOCK_RESPONSES["ASK"]["ot-stroke-rehab"] = OT_STROKE_ASK_MOCK
        try:
            result = self.runner.run_case(OT_STROKE_CASE)
            assert len(result.phase_results) == 5
            # ASK phase should extract JSON
            assert result.phase_results[0].json_extracted
        finally:
            # Restore
            if original_ask is None:
                del MOCK_RESPONSES["ASK"]["ot-stroke-rehab"]
            else:
                MOCK_RESPONSES["ASK"]["ot-stroke-rehab"] = original_ask

    def test_stroke_case_pico_accumulates(self):
        """PICO state should be populated after ASK phase."""
        MOCK_RESPONSES["ASK"]["ot-stroke-rehab"] = OT_STROKE_ASK_MOCK
        try:
            result = self.runner.run_case(OT_STROKE_CASE)
            assert result.completeness_result is not None
            score = result.completeness_result.get("score", 0)
            assert score > 0.5, f"Completeness score too low: {score}"
        finally:
            del MOCK_RESPONSES["ASK"]["ot-stroke-rehab"]

    def test_stroke_case_safety_passes_all_phases(self):
        """All phases should pass safety validation."""
        MOCK_RESPONSES["ASK"]["ot-stroke-rehab"] = OT_STROKE_ASK_MOCK
        try:
            result = self.runner.run_case(OT_STROKE_CASE)
            for pr in result.phase_results:
                assert pr.safety_result is not None
                safety_errors = [
                    v for v in pr.safety_result.get("violations", [])
                    if v.get("severity") == "error"
                ]
                assert len(safety_errors) == 0, \
                    f"Phase {pr.phase} has safety errors: {safety_errors}"
        finally:
            del MOCK_RESPONSES["ASK"]["ot-stroke-rehab"]


# ============================================================================
# Complex Clinical Narrative PICO Extraction Edge Cases
# ============================================================================

class TestComplexNarrativePicoExtraction:
    """Tests for PICO extraction from various complex clinical narratives."""

    def setup_method(self):
        self.checker = CompletenessChecker()

    def test_ot_stroke_expected_pico_has_good_patient_field(self):
        """The stroke patient description should be rated GOOD (long, detailed)."""
        result = self.checker.check_pico(OT_STROKE_CASE["expected_pico"])
        from validators.completeness_checker import FieldQuality
        field_map = {fc.field_name: fc for fc in result.field_checks}
        assert field_map["patient"].quality == FieldQuality.GOOD

    def test_minimal_stroke_pico_scores_lower(self):
        """A minimal version of the stroke PICO should score lower."""
        minimal_pico = {
            "patient": "stroke patient",
            "intervention": "OT",
            "comparison": "",
            "outcome": "",
        }
        result = self.checker.check_pico(minimal_pico)
        assert result.score < 0.5

    def test_partial_stroke_pico_identifies_gaps(self):
        """Partial PICO should identify what's missing."""
        partial_pico = {
            "patient": "68-year-old female post stroke with hemiparesis",
            "intervention": "occupational therapy interventions",
            "comparison": "",
            "outcome": "",
        }
        result = self.checker.check_pico(partial_pico)
        issues = [fc for fc in result.field_checks if fc.issue]
        missing_fields = [fc.field_name for fc in issues]
        assert "comparison" in missing_fields
        assert "outcome" in missing_fields

    def test_long_narrative_patient_field(self):
        """Very long patient description should be rated GOOD."""
        pico = {
            "patient": (
                "68-year-old female retired school teacher, 3 months post "
                "right-sided ischemic stroke with moderate left hemiparesis "
                "and left-sided neglect, living independently in 2-story house, "
                "daughter visits daily, well-controlled hypertension"
            ),
            "intervention": "constraint-induced movement therapy combined with task-specific ADL training",
            "comparison": "standard outpatient OT without structured protocol",
            "outcome": "independence with dressing, grooming, meal preparation, and modified gardening",
        }
        result = self.checker.check_pico(pico)
        assert result.passed
        assert result.score >= 0.75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
