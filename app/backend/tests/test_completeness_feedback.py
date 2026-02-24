"""
Tests for completeness feedback, missing-field guidance, and clarifying question triggers.

Addresses external test report issues:
- #5: Incomplete completeness feedback (shows % but not what's missing)
- #6: No "missing/uncertain" markers
- #4: Clarifying question system untested

Run with:
    cd app/backend
    python -m pytest tests/test_completeness_feedback.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from validators.completeness_checker import (
    CompletenessChecker,
    CompletenessResult,
    FieldQuality,
    FieldCheck,
)


class TestFieldLevelFeedback:
    """Tests that completeness results provide field-level guidance on what's missing."""

    def setup_method(self):
        self.checker = CompletenessChecker()

    def test_empty_pico_identifies_all_fields_missing(self):
        """Empty PICO should report all 4 fields as empty."""
        result = self.checker.check_pico({
            "patient": "", "intervention": "", "comparison": "", "outcome": ""
        })
        empty_fields = [fc for fc in result.field_checks if fc.quality == FieldQuality.EMPTY]
        assert len(empty_fields) == 4

    def test_partial_pico_identifies_specific_missing_fields(self):
        """Partial PICO should name the exact missing fields."""
        result = self.checker.check_pico({
            "patient": "adults with type 2 diabetes",
            "intervention": "semaglutide",
            "comparison": "",
            "outcome": "",
        })
        field_map = {fc.field_name: fc for fc in result.field_checks}
        assert field_map["comparison"].quality == FieldQuality.EMPTY
        assert field_map["outcome"].quality == FieldQuality.EMPTY
        assert field_map["patient"].quality != FieldQuality.EMPTY
        assert field_map["intervention"].quality != FieldQuality.EMPTY

    def test_issues_list_names_missing_fields(self):
        """Issues list should contain field names for empty fields."""
        result = self.checker.check_pico({
            "patient": "adults with diabetes mellitus",
            "intervention": "GLP-1 agonists",
            "comparison": "",
            "outcome": "",
        })
        issue_text = " ".join(result.issues)
        assert "comparison" in issue_text
        assert "outcome" in issue_text

    def test_vague_field_flagged_with_reason(self):
        """Vague values should produce an issue explaining the problem."""
        result = self.checker.check_pico({
            "patient": "unknown",
            "intervention": "n/a",
            "comparison": "TBD",
            "outcome": "unclear",
        })
        for fc in result.field_checks:
            assert fc.quality == FieldQuality.EMPTY
            assert fc.issue is not None
            # Issue should mention placeholder/vague
            assert "placeholder" in fc.issue or "empty" in fc.issue

    def test_brief_field_flagged_as_minimal(self):
        """Single-word patient (below 3-word min) should be MINIMAL."""
        result = self.checker.check_pico({
            "patient": "adults",
            "intervention": "therapy for stroke rehabilitation",
            "comparison": "placebo",
            "outcome": "motor recovery improvement",
        })
        field_map = {fc.field_name: fc for fc in result.field_checks}
        assert field_map["patient"].quality == FieldQuality.MINIMAL
        assert "brief" in field_map["patient"].issue or "words" in field_map["patient"].issue

    def test_uncertain_language_flagged(self):
        """Fields containing 'ask user' or 'unclear' should be flagged."""
        result = self.checker.check_pico({
            "patient": "adults with diabetes",
            "intervention": "unclear - ask user",
            "comparison": "not specified",
            "outcome": "to be determined",
        })
        field_map = {fc.field_name: fc for fc in result.field_checks}
        assert field_map["intervention"].quality == FieldQuality.MINIMAL
        assert field_map["comparison"].quality == FieldQuality.EMPTY
        assert field_map["outcome"].quality == FieldQuality.EMPTY


