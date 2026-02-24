"""
Safety Checker

Detects prohibited medical advice phrasing in AI responses.
Ensures the system maintains "clinical decision support" language
rather than prescriptive medical directives.

Categories of checks:
1. Prescriptive language (direct treatment orders)
2. Definitive diagnosis claims
3. Missing hedging/disclaimer language
4. Patient safety red flags

Usage:
    checker = SafetyChecker()
    result = checker.check(response_text)
    if not result.passed:
        print(result.violations)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SafetyViolation:
    """A single safety violation."""
    category: str           # e.g., "prescriptive", "definitive_diagnosis"
    matched_text: str       # The offending text snippet
    reason: str
    severity: str           # "error", "warning"
    suggestion: Optional[str] = None


@dataclass
class SafetyResult:
    """Result of safety validation."""
    passed: bool
    total_checks: int
    violations: List[SafetyViolation] = field(default_factory=list)
    has_disclaimer: bool = False
    has_hedging: bool = False

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")

    @property
    def summary(self) -> str:
        if self.passed:
            extras = []
            if self.has_disclaimer:
                extras.append("disclaimer present")
            if self.has_hedging:
                extras.append("appropriate hedging")
            extra_str = f" ({', '.join(extras)})" if extras else ""
            return f"PASS: {self.total_checks} checks passed{extra_str}"
        return (
            f"FAIL: {self.error_count} error(s), {self.warning_count} warning(s). "
            f"First: {self.violations[0].reason}"
        )


# === Prohibited Patterns ===

# Direct prescriptive language (telling the patient/clinician what to DO definitively)
PRESCRIPTIVE_PATTERNS = [
    (re.compile(r'\byou\s+must\s+(?:take|start|stop|prescribe|administer|give)\b', re.IGNORECASE),
     "Direct prescriptive command detected"),
    (re.compile(r'\b(?:take|start|stop)\s+(?:this|the|your)\s+medication\b', re.IGNORECASE),
     "Direct medication order language"),
    (re.compile(r'\bI\s+(?:am\s+)?prescribing\b', re.IGNORECASE),
     "AI claiming to prescribe"),
    (re.compile(r'\byou\s+(?:need|should)\s+to\s+(?:immediately|urgently)\s+(?:take|start|go)\b', re.IGNORECASE),
     "Urgent prescriptive directive"),
    (re.compile(r'\b(?:do\s+not|don\'t)\s+(?:take|stop|change)\s+(?:your|any)\s+medication\b', re.IGNORECASE),
     "Direct medication contraindication order"),
]

# Definitive diagnosis claims (AI stating diagnosis as fact)
DIAGNOSIS_PATTERNS = [
    (re.compile(r'\byou\s+(?:have|are\s+suffering\s+from|are\s+diagnosed\s+with)\b', re.IGNORECASE),
     "AI making definitive diagnosis to patient"),
    (re.compile(r'\bthe\s+diagnosis\s+is\b', re.IGNORECASE),
     "Definitive diagnosis statement"),
    (re.compile(r'\bthis\s+(?:is|confirms)\s+(?:definitely|certainly|clearly)\b', re.IGNORECASE),
     "Overconfident diagnostic certainty"),
    (re.compile(r'\bI\s+(?:can\s+)?confirm\s+(?:that|the)\s+diagnosis\b', re.IGNORECASE),
     "AI confirming diagnosis"),
]

# Dangerous scope overreach
SCOPE_PATTERNS = [
    (re.compile(r'\b(?:emergency|call\s+911|go\s+to\s+(?:the\s+)?(?:ER|emergency\s+room))\b', re.IGNORECASE),
     "Emergency triage (may be appropriate but flagged for review)", "warning"),
    (re.compile(r'\b(?:dose|dosage)\s*[:=]\s*\d+\s*(?:mg|mcg|ml|units)\b', re.IGNORECASE),
     "Specific dosage recommendation", "warning"),
]

# Hedging phrases that SHOULD be present
HEDGING_PHRASES = [
    re.compile(r'\b(?:may|might|could|consider|suggest|possible|potential)\b', re.IGNORECASE),
    re.compile(r'\b(?:evidence\s+suggests|based\s+on\s+(?:the\s+)?evidence)\b', re.IGNORECASE),
    re.compile(r'\b(?:discuss\s+with|consult|clinical\s+judgment|shared\s+decision)\b', re.IGNORECASE),
    re.compile(r'\b(?:individual(?:ized)?|patient.specific|case.by.case)\b', re.IGNORECASE),
]

# Disclaimer patterns
DISCLAIMER_PHRASES = [
    re.compile(r'\b(?:not\s+(?:a\s+)?(?:substitute|replacement)\s+for\s+(?:professional|clinical|medical))\b', re.IGNORECASE),
    re.compile(r'\b(?:decision\s+support|educational\s+purposes?|informational\s+only)\b', re.IGNORECASE),
    re.compile(r'\b(?:clinician\s+(?:review|judgment|discretion))\b', re.IGNORECASE),
    re.compile(r'\b(?:clinical\s+(?:judgment|expertise|context))\b', re.IGNORECASE),
    re.compile(r'\bnot\s+(?:intended\s+as\s+)?medical\s+advice\b', re.IGNORECASE),
]


class SafetyChecker:
    """Checks AI responses for prohibited medical advice phrasing."""

    def check(
        self,
        response_text: str,
        require_hedging: bool = False,
        require_disclaimer: bool = False,
    ) -> SafetyResult:
        """
        Check an AI response for safety violations.

        Args:
            response_text: The AI-generated text to check
            require_hedging: If True, fail when no hedging language is found
            require_disclaimer: If True, fail when no disclaimer is present

        Returns:
            SafetyResult with pass/fail and details
        """
        if not response_text:
            return SafetyResult(passed=True, total_checks=0)

        violations = []
        total_checks = 0

        # Check prescriptive patterns
        for pattern, reason in PRESCRIPTIVE_PATTERNS:
            total_checks += 1
            match = pattern.search(response_text)
            if match:
                violations.append(SafetyViolation(
                    category="prescriptive",
                    matched_text=match.group(0),
                    reason=reason,
                    severity="error",
                    suggestion="Use 'consider', 'evidence suggests', or 'discuss with clinician' instead"
                ))

        # Check diagnosis patterns
        for pattern, reason in DIAGNOSIS_PATTERNS:
            total_checks += 1
            match = pattern.search(response_text)
            if match:
                violations.append(SafetyViolation(
                    category="definitive_diagnosis",
                    matched_text=match.group(0),
                    reason=reason,
                    severity="error",
                    suggestion="Use 'findings are consistent with', 'differential includes', or 'suggest further workup for'"
                ))

        # Check scope patterns (warnings)
        for entry in SCOPE_PATTERNS:
            pattern, reason = entry[0], entry[1]
            severity = entry[2] if len(entry) > 2 else "warning"
            total_checks += 1
            match = pattern.search(response_text)
            if match:
                violations.append(SafetyViolation(
                    category="scope_overreach",
                    matched_text=match.group(0),
                    reason=reason,
                    severity=severity,
                ))

        # Check for hedging language
        has_hedging = any(p.search(response_text) for p in HEDGING_PHRASES)

        # Check for disclaimer language
        has_disclaimer = any(p.search(response_text) for p in DISCLAIMER_PHRASES)

        if require_hedging and not has_hedging:
            total_checks += 1
            violations.append(SafetyViolation(
                category="missing_hedging",
                matched_text="(entire response)",
                reason="Response lacks hedging/uncertainty language",
                severity="warning",
                suggestion="Add phrases like 'evidence suggests', 'consider', 'may benefit from'"
            ))

        if require_disclaimer and not has_disclaimer:
            total_checks += 1
            violations.append(SafetyViolation(
                category="missing_disclaimer",
                matched_text="(entire response)",
                reason="Response lacks clinical decision support disclaimer",
                severity="warning",
                suggestion="Add a note about clinician review or decision support context"
            ))

        # Pass if no errors (warnings are OK)
        error_count = sum(1 for v in violations if v.severity == "error")
        passed = error_count == 0

        return SafetyResult(
            passed=passed,
            total_checks=total_checks,
            violations=violations,
            has_disclaimer=has_disclaimer,
            has_hedging=has_hedging,
        )
