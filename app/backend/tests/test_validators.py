"""
Tests for MedGemma validators: citation, completeness, and safety.

Run with:
    cd app/backend
    python -m pytest tests/test_validators.py -v
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from validators.citation_validator import CitationValidator, CitationResult
from validators.completeness_checker import CompletenessChecker, CompletenessResult, FieldQuality
from validators.safety_checker import SafetyChecker, SafetyResult


# ============================================================================
# Citation Validator Tests
# ============================================================================

class TestCitationValidator:
    """Tests for CitationValidator."""

    def setup_method(self):
        self.validator = CitationValidator()
        self.sample_refs = [
            {
                "id": "pubmed-12345",
                "title": "Cardiovascular outcomes with GLP-1 receptor agonists in T2DM",
                "source": "New England Journal of Medicine",
                "year": "2023",
                "type": "RCT",
                "pubmedId": "12345",
            },
            {
                "id": "pubmed-67890",
                "title": "Systematic review of SGLT2 inhibitors for weight management",
                "source": "The Lancet",
                "year": "2022",
                "type": "Systematic Review",
                "pubmedId": "67890",
            },
            {
                "id": "pubmed-11111",
                "title": "Real-world effectiveness of semaglutide therapy",
                "source": "JAMA Internal Medicine",
                "year": "2024",
                "type": "Cohort Study",
                "pubmedId": "11111",
            },
        ]

    def test_empty_response_passes(self):
        result = self.validator.validate("", self.sample_refs)
        assert result.passed

    def test_no_citations_no_refs(self):
        result = self.validator.validate("This is just plain text.", [])
        assert result.passed
        assert result.total_citations_found == 0

    def test_no_citations_with_refs_warns(self):
        result = self.validator.validate(
            "Evidence supports this approach for the patient.",
            self.sample_refs
        )
        assert result.passed  # No citations is not an error
        assert result.total_citations_found == 0
        # Should have a warning about missing citations
        assert any(v.severity == "warning" for v in result.violations)

    def test_grounded_numbered_citation(self):
        text = "As shown in study [1], GLP-1 agonists reduce cardiovascular risk."
        result = self.validator.validate(text, self.sample_refs)
        assert result.passed
        assert result.grounded_citations >= 1

    def test_grounded_multiple_numbered_citations(self):
        text = "Studies [1] and [2] demonstrate consistent findings."
        result = self.validator.validate(text, self.sample_refs)
        assert result.passed
        assert result.grounded_citations >= 2

    def test_grounded_range_citation(self):
        text = "Multiple trials [1-3] support this conclusion."
        result = self.validator.validate(text, self.sample_refs)
        assert result.passed
        assert result.grounded_citations >= 3

    def test_ungrounded_numbered_citation(self):
        text = "As shown in [10], this approach is preferred."
        result = self.validator.validate(text, self.sample_refs, strict=True)
        assert not result.passed
        assert result.ungrounded_citations >= 1

    def test_grounded_author_year_citation(self):
        # Year 2023 matches a reference
        text = "Smith et al. (2023) demonstrated cardiovascular benefit."
        result = self.validator.validate(text, self.sample_refs)
        assert result.passed

    def test_ungrounded_author_year_citation(self):
        # Year 1990 doesn't match any reference
        text = "Wilson et al. (1990) conducted a landmark study."
        result = self.validator.validate(text, self.sample_refs, strict=True)
        assert not result.passed

    def test_mixed_citations(self):
        text = (
            "Based on findings from [1] and the meta-analysis [2], "
            "the evidence is strong."
        )
        result = self.validator.validate(text, self.sample_refs)
        assert result.passed
        assert result.grounded_citations >= 2

    def test_coverage_score(self):
        text = "Study [1] shows benefit. Study [2] confirms. Study [3] adds real-world data."
        result = self.validator.validate(text, self.sample_refs)
        assert result.coverage_score > 0

    def test_non_strict_mode(self):
        text = "Wilson (1990) and [1] both suggest benefit."
        result = self.validator.validate(text, self.sample_refs, strict=False)
        # In non-strict mode, one ungrounded out of two should still pass
        assert result.passed


class TestCitationExtraction:
    """Tests for citation pattern extraction."""

    def setup_method(self):
        self.validator = CitationValidator()

    def test_extract_author_et_al_year(self):
        citations = self.validator._extract_citations("Smith et al. (2023)")
        assert len(citations) >= 1
        assert citations[0]["year"] == "2023"

    def test_extract_author_and_author_year(self):
        citations = self.validator._extract_citations("Johnson & Lee (2024)")
        assert len(citations) >= 1
        assert citations[0]["year"] == "2024"

    def test_extract_parenthetical_citation(self):
        citations = self.validator._extract_citations("(Williams, 2023)")
        assert len(citations) >= 1

    def test_extract_numbered_ref(self):
        citations = self.validator._extract_citations("as shown in [3]")
        assert len(citations) >= 1
        assert citations[0]["type"] == "numbered"

    def test_extract_number_range(self):
        citations = self.validator._extract_citations("[1-3]")
        assert len(citations) >= 3  # Should expand to [1], [2], [3]

    def test_no_citations_in_plain_text(self):
        citations = self.validator._extract_citations(
            "This is just a regular clinical discussion with no references."
        )
        assert len(citations) == 0


# ============================================================================
# Completeness Checker Tests
# ============================================================================

class TestCompletenessChecker:
    """Tests for CompletenessChecker."""

    def setup_method(self):
        self.checker = CompletenessChecker()

    # --- PICO Tests ---

    def test_complete_pico_passes(self):
        pico = {
            "patient": "elderly patients with type 2 diabetes and obesity",
            "intervention": "GLP-1 receptor agonists (semaglutide)",
            "comparison": "sulfonylurea or SGLT2 inhibitors",
            "outcome": "weight loss and cardiovascular outcomes",
        }
        result = self.checker.check_pico(pico)
        assert result.passed
        assert result.score >= 0.75

    def test_empty_pico_fails(self):
        pico = {
            "patient": "",
            "intervention": "",
            "comparison": "",
            "outcome": "",
        }
        result = self.checker.check_pico(pico)
        assert not result.passed
        assert result.score == 0.0

    def test_partial_pico(self):
        pico = {
            "patient": "adults with diabetes mellitus",
            "intervention": "semaglutide",
            "comparison": "",
            "outcome": "",
        }
        result = self.checker.check_pico(pico)
        # 2 out of 4 fields filled
        assert result.score > 0.0
        assert result.score < 1.0

    def test_vague_values_treated_as_empty(self):
        pico = {
            "patient": "unknown",
            "intervention": "n/a",
            "comparison": "TBD",
            "outcome": "unclear",
        }
        result = self.checker.check_pico(pico)
        assert result.score == 0.0

    def test_single_word_patient_is_minimal(self):
        pico = {
            "patient": "adults",
            "intervention": "GLP-1 agonists for diabetes",
            "comparison": "placebo",
            "outcome": "glycemic control improvement",
        }
        result = self.checker.check_pico(pico)
        # "adults" is only 1 word, below the 3-word minimum for patient
        field_checks = {fc.field_name: fc for fc in result.field_checks}
        assert field_checks["patient"].quality in (FieldQuality.MINIMAL, FieldQuality.EMPTY)

    def test_pico_completeness_scoring(self):
        pico = {
            "patient": "adults with type 2 diabetes mellitus",
            "intervention": "metformin therapy",
            "comparison": "placebo",
            "outcome": "HbA1c reduction",
        }
        result = self.checker.check_pico(pico)
        assert result.passed
        assert result.score > 0.5

    # --- Workflow Tests ---

    def test_complete_workflow_passes(self):
        state = {
            "pico": {
                "patient": "elderly patients with chronic low back pain",
                "intervention": "physical therapy combined with exercise",
                "comparison": "standard care with NSAIDs",
                "outcome": "pain reduction and functional improvement",
            },
            "references": [
                {"id": "1", "title": "Study A"},
                {"id": "2", "title": "Study B"},
                {"id": "3", "title": "Study C"},
            ],
            "appraisals": [
                {"title": "Design", "verdict": "Positive"},
                {"title": "Bias", "verdict": "Neutral"},
                {"title": "Applicability", "verdict": "Positive"},
            ],
            "applyPoints": [
                {"action": "Start PT", "rationale": "Evidence supports"},
                {"action": "Monitor", "rationale": "Track progress"},
            ],
            "assessPoints": [
                {"metric": "Pain VAS", "target": "<3", "frequency": "Weekly"},
                {"metric": "Function", "target": ">80%", "frequency": "Monthly"},
            ],
        }
        result = self.checker.check_workflow(state)
        assert result.passed
        assert result.score > 0.7

    def test_empty_workflow_fails(self):
        state = {
            "pico": {},
            "references": [],
            "appraisals": [],
            "applyPoints": [],
            "assessPoints": [],
        }
        result = self.checker.check_workflow(state)
        assert not result.passed
        assert result.score == 0.0

    def test_partial_workflow(self):
        state = {
            "pico": {
                "patient": "adults with type 2 diabetes",
                "intervention": "semaglutide",
                "comparison": "standard care",
                "outcome": "weight loss",
            },
            "references": [{"id": "1", "title": "A study"}],
            "appraisals": [],
            "applyPoints": [],
            "assessPoints": [],
        }
        result = self.checker.check_workflow(state)
        # PICO complete + 1 reference, but missing appraisals/actions/outcomes
        assert result.score > 0.0
        assert result.score < 0.8


# ============================================================================
# Safety Checker Tests
# ============================================================================

class TestSafetyChecker:
    """Tests for SafetyChecker."""

    def setup_method(self):
        self.checker = SafetyChecker()

    def test_safe_response_passes(self):
        text = (
            "Based on the evidence, GLP-1 receptor agonists may offer benefit "
            "for weight loss in this patient population. Consider discussing "
            "with the patient the potential cardiovascular benefits as shown "
            "in recent meta-analyses. Clinical judgment should guide the "
            "final treatment decision."
        )
        result = self.checker.check(text)
        assert result.passed
        assert result.has_hedging

    def test_empty_response_passes(self):
        result = self.checker.check("")
        assert result.passed

    def test_prescriptive_language_fails(self):
        text = "You must take this medication immediately to avoid complications."
        result = self.checker.check(text)
        assert not result.passed
        assert any(v.category == "prescriptive" for v in result.violations)

    def test_prescribe_language_fails(self):
        text = "I am prescribing amoxicillin 500mg three times daily."
        result = self.checker.check(text)
        assert not result.passed
        assert any(v.category == "prescriptive" for v in result.violations)

    def test_definitive_diagnosis_fails(self):
        text = "You have pneumonia and need antibiotics right away."
        result = self.checker.check(text)
        assert not result.passed
        assert any(v.category == "definitive_diagnosis" for v in result.violations)

    def test_diagnosis_confirmation_fails(self):
        text = "I can confirm the diagnosis of type 2 diabetes based on these labs."
        result = self.checker.check(text)
        assert not result.passed

    def test_the_diagnosis_is_fails(self):
        text = "The diagnosis is community-acquired pneumonia, stage II."
        result = self.checker.check(text)
        assert not result.passed

    def test_overconfident_certainty_fails(self):
        text = "This is definitely a case of rheumatoid arthritis."
        result = self.checker.check(text)
        assert not result.passed

    def test_hedging_language_detected(self):
        text = "Evidence suggests this treatment could be beneficial."
        result = self.checker.check(text)
        assert result.has_hedging

    def test_disclaimer_detected(self):
        text = "This is for educational purposes only and not a substitute for professional medical advice."
        result = self.checker.check(text)
        assert result.has_disclaimer

    def test_require_hedging_option(self):
        text = "The patient should receive treatment for the condition."
        result = self.checker.check(text, require_hedging=True)
        # This text has no hedging words
        assert any(v.category == "missing_hedging" for v in result.violations)

    def test_require_disclaimer_option(self):
        text = "Evidence supports early intervention in this case."
        result = self.checker.check(text, require_disclaimer=True)
        assert any(v.category == "missing_disclaimer" for v in result.violations)

    def test_dosage_warning(self):
        text = "Consider starting with dose: 500mg twice daily."
        result = self.checker.check(text)
        # Dosage generates a warning, not an error
        assert result.passed  # Warnings don't fail
        assert any(v.category == "scope_overreach" for v in result.violations)
        assert any(v.severity == "warning" for v in result.violations)

    def test_emergency_warning(self):
        text = "If symptoms worsen, call 911 or go to the emergency room."
        result = self.checker.check(text)
        # Emergency language is a warning, not error
        assert result.passed
        assert any(v.category == "scope_overreach" for v in result.violations)

    def test_clinical_recommendation_with_hedging_passes(self):
        text = (
            "Based on the retrieved evidence, consider initiating GLP-1 agonist "
            "therapy. The meta-analysis suggests potential cardiovascular benefit. "
            "Individual patient factors should be discussed, and shared decision "
            "making with the patient is recommended. Clinical judgment should "
            "guide the final approach."
        )
        result = self.checker.check(text)
        assert result.passed
        assert result.has_hedging

    def test_mock_response_passes_safety(self):
        """Test that mock responses from eval_runner pass safety checks."""
        mock_ask = (
            "Based on your case, I've formulated the following PICO question:\n\n"
            "This is a well-defined clinical scenario. The evidence suggests "
            "GLP-1 receptor agonists may offer advantages for this patient profile."
        )
        result = self.checker.check(mock_ask)
        assert result.passed

    def test_mock_apply_passes_safety(self):
        """Test that the APPLY mock response passes safety."""
        mock_apply = (
            "Based on the evidence appraisal, here are clinical recommendations "
            "to discuss with the patient:\n\n"
            "These recommendations should be considered in the context of "
            "individual patient factors and shared decision-making."
        )
        result = self.checker.check(mock_apply)
        assert result.passed


# ============================================================================
# Integration Tests
# ============================================================================

class TestValidatorIntegration:
    """Integration tests combining multiple validators."""

    def setup_method(self):
        self.citation = CitationValidator()
        self.completeness = CompletenessChecker()
        self.safety = SafetyChecker()

    def test_full_good_response(self):
        """A well-crafted AI response should pass all validators."""
        response = (
            "Based on the retrieved evidence [1,2], GLP-1 receptor agonists "
            "may offer significant benefit for this patient. The meta-analysis [1] "
            "suggests cardiovascular risk reduction, while the systematic review [2] "
            "supports weight loss outcomes. Consider discussing these options with "
            "the patient as part of shared decision-making. Clinical judgment should "
            "guide the final treatment plan."
        )
        refs = [
            {"id": "1", "title": "Meta-analysis of GLP-1 outcomes", "year": "2023", "source": "NEJM"},
            {"id": "2", "title": "Systematic review of weight loss", "year": "2022", "source": "Lancet"},
        ]

        citation_result = self.citation.validate(response, refs)
        safety_result = self.safety.check(response)

        assert citation_result.passed, f"Citation failed: {citation_result.summary}"
        assert safety_result.passed, f"Safety failed: {safety_result.summary}"

    def test_full_bad_response(self):
        """A poorly crafted response should fail at least one validator."""
        response = (
            "You have type 2 diabetes. I am prescribing semaglutide. "
            "Jones et al. (1985) proved this is the only treatment. "
            "You must take this medication immediately."
        )
        refs = [
            {"id": "1", "title": "Modern GLP-1 study", "year": "2023", "source": "NEJM"},
        ]

        citation_result = self.citation.validate(response, refs, strict=True)
        safety_result = self.safety.check(response)

        # Should fail safety (prescriptive + definitive diagnosis)
        assert not safety_result.passed
        # Should fail citation (1985 not in refs)
        assert not citation_result.passed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