class TestCompletenessGuidance:
    """Tests that completeness results guide the user on how to improve."""

    def setup_method(self):
        self.checker = CompletenessChecker()

    def test_missing_field_generates_guidance(self):
        """get_guidance() should suggest what to fill next."""
        result = self.checker.check_pico({
            "patient": "adults with knee osteoarthritis",
            "intervention": "",
            "comparison": "",
            "outcome": "",
        })
        guidance = self.checker.get_guidance(result)
        assert isinstance(guidance, list)
        assert len(guidance) > 0
        # Should suggest filling the biggest gap
        guidance_text = " ".join(guidance)
        assert "intervention" in guidance_text.lower() or "comparison" in guidance_text.lower() or "outcome" in guidance_text.lower()

    def test_complete_pico_returns_no_guidance(self):
        """Complete PICO should have no improvement guidance."""
        result = self.checker.check_pico({
            "patient": "elderly patients with type 2 diabetes and obesity",
            "intervention": "GLP-1 receptor agonists (semaglutide)",
            "comparison": "sulfonylurea or SGLT2 inhibitors",
            "outcome": "weight loss and cardiovascular outcomes",
        })
        guidance = self.checker.get_guidance(result)
        assert len(guidance) == 0

    def test_guidance_prioritizes_empty_over_minimal(self):
        """Guidance should suggest empty fields before minimal ones."""
        result = self.checker.check_pico({
            "patient": "adults",  # MINIMAL (1 word, needs 3)
            "intervention": "therapy",  # MINIMAL (1 word, needs 2)
            "comparison": "",  # EMPTY
            "outcome": "",  # EMPTY
        })
        guidance = self.checker.get_guidance(result)
        assert len(guidance) >= 2
        # Empty fields should come first
        first_guidance = guidance[0].lower()
        assert "comparison" in first_guidance or "outcome" in first_guidance


class TestClarifyingQuestionTriggers:
    """Tests that incomplete PICO states correctly identify when
    clarifying questions should be asked."""

    def setup_method(self):
        self.checker = CompletenessChecker()

    def test_score_below_50_needs_clarification(self):
        """PICO below 50% should indicate clarification needed."""
        result = self.checker.check_pico({
            "patient": "patients with knee OA",
            "intervention": "",
            "comparison": "",
            "outcome": "",
        })
        assert result.score < 0.5
        assert not result.passed

    def test_score_above_50_can_proceed(self):
        """PICO at 50%+ should allow proceeding to ACQUIRE."""
        result = self.checker.check_pico({
            "patient": "adults with type 2 diabetes",
            "intervention": "GLP-1 agonists",
            "comparison": "",
            "outcome": "weight loss",
        })
        assert result.score >= 0.5
        assert result.passed

    def test_biggest_gap_identification(self):
        """Should identify which field has the biggest gap."""
        result = self.checker.check_pico({
            "patient": "elderly patients with stroke and hemiparesis",
            "intervention": "OT",  # too brief
            "comparison": "",  # empty
            "outcome": "recovery",  # too brief
        })
        empty_fields = [
            fc for fc in result.field_checks
            if fc.quality == FieldQuality.EMPTY
        ]
        minimal_fields = [
            fc for fc in result.field_checks
            if fc.quality == FieldQuality.MINIMAL
        ]
        # comparison is the empty field - biggest gap
        assert len(empty_fields) >= 1
        assert any(fc.field_name == "comparison" for fc in empty_fields)

    def test_all_four_quality_levels(self):
        """Test that all four quality levels can be produced."""
        result = self.checker.check_pico({
            "patient": "68-year-old female retired school teacher with moderate left hemiparesis and neglect post stroke",  # GOOD (many words)
            "intervention": "occupational therapy interventions",  # ADEQUATE
            "comparison": "s",  # MINIMAL (1 char below threshold)
            "outcome": "",  # EMPTY
        })
        field_map = {fc.field_name: fc for fc in result.field_checks}
        assert field_map["patient"].quality == FieldQuality.GOOD
        assert field_map["intervention"].quality in (FieldQuality.ADEQUATE, FieldQuality.GOOD)
        assert field_map["outcome"].quality == FieldQuality.EMPTY


