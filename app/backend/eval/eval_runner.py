"""
Evaluation Runner

Runs demo cases through the MedGemma EBP workflow and validates outputs
using the citation, completeness, and safety validators.

Supports both mock mode (for CI/testing) and real model mode.

Usage:
    # Mock mode (no GPU needed)
    python -m eval.eval_runner --mock

    # Real model
    python -m eval.eval_runner --model google/medgemma-1.5-4b-it

    # Run from the backend directory:
    cd app/backend
    python eval/eval_runner.py --mock
"""

import sys
import json
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from validators.citation_validator import CitationValidator
from validators.completeness_checker import CompletenessChecker
from validators.safety_checker import SafetyChecker


# ============================================================================
# Demo Cases (Python equivalent of app/demo/cases.ts)
# ============================================================================

DEMO_CASES = [
    {
        "id": "diabetes-glp1",
        "title": "GLP-1 Agonists for Weight Loss in T2DM",
        "difficulty": "easy",
        "initial_message": (
            "I have a 68-year-old male patient with type 2 diabetes mellitus "
            "(HbA1c 8.2%), BMI 34, currently on metformin 1000mg BID. He's "
            "interested in losing weight and has heard about 'those new diabetes "
            "shots' for weight loss. He has a history of mild CKD (eGFR 55), "
            "no cardiovascular events but moderate risk. His insurance has approved "
            "semaglutide. I'm wondering if GLP-1 agonists would be beneficial "
            "compared to adding a sulfonylurea or SGLT2 inhibitor."
        ),
        "expected_pico": {
            "patient": "elderly patients with type 2 diabetes and obesity, with mild CKD",
            "intervention": "GLP-1 receptor agonists (semaglutide)",
            "comparison": "sulfonylurea or SGLT2 inhibitors",
            "outcome": "weight loss and cardiovascular outcomes",
        },
        "expected_keywords": ["semaglutide", "GLP-1", "weight loss", "cardiovascular", "diabetes"],
    },
    {
        "id": "chest-xray-pneumonia",
        "title": "Community-Acquired Pneumonia Management",
        "difficulty": "medium",
        "initial_message": (
            "45-year-old female presents to urgent care with 4 days of productive "
            "cough (yellow-green sputum), fever (101.2F), and right-sided pleuritic "
            "chest pain. Vital signs: HR 98, RR 22, SpO2 94% on room air. "
            "Physical exam: Decreased breath sounds and dullness to percussion "
            "right lower lobe, crackles present. I've ordered a chest X-ray which "
            "shows right lower lobe consolidation. CURB-65 score is 1. Should this "
            "patient be treated as outpatient or does she need admission?"
        ),
        "expected_pico": {
            "patient": "adults with community-acquired pneumonia",
            "intervention": "outpatient oral antibiotic therapy",
            "comparison": "inpatient IV antibiotic therapy",
            "outcome": "treatment success and complications",
        },
        "expected_keywords": ["pneumonia", "CURB-65", "antibiotics", "outpatient"],
    },
    {
        "id": "fatigue-differential",
        "title": "Unexplained Chronic Fatigue Workup",
        "difficulty": "hard",
        "initial_message": (
            "32-year-old female presenting with progressive fatigue over 6 months, "
            "not improved with rest. She reports brain fog, muscle aches, and "
            "occasional joint pain without swelling. PMH: Hashimoto's thyroiditis "
            "on levothyroxine 75mcg (TSH 2.1 last month). Labs: Hgb 11.2, "
            "MCV 82, Ferritin 18 ng/mL (low normal), Vitamin D 22 ng/mL "
            "(insufficient), ANA negative, ESR 12, CRP 0.4. She's frustrated "
            "because 'everything looks normal.' How should I approach the workup?"
        ),
        "expected_pico": {
            "patient": "young women with chronic fatigue and Hashimoto thyroiditis",
            "intervention": "systematic diagnostic workup",
            "comparison": "empiric symptomatic treatment",
            "outcome": "diagnosis rate and symptom improvement",
        },
        "expected_keywords": ["fatigue", "fibromyalgia", "iron", "vitamin D", "Hashimoto"],
    },
]


# ============================================================================
# Mock Responses (simulated AI output for testing without GPU)
# ============================================================================

