"""
Completeness Checker

Validates that PICO elements and SOAP/EBP workflow sections are
adequately populated for a given demo case or real session.

Checks:
- PICO field completeness (each field non-empty and substantive)
- EBP phase data population (references, appraisals, actions, outcomes)
- Minimum quality thresholds per field

Usage:
    checker = CompletenessChecker()
    result = checker.check_pico(pico_data)
    result = checker.check_workflow(workflow_state)
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class FieldQuality(Enum):
    """Quality rating for a single field."""
    EMPTY = "empty"
    MINIMAL = "minimal"       # Has content but very short/vague
    ADEQUATE = "adequate"     # Meets minimum threshold
    GOOD = "good"             # Well-populated


@dataclass
class FieldCheck:
    """Result for a single field check."""
    field_name: str
    quality: FieldQuality
    value: str
    issue: Optional[str] = None


@dataclass
class CompletenessResult:
    """Result of completeness validation."""
    passed: bool
    score: float  # 0.0-1.0
    field_checks: List[FieldCheck] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        issues_str = f" Issues: {'; '.join(self.issues)}" if self.issues else ""
        return f"{status}: completeness {self.score:.0%}.{issues_str}"


# Minimum word counts to consider a field "adequate"
PICO_MIN_WORDS = {
    "patient": 3,       # e.g., "adults with diabetes"
    "intervention": 2,  # e.g., "GLP-1 agonists"
    "comparison": 1,    # e.g., "placebo" (can be short)
    "outcome": 2,       # e.g., "weight loss"
}

# Vague/placeholder values that don't count as real content
VAGUE_VALUES = {
    "unknown", "unclear", "n/a", "na", "none", "tbd", "to be determined",
    "not specified", "not yet", "any", "all", "various", "...", "?",
}


class CompletenessChecker:
    """Validates completeness of PICO and EBP workflow data."""

    def check_pico(
        self,
        pico: Dict[str, Any],
        pass_threshold: float = 0.5,
    ) -> CompletenessResult:
        """
        Check PICO field completeness.

        Args:
            pico: Dict with keys 'patient', 'intervention', 'comparison', 'outcome'
            pass_threshold: Minimum score (0-1) to pass

        Returns:
            CompletenessResult
        """
        checks = []
        issues = []
        total_score = 0.0

        for field_name in ["patient", "intervention", "comparison", "outcome"]:
            value = str(pico.get(field_name, "")).strip()
            quality, issue = self._assess_field(field_name, value)
            checks.append(FieldCheck(
                field_name=field_name,
                quality=quality,
                value=value,
                issue=issue,
            ))

            if quality == FieldQuality.GOOD:
                total_score += 1.0
            elif quality == FieldQuality.ADEQUATE:
                total_score += 0.75
            elif quality == FieldQuality.MINIMAL:
                total_score += 0.25

            if issue:
                issues.append(issue)

        score = total_score / 4.0  # 4 PICO fields
        passed = score >= pass_threshold

        return CompletenessResult(
            passed=passed,
            score=score,
            field_checks=checks,
            issues=issues,
        )

    def check_workflow(
        self,
        state: Dict[str, Any],
        pass_threshold: float = 0.5,
    ) -> CompletenessResult:
        """
        Check overall EBP workflow completeness.

        Args:
            state: Dict with keys:
                'pico': PICO dict
                'references': list of reference dicts
                'appraisals': list of appraisal dicts
                'applyPoints': list of action dicts
                'assessPoints': list of outcome metric dicts

        Returns:
            CompletenessResult
        """
        checks = []
        issues = []
        total_score = 0.0
        n_sections = 5  # PICO + 4 EBP data sections

        # 1. PICO completeness
        pico = state.get("pico", {})
        pico_result = self.check_pico(pico)
        pico_check = FieldCheck(
            field_name="pico",
            quality=FieldQuality.GOOD if pico_result.score >= 0.75 else
                    FieldQuality.ADEQUATE if pico_result.score >= 0.5 else
                    FieldQuality.MINIMAL if pico_result.score > 0 else
                    FieldQuality.EMPTY,
            value=f"score={pico_result.score:.0%}",
            issue=f"PICO incomplete ({pico_result.score:.0%})" if pico_result.score < 0.5 else None
        )
        checks.append(pico_check)
        total_score += pico_result.score
        if pico_check.issue:
            issues.append(pico_check.issue)

        # 2. References (ACQUIRE phase)
        refs = state.get("references", [])
        ref_quality, ref_issue = self._assess_list_section(
            "references", refs, min_count=1, good_count=3
        )
        checks.append(FieldCheck("references", ref_quality, f"{len(refs)} items", ref_issue))
        total_score += self._quality_to_score(ref_quality)
        if ref_issue:
            issues.append(ref_issue)

        # 3. Appraisals (APPRAISE phase)
        appraisals = state.get("appraisals", [])
        apr_quality, apr_issue = self._assess_list_section(
            "appraisals", appraisals, min_count=1, good_count=3
        )
        checks.append(FieldCheck("appraisals", apr_quality, f"{len(appraisals)} items", apr_issue))
        total_score += self._quality_to_score(apr_quality)
        if apr_issue:
            issues.append(apr_issue)

        # 4. Action items (APPLY phase)
        actions = state.get("applyPoints", [])
        act_quality, act_issue = self._assess_list_section(
            "actions", actions, min_count=1, good_count=2
        )
        checks.append(FieldCheck("actions", act_quality, f"{len(actions)} items", act_issue))
        total_score += self._quality_to_score(act_quality)
        if act_issue:
            issues.append(act_issue)

        # 5. Outcome measures (ASSESS phase)
        outcomes = state.get("assessPoints", [])
        out_quality, out_issue = self._assess_list_section(
            "outcomes", outcomes, min_count=1, good_count=2
        )
        checks.append(FieldCheck("outcomes", out_quality, f"{len(outcomes)} items", out_issue))
        total_score += self._quality_to_score(out_quality)
        if out_issue:
            issues.append(out_issue)

        score = total_score / n_sections
        passed = score >= pass_threshold

        return CompletenessResult(
            passed=passed,
            score=score,
            field_checks=checks,
            issues=issues,
        )

    def _assess_field(self, field_name: str, value: str) -> tuple:
        """Assess quality of a single text field."""
        if not value:
            return FieldQuality.EMPTY, f"{field_name}: empty"

        normalized = value.lower().strip()

        # Check for vague/placeholder values
        if normalized in VAGUE_VALUES:
            return FieldQuality.EMPTY, f"{field_name}: contains only placeholder value '{value}'"

        # Check for "ask user" type patterns
        if re.search(r'\b(ask\s+user|unclear|not\s+specified|unknown)\b', normalized, re.IGNORECASE):
            return FieldQuality.MINIMAL, f"{field_name}: contains uncertain language"

        # Check word count
        word_count = len(value.split())
        min_words = PICO_MIN_WORDS.get(field_name, 2)

        if word_count < min_words:
            return FieldQuality.MINIMAL, f"{field_name}: too brief ({word_count} words, need {min_words}+)"

        # Good quality
        if word_count >= min_words * 2:
            return FieldQuality.GOOD, None

        return FieldQuality.ADEQUATE, None

    def _assess_list_section(
        self,
        section_name: str,
        items: list,
        min_count: int = 1,
        good_count: int = 3,
    ) -> tuple:
        """Assess quality of a list section (references, appraisals, etc.)."""
        count = len(items)
        if count == 0:
            return FieldQuality.EMPTY, f"{section_name}: no items"
        if count < min_count:
            return FieldQuality.MINIMAL, f"{section_name}: only {count} item(s), need {min_count}+"
        if count >= good_count:
            return FieldQuality.GOOD, None
        return FieldQuality.ADEQUATE, None

    def get_guidance(self, result: CompletenessResult) -> list:
        """
        Return actionable guidance on what to fill next based on completeness result.

        Prioritizes empty fields over minimal ones. Returns an empty list
        if all fields are adequate or better.

        Args:
            result: A CompletenessResult from check_pico()

        Returns:
            List of guidance strings, ordered by priority (biggest gaps first)
        """
        guidance = []

        # Collect empty fields first (highest priority)
        empty_fields = [
            fc for fc in result.field_checks
            if fc.quality == FieldQuality.EMPTY
        ]
        for fc in empty_fields:
            guidance.append(
                f"Add {fc.field_name}: this field is empty and needs content."
            )

        # Then minimal fields
        minimal_fields = [
            fc for fc in result.field_checks
            if fc.quality == FieldQuality.MINIMAL
        ]
        for fc in minimal_fields:
            min_words = PICO_MIN_WORDS.get(fc.field_name, 2)
            guidance.append(
                f"Expand {fc.field_name}: provide at least {min_words} descriptive words."
            )

        return guidance

    def _quality_to_score(self, quality: FieldQuality) -> float:
        """Convert quality enum to numeric score."""
        return {
            FieldQuality.EMPTY: 0.0,
            FieldQuality.MINIMAL: 0.25,
            FieldQuality.ADEQUATE: 0.75,
            FieldQuality.GOOD: 1.0,
        }[quality]
