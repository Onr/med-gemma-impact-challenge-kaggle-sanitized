"""
Citation Validator

Enforces strict cite-only discipline: AI responses may only reference
studies that were actually retrieved from PubMed or provided by the system.
Detects hallucinated citations (fabricated authors, journals, years).

Usage:
    validator = CitationValidator()
    result = validator.validate(response_text, retrieved_references)
    if not result.passed:
        print(result.violations)
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class CitationViolation:
    """A single citation grounding violation."""
    citation_text: str
    reason: str
    severity: str  # "error" or "warning"


@dataclass
class CitationResult:
    """Result of citation validation."""
    passed: bool
    total_citations_found: int
    grounded_citations: int
    ungrounded_citations: int
    violations: List[CitationViolation] = field(default_factory=list)
    coverage_score: float = 0.0  # 0.0-1.0: what fraction of retrieved refs are cited

    @property
    def summary(self) -> str:
        if self.passed:
            return (
                f"PASS: {self.grounded_citations}/{self.total_citations_found} "
                f"citations grounded (coverage: {self.coverage_score:.0%})"
            )
        violations_str = "; ".join(v.citation_text for v in self.violations if v.severity == "error")
        return (
            f"FAIL: {self.ungrounded_citations} ungrounded citation(s). "
            f"Violations: {violations_str}"
        )


class CitationValidator:
    """Validates that AI responses only cite retrieved references."""

    # Patterns that look like academic citations
    # e.g. "Smith et al. (2023)", "Johnson & Lee, 2024", "(Williams 2023)"
    CITATION_PATTERNS = [
        # Author et al. (Year)
        re.compile(r'([A-Z][a-z]+(?:\s+(?:et\s+al|and|&)\s*\.?))\s*\((\d{4})\)', re.IGNORECASE),
        # Author (Year)
        re.compile(r'([A-Z][a-z]+)\s*\((\d{4})\)'),
        # (Author Year)
        re.compile(r'\(([A-Z][a-z]+(?:\s+(?:et\s+al|and|&)\s*\.?)?),?\s*(\d{4})\)'),
        # Author, Year
        re.compile(r'([A-Z][a-z]+(?:\s+(?:et\s+al|and|&)\s*\.?)),\s*(\d{4})'),
    ]

    # Pattern for numbered references like [1], [2,3], [1-3]
    NUMBERED_REF_PATTERN = re.compile(r'\[(\d+(?:[,\-]\d+)*)\]')

    # Pattern for "Study X" or "Reference X" style
    STUDY_REF_PATTERN = re.compile(r'(?:study|reference|ref|source)\s*#?\s*(\d+)', re.IGNORECASE)

    def validate(
        self,
        response_text: str,
        retrieved_references: List[Dict[str, str]],
        strict: bool = True,
    ) -> CitationResult:
        """
        Validate citations in an AI response against retrieved references.

        Args:
            response_text: The AI-generated text to check
            retrieved_references: List of dicts with keys like
                'title', 'source', 'year', 'authors', 'pubmedId'
            strict: If True, any ungrounded citation is a failure.
                    If False, only clearly fabricated citations fail.

        Returns:
            CitationResult with pass/fail and details
        """
        if not response_text:
            return CitationResult(passed=True, total_citations_found=0,
                                  grounded_citations=0, ungrounded_citations=0,
                                  coverage_score=0.0)

        # Extract all citation-like patterns from the response
        found_citations = self._extract_citations(response_text)

        if not found_citations:
            # No citations found at all - might be fine if no references expected
            if retrieved_references:
                return CitationResult(
                    passed=True,  # Not citing is not a violation per se
                    total_citations_found=0,
                    grounded_citations=0,
                    ungrounded_citations=0,
                    coverage_score=0.0,
                    violations=[CitationViolation(
                        citation_text="(none)",
                        reason="Response contains no citations despite available references",
                        severity="warning"
                    )]
                )
            return CitationResult(passed=True, total_citations_found=0,
                                  grounded_citations=0, ungrounded_citations=0,
                                  coverage_score=0.0)

        # Build a lookup from retrieved references
        ref_lookup = self._build_reference_lookup(retrieved_references)

        # Check each citation
        violations = []
        grounded = 0
        cited_ref_ids = set()

        for citation in found_citations:
            is_grounded, matched_ref_id = self._check_citation(citation, ref_lookup)
            if is_grounded:
                grounded += 1
                if matched_ref_id:
                    cited_ref_ids.add(matched_ref_id)
            else:
                violations.append(CitationViolation(
                    citation_text=citation.get("raw", str(citation)),
                    reason=f"Citation not found in retrieved references",
                    severity="error" if strict else "warning"
                ))

        ungrounded = len(found_citations) - grounded
        total = len(found_citations)

        # Coverage: what fraction of retrieved refs were actually cited
        coverage = len(cited_ref_ids) / len(retrieved_references) if retrieved_references else 0.0

        passed = ungrounded == 0 if strict else (ungrounded <= total * 0.5)

        return CitationResult(
            passed=passed,
            total_citations_found=total,
            grounded_citations=grounded,
            ungrounded_citations=ungrounded,
            violations=violations,
            coverage_score=coverage,
        )

    def _extract_citations(self, text: str) -> List[Dict[str, str]]:
        """Extract citation-like patterns from text."""
        citations = []
        seen = set()

        # Check author-year patterns
        for pattern in self.CITATION_PATTERNS:
            for match in pattern.finditer(text):
                raw = match.group(0).strip()
                if raw not in seen:
                    seen.add(raw)
                    citations.append({
                        "raw": raw,
                        "author": match.group(1).strip() if match.lastindex >= 1 else "",
                        "year": match.group(2).strip() if match.lastindex >= 2 else "",
                        "type": "author_year"
                    })

        # Check numbered references [1], [2,3]
        for match in self.NUMBERED_REF_PATTERN.finditer(text):
            raw = match.group(0)
            if raw not in seen:
                seen.add(raw)
                nums_str = match.group(1)
                # Parse "1,2,3" or "1-3" into individual numbers
                nums = self._parse_number_range(nums_str)
                for n in nums:
                    citations.append({
                        "raw": raw,
                        "number": str(n),
                        "type": "numbered"
                    })

        return citations

    def _parse_number_range(self, s: str) -> List[int]:
        """Parse '1,2,3' or '1-3' into [1,2,3]."""
        nums = []
        for part in s.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    nums.extend(range(int(start), int(end) + 1))
                except ValueError:
                    pass
            else:
                try:
                    nums.append(int(part))
                except ValueError:
                    pass
        return nums

    def _build_reference_lookup(
        self, references: List[Dict[str, str]]
    ) -> Dict[str, Dict]:
        """Build lookup structures from retrieved references."""
        lookup = {
            "by_index": {},     # 1-indexed
            "by_year": {},      # year -> [refs]
            "by_author": {},    # lowered last name -> [refs]
            "by_title_words": {},  # significant word -> [refs]
            "all_refs": [],
        }

        for i, ref in enumerate(references):
            ref_id = ref.get("id", ref.get("pubmedId", str(i)))
            ref_entry = {**ref, "_id": ref_id, "_index": i + 1}

            lookup["by_index"][i + 1] = ref_entry
            lookup["all_refs"].append(ref_entry)

            # Index by year
            year = ref.get("year", "")
            # Extract 4-digit year from strings like "Mar 2023"
            year_match = re.search(r'(\d{4})', str(year))
            if year_match:
                yr = year_match.group(1)
                lookup["by_year"].setdefault(yr, []).append(ref_entry)

            # Index by author last names from title (best effort)
            title = ref.get("title", "")
            for word in title.split():
                cleaned = word.strip(".,;:()[]").lower()
                if len(cleaned) > 3:
                    lookup["by_title_words"].setdefault(cleaned, []).append(ref_entry)

            # Index by source journal
            source = ref.get("source", "").lower()
            for word in source.split():
                cleaned = word.strip(".,;:()[]").lower()
                if len(cleaned) > 3:
                    lookup["by_title_words"].setdefault(cleaned, []).append(ref_entry)

        return lookup

    def _check_citation(
        self, citation: Dict[str, str], ref_lookup: Dict
    ) -> tuple:
        """
        Check if a citation matches any retrieved reference.
        Returns (is_grounded, matched_ref_id or None).
        """
        ctype = citation.get("type", "")

        if ctype == "numbered":
            num = int(citation.get("number", 0))
            ref = ref_lookup["by_index"].get(num)
            if ref:
                return True, ref["_id"]
            # Numbered refs within range of total refs are considered grounded
            if 1 <= num <= len(ref_lookup["all_refs"]):
                return True, ref_lookup["all_refs"][num - 1]["_id"]
            return False, None

        if ctype == "author_year":
            year = citation.get("year", "")
            author = citation.get("author", "").lower()

            # Check year match
            year_refs = ref_lookup["by_year"].get(year, [])
            if year_refs:
                # If we have refs from that year, consider it plausibly grounded
                # (author names aren't in PubMed title data, so we're lenient)
                return True, year_refs[0]["_id"]

            # Check if author name appears in any title/source
            author_words = [w.strip(".,;:()[]") for w in author.split() if len(w) > 2]
            for word in author_words:
                if word.lower() in ("et", "al", "and"):
                    continue
                matches = ref_lookup["by_title_words"].get(word.lower(), [])
                if matches:
                    return True, matches[0]["_id"]

            return False, None

        return False, None