MOCK_RESPONSES = {
    "ASK": {
        "diabetes-glp1": """Based on your case, I've formulated the following PICO question:

This is a well-defined clinical scenario. The evidence suggests GLP-1 receptor agonists may offer advantages for this patient profile.

Let me structure the clinical question:

```json
{
  "type": "PICO_UPDATE",
  "data": {
    "patient": "elderly patients with type 2 diabetes mellitus and obesity (BMI 34), with mild CKD (eGFR 55)",
    "intervention": "GLP-1 receptor agonists (semaglutide)",
    "comparison": "sulfonylurea or SGLT2 inhibitors as add-on to metformin",
    "outcome": "weight loss, cardiovascular outcomes, and glycemic control (HbA1c reduction)",
    "completeness": 100
  }
}
```""",
        "chest-xray-pneumonia": """This is a clear presentation of community-acquired pneumonia. Consider the CURB-65 score for disposition decisions.

The evidence suggests outpatient management may be appropriate with a CURB-65 of 1, though clinical judgment should account for hypoxia.

```json
{
  "type": "PICO_UPDATE",
  "data": {
    "patient": "adults with community-acquired pneumonia (CURB-65 score 1, SpO2 94%)",
    "intervention": "outpatient oral antibiotic therapy",
    "comparison": "inpatient IV antibiotic therapy",
    "outcome": "clinical cure rate, complications, and 30-day mortality",
    "completeness": 100
  }
}
```""",
        "fatigue-differential": """This is a complex presentation with multiple potential contributing factors. The evidence suggests a systematic approach is warranted.

Given the borderline lab values and Hashimoto's history, consider evaluating for subclinical deficiencies.

```json
{
  "type": "PICO_UPDATE",
  "data": {
    "patient": "young women with chronic fatigue, Hashimoto thyroiditis, and borderline iron/vitamin D deficiency",
    "intervention": "systematic diagnostic workup including iron repletion, vitamin D supplementation, and fibromyalgia screening",
    "comparison": "empiric symptomatic treatment or watchful waiting",
    "outcome": "identification of treatable cause and symptom improvement at 3 months",
    "completeness": 100
  }
}
```""",
    },
    "ACQUIRE": {
        "default": """Based on the PICO question, here are relevant studies from the literature:

The evidence base includes several high-quality trials. These studies were retrieved from PubMed and represent the best available evidence.

```json
{
  "type": "REFERENCE_UPDATE",
  "data": [
    {
      "id": "1",
      "title": "Cardiovascular and renal outcomes with GLP-1 receptor agonists",
      "source": "New England Journal of Medicine",
      "year": "2023",
      "type": "Meta-Analysis",
      "relevance": "High"
    },
    {
      "id": "2",
      "title": "Comparative effectiveness of second-line antidiabetic agents",
      "source": "The Lancet",
      "year": "2023",
      "type": "Systematic Review",
      "relevance": "High"
    },
    {
      "id": "3",
      "title": "Real-world outcomes of GLP-1 agonist therapy",
      "source": "JAMA Internal Medicine",
      "year": "2022",
      "type": "Cohort Study",
      "relevance": "Medium"
    }
  ]
}
```""",
    },
    "APPRAISE": {
        "default": """Critical appraisal of the retrieved evidence:

The overall quality of evidence is moderate to high. Consider the following when applying these findings to your patient.

```json
{
  "type": "APPRAISAL_UPDATE",
  "data": [
    {
      "title": "Study Design",
      "description": "Multiple RCTs and a well-conducted meta-analysis provide strong evidence for efficacy.",
      "verdict": "Positive"
    },
    {
      "title": "Population Relevance",
      "description": "Most trials included patients with similar comorbidity profiles. Evidence suggests applicability to this patient.",
      "verdict": "Positive"
    },
    {
      "title": "Follow-up Duration",
      "description": "Longest trial follow-up is 3 years. Long-term (>5 year) data still emerging.",
      "verdict": "Neutral"
    },
    {
      "title": "Funding Source",
      "description": "Primary trials industry-funded, though independent meta-analyses confirm findings.",
      "verdict": "Neutral"
    }
  ]
}
```""",
    },
    "APPLY": {
        "default": """Based on the evidence appraisal, here are clinical recommendations to discuss with the patient:

These recommendations should be considered in the context of individual patient factors and shared decision-making.

```json
{
  "type": "APPLY_UPDATE",
  "data": [
    {
      "action": "Consider initiating GLP-1 receptor agonist therapy",
      "rationale": "Supported by meta-analysis showing benefit for weight loss and cardiovascular risk reduction in T2DM patients."
    },
    {
      "action": "Monitor renal function closely during initiation",
      "rationale": "Patient has mild CKD (eGFR 55); evidence suggests GLP-1 RAs are renal-safe but monitoring is prudent."
    },
    {
      "action": "Discuss expected outcomes and timeline with patient",
      "rationale": "Shared decision-making recommended; clinical judgment should guide therapy choices."
    }
  ]
}
```""",
    },
    "ASSESS": {
        "default": """Outcome assessment framework to monitor treatment response:

Regular monitoring will help determine if treatment goals are being met and inform clinical judgment about continuation.

```json
{
  "type": "ASSESS_UPDATE",
  "data": [
    {
      "metric": "HbA1c",
      "target": "< 7.0% (individualized based on patient factors)",
      "frequency": "Every 3 months"
    },
    {
      "metric": "Body weight",
      "target": "> 5% reduction from baseline",
      "frequency": "Monthly"
    },
    {
      "metric": "eGFR",
      "target": "Stable or improved from baseline 55",
      "frequency": "Every 3 months"
    }
  ]
}
```""",
    },
}