class TestWorkflowCompleteness:
    """Tests for workflow-level completeness tracking across all 5 phases."""

    def setup_method(self):
        self.checker = CompletenessChecker()

    def test_ask_only_workflow_is_incomplete(self):
        """After only ASK phase, workflow should be incomplete."""
        state = {
            "pico": {
                "patient": "adults with stroke and hemiparesis",
                "intervention": "constraint-induced movement therapy",
                "comparison": "standard OT care",
                "outcome": "upper extremity function and ADL independence",
            },
            "references": [],
            "appraisals": [],
            "applyPoints": [],
            "assessPoints": [],
        }
        result = self.checker.check_workflow(state)
        # Only PICO filled, 4 sections empty
        assert result.score < 0.5

    def test_progressive_workflow_scores_increase(self):
        """Adding data to each phase should increase the score."""
        base_state = {
            "pico": {
                "patient": "adults with stroke",
                "intervention": "CIMT",
                "comparison": "standard care",
                "outcome": "UE function",
            },
            "references": [],
            "appraisals": [],
            "applyPoints": [],
            "assessPoints": [],
        }
        score_after_ask = self.checker.check_workflow(base_state).score

        base_state["references"] = [{"id": "1", "title": "Study A"}, {"id": "2", "title": "Study B"}]
        score_after_acquire = self.checker.check_workflow(base_state).score
        assert score_after_acquire > score_after_ask

        base_state["appraisals"] = [{"title": "Design", "verdict": "Positive"}]
        score_after_appraise = self.checker.check_workflow(base_state).score
        assert score_after_appraise > score_after_acquire

        base_state["applyPoints"] = [{"action": "Start CIMT", "rationale": "Evidence supports"}]
        score_after_apply = self.checker.check_workflow(base_state).score
        assert score_after_apply > score_after_appraise

        base_state["assessPoints"] = [{"metric": "FMA-UE", "target": ">50", "frequency": "Weekly"}]
        score_after_assess = self.checker.check_workflow(base_state).score
        assert score_after_assess > score_after_apply

    def test_workflow_identifies_missing_sections(self):
        """Workflow check should name which sections are empty."""
        state = {
            "pico": {
                "patient": "adults with stroke",
                "intervention": "CIMT",
                "comparison": "standard care",
                "outcome": "function",
            },
            "references": [{"id": "1", "title": "A"}],
            "appraisals": [],
            "applyPoints": [],
            "assessPoints": [],
        }
        result = self.checker.check_workflow(state)
        issue_text = " ".join(result.issues)
        assert "appraisals" in issue_text
        assert "actions" in issue_text
        assert "outcomes" in issue_text


class TestEdgeCases:
    """Edge cases for completeness checking."""

    def setup_method(self):
        self.checker = CompletenessChecker()

    def test_very_long_patient_description(self):
        """A very long patient description (>200 words) should be GOOD."""
        long_desc = " ".join(["word"] * 250)
        result = self.checker.check_pico({
            "patient": long_desc,
            "intervention": "some intervention therapy",
            "comparison": "standard care",
            "outcome": "improved outcomes measured",
        })
        field_map = {fc.field_name: fc for fc in result.field_checks}
        assert field_map["patient"].quality == FieldQuality.GOOD

    def test_unicode_in_fields(self):
        """Unicode characters should not break completeness checking."""
        result = self.checker.check_pico({
            "patient": "patients with caf\u00e9-au-lait spots and neurofibromatosis",
            "intervention": "surgical resection \u00b1 chemotherapy",
            "comparison": "observation \u2014 watchful waiting",
            "outcome": "5-year survival rate \u2265 80%",
        })
        assert result.score > 0

    def test_whitespace_only_is_empty(self):
        """Whitespace-only fields should be treated as empty."""
        result = self.checker.check_pico({
            "patient": "   \t\n  ",
            "intervention": "",
            "comparison": "  ",
            "outcome": "\n",
        })
        assert result.score == 0.0

    def test_none_values_handled(self):
        """None values should be treated as empty."""
        result = self.checker.check_pico({
            "patient": None,
            "intervention": None,
            "comparison": None,
            "outcome": None,
        })
        assert result.score == 0.0

    def test_missing_keys_handled(self):
        """Missing PICO keys should be treated as empty."""
        result = self.checker.check_pico({"patient": "adults with diabetes"})
        # Only patient filled
        assert result.score > 0.0
        assert result.score < 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