# ============================================================================
# Eval Result Types
# ============================================================================

@dataclass
class PhaseResult:
    """Result for a single EBP phase evaluation."""
    phase: str
    response_text: str
    json_extracted: bool
    json_data: Optional[Dict] = None
    citation_result: Optional[Dict] = None
    safety_result: Optional[Dict] = None
    issues: List[str] = field(default_factory=list)


@dataclass
class CaseResult:
    """Result for a complete demo case evaluation."""
    case_id: str
    case_title: str
    passed: bool
    phase_results: List[PhaseResult] = field(default_factory=list)
    completeness_result: Optional[Dict] = None
    total_issues: int = 0
    duration_seconds: float = 0.0


@dataclass
class EvalReport:
    """Full evaluation report across all demo cases."""
    timestamp: str
    mode: str  # "mock" or "model"
    model_id: Optional[str]
    cases: List[CaseResult] = field(default_factory=list)
    overall_passed: bool = True
    total_cases: int = 0
    passed_cases: int = 0

    @property
    def summary(self) -> str:
        return (
            f"Eval Report ({self.mode}): "
            f"{self.passed_cases}/{self.total_cases} cases passed. "
            f"Overall: {'PASS' if self.overall_passed else 'FAIL'}"
        )


# ============================================================================
# JSON Extraction (mirrors frontend extractJson)
# ============================================================================

import re

def extract_json(text: str) -> tuple:
    """Extract JSON block from AI response text."""
    pattern = re.compile(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', re.IGNORECASE)
    match = pattern.search(text)
    if match:
        try:
            data = json.loads(match.group(1))
            clean_text = pattern.sub('', text).strip()
            return clean_text, data
        except json.JSONDecodeError:
            pass
    return text, None


# ============================================================================
# Eval Runner
# ============================================================================

class EvalRunner:
    """Runs demo cases through the EBP workflow and validates outputs."""

    PHASES = ["ASK", "ACQUIRE", "APPRAISE", "APPLY", "ASSESS"]

    def __init__(self, model=None, mock: bool = True):
        self.model = model
        self.mock = mock
        self.citation_validator = CitationValidator()
        self.completeness_checker = CompletenessChecker()
        self.safety_checker = SafetyChecker()

    def run_all(self) -> EvalReport:
        """Run evaluation on all demo cases."""
        report = EvalReport(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            mode="mock" if self.mock else "model",
            model_id=getattr(self.model, "model_id", None) if self.model else None,
        )

        for case in DEMO_CASES:
            case_result = self.run_case(case)
            report.cases.append(case_result)
            if not case_result.passed:
                report.overall_passed = False

        report.total_cases = len(report.cases)
        report.passed_cases = sum(1 for c in report.cases if c.passed)
        return report

    def run_case(self, case: Dict[str, Any]) -> CaseResult:
        """Run a single demo case through the full EBP workflow."""
        start = time.time()
        case_id = case["id"]
        case_title = case["title"]
        phase_results = []

        # Track accumulated state
        accumulated_state = {
            "pico": {},
            "references": [],
            "appraisals": [],
            "applyPoints": [],
            "assessPoints": [],
        }

        all_issues = []

        for phase in self.PHASES:
            # Get response (mock or real)
            if self.mock:
                response = self._get_mock_response(phase, case_id)
            else:
                response = self._get_model_response(phase, case, accumulated_state)

            # Extract JSON
            clean_text, json_data = extract_json(response)

            # Update accumulated state from extracted JSON
            if json_data:
                self._update_state(accumulated_state, json_data)

            # Validate safety
            safety_result = self.safety_checker.check(clean_text)

            # Validate citations (only in ACQUIRE/APPRAISE/APPLY phases)
            citation_result = None
            if phase in ("ACQUIRE", "APPRAISE", "APPLY") and accumulated_state["references"]:
                ref_dicts = accumulated_state["references"]
                citation_result = self.citation_validator.validate(clean_text, ref_dicts)

            # Collect issues
            issues = []
            if not safety_result.passed:
                for v in safety_result.violations:
                    if v.severity == "error":
                        issues.append(f"[{phase}] Safety: {v.reason}")

            if citation_result and not citation_result.passed:
                for v in citation_result.violations:
                    if v.severity == "error":
                        issues.append(f"[{phase}] Citation: {v.reason}")

            if not json_data and phase != "ASSESS":
                # ASSESS can be the final phase; others should have JSON
                issues.append(f"[{phase}] No structured JSON data extracted")

            all_issues.extend(issues)

            phase_results.append(PhaseResult(
                phase=phase,
                response_text=clean_text[:200] + "..." if len(clean_text) > 200 else clean_text,
                json_extracted=json_data is not None,
                json_data=json_data,
                citation_result=asdict(citation_result) if citation_result else None,
                safety_result=asdict(safety_result),
                issues=issues,
            ))

        # Final completeness check
        completeness_result = self.completeness_checker.check_workflow(accumulated_state)

        # Determine pass/fail
        has_errors = any(
            issue for pr in phase_results for issue in pr.issues
            if "Safety:" in issue  # Safety errors fail the case
        )
        passed = completeness_result.passed and not has_errors

        duration = time.time() - start

        return CaseResult(
            case_id=case_id,
            case_title=case_title,
            passed=passed,
            phase_results=phase_results,
            completeness_result=asdict(completeness_result),
            total_issues=len(all_issues),
            duration_seconds=round(duration, 2),
        )

    def _get_mock_response(self, phase: str, case_id: str) -> str:
        """Get a mock response for testing."""
        phase_responses = MOCK_RESPONSES.get(phase, {})
        # Try case-specific first, then default
        return phase_responses.get(case_id, phase_responses.get("default", "No response available."))

    def _get_model_response(
        self, phase: str, case: Dict, state: Dict
    ) -> str:
        """Get a real model response."""
        if not self.model:
            raise RuntimeError("No model loaded for non-mock evaluation")

        # Build appropriate prompt for each phase
        prompts = {
            "ASK": case["initial_message"],
            "ACQUIRE": "Please find evidence relevant to the PICO question we formulated.",
            "APPRAISE": "Can you critically appraise the quality of these studies?",
            "APPLY": "Based on this evidence, what specific interventions should I recommend?",
            "ASSESS": "What outcomes should I track to measure treatment success?",
        }

        system_prompt = f"""You are MedGemma, an expert EBP Copilot.
Current Phase: {phase}
Patient Context: {case.get('title', '')}

Guide the user through the EBP cycle. Output structured JSON data blocks."""

        return self.model.generate(
            prompt=prompts[phase],
            system_prompt=system_prompt,
            max_new_tokens=512,
        )

    def _update_state(self, state: Dict, json_data: Dict) -> None:
        """Update accumulated state from extracted JSON data."""
        data_type = json_data.get("type", "")
        data = json_data.get("data")
        if not data:
            return

        if data_type == "PICO_UPDATE" and isinstance(data, dict):
            state["pico"].update(data)
        elif data_type == "REFERENCE_UPDATE" and isinstance(data, list):
            state["references"].extend(data)
        elif data_type == "APPRAISAL_UPDATE" and isinstance(data, list):
            state["appraisals"].extend(data)
        elif data_type == "APPLY_UPDATE" and isinstance(data, list):
            state["applyPoints"].extend(data)
        elif data_type == "ASSESS_UPDATE" and isinstance(data, list):
            state["assessPoints"].extend(data)


# ============================================================================
# Report Printer
# ============================================================================

def print_report(report: EvalReport) -> None:
    """Print a human-readable evaluation report."""
    print("\n" + "=" * 70)
    print("  MEDGEMMA EBP COPILOT - EVALUATION REPORT")
    print("=" * 70)
    print(f"  Timestamp: {report.timestamp}")
    print(f"  Mode:      {report.mode}")
    if report.model_id:
        print(f"  Model:     {report.model_id}")
    print(f"  Result:    {'PASS' if report.overall_passed else 'FAIL'}")
    print(f"  Cases:     {report.passed_cases}/{report.total_cases} passed")
    print("=" * 70)

    for case in report.cases:
        status = "PASS" if case.passed else "FAIL"
        print(f"\n{'─' * 60}")
        print(f"  Case: {case.case_title}")
        print(f"  ID:   {case.case_id}")
        print(f"  Result: {status} ({case.duration_seconds}s)")
        print(f"{'─' * 60}")

        for pr in case.phase_results:
            json_icon = "+" if pr.json_extracted else "-"
            issues_str = f" [{len(pr.issues)} issues]" if pr.issues else ""
            print(f"  [{pr.phase:8s}] JSON:{json_icon}{issues_str}")
            for issue in pr.issues:
                print(f"           ! {issue}")

        if case.completeness_result:
            score = case.completeness_result.get("score", 0)
            c_passed = case.completeness_result.get("passed", False)
            c_status = "PASS" if c_passed else "FAIL"
            print(f"  [COMPLETE] {c_status} ({score:.0%})")
            for fc in case.completeness_result.get("field_checks", []):
                quality = fc.get("quality", "unknown")
                name = fc.get("field_name", "?")
                print(f"    {name:12s}: {quality}")

    print("\n" + "=" * 70)
    print(f"  OVERALL: {'PASS' if report.overall_passed else 'FAIL'}")
    print("=" * 70 + "\n")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="MedGemma EBP Evaluation Runner")
    parser.add_argument("--mock", action="store_true", default=True,
                        help="Use mock responses (default)")
    parser.add_argument("--model", type=str, default=None,
                        help="Use real model (overrides --mock)")
    parser.add_argument("--json", action="store_true",
                        help="Output report as JSON")
    parser.add_argument("--case", type=str, default=None,
                        help="Run only a specific case by ID")
    args = parser.parse_args()

    model = None
    use_mock = args.mock

    if args.model:
        use_mock = False
        # Import and load real model
        try:
            from test_medgemma_local import MedGemmaModel
            model = MedGemmaModel(args.model)
        except Exception as e:
            print(f"Failed to load model: {e}")
            print("Falling back to mock mode.")
            use_mock = True

    runner = EvalRunner(model=model, mock=use_mock)

    if args.case:
        # Run single case
        case = next((c for c in DEMO_CASES if c["id"] == args.case), None)
        if not case:
            print(f"Unknown case ID: {args.case}")
            print(f"Available: {[c['id'] for c in DEMO_CASES]}")
            sys.exit(1)
        result = runner.run_case(case)
        if args.json:
            print(json.dumps(asdict(result), indent=2))
        else:
            # Wrap in a minimal report for printing
            report = EvalReport(
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                mode="mock" if use_mock else "model",
                model_id=args.model,
                cases=[result],
                overall_passed=result.passed,
                total_cases=1,
                passed_cases=1 if result.passed else 0,
            )
            print_report(report)
    else:
        # Run all cases
        report = runner.run_all()
        if args.json:
            print(json.dumps(asdict(report), indent=2))
        else:
            print_report(report)

    sys.exit(0 if (runner.run_all() if not args.case else report).overall_passed else 1)


if __name__ == "__main__":
    main()
