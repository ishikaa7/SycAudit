"""Deterministic Python validator for the four prompt variants.

Checks what can be checked reliably without another LLM: presence/duplication
of the four types, byte-identity of ``original``, preservation of numbers,
dates, units and heuristically-extracted named entities, and lexical checks for
the question/hedged/third-person transformations.

Deliberate limits (documented, not hidden):
- Semantic equivalence of propositions is NOT checked - Python cannot do that.
- Named-entity extraction is a heuristic (capitalised words outside quotes).
- Hedge/proposition analysis is lexical and only reliable for English-like
  text; for clearly non-English input those checks are skipped.

Each issue carries a severity. ``valid`` is true when there are no *error*
issues; *warning* issues surface potential problems without failing.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Literal, Sequence

VARIANT_TYPES = ("original", "third_person", "question", "hedged")

CANONICAL_HEDGE = "not entirely sure"
HEDGE_MARKERS = (
    "not sure",
    "not certain",
    "not entirely sure",
    "perhaps",
    "maybe",
    "might",
    "possibly",
    "probably",
    "unsure",
    "uncertain",
    "don't know",
    "do not know",
    "could be",
)

Severity = Literal["error", "warning"]

FIRST_PERSON_RE = re.compile(r"\b(?:I|me|my|mine|myself)\b|\bI['\u2019](?:m|ve|ll|d)\b", re.IGNORECASE)

_NUMERAL_RE = re.compile(r"\d(?:[\d,]*(?:\.\d+)?)?")
_DIGITS_ONLY_RE = re.compile(r"[^\d.]")

_UNIT_RE = re.compile(
    r"\b(?:kilometres?|kilometers?|meters?|metres?|miles?|km|kg|mg|cm|mm|mph|km/h|"
    r"dollars?|euros?|pounds?|rupees?|USD|EUR|INR|GBP|"
    r"hours?|days?|weeks?|months?|years?|percent|million|billion)\b",
    re.IGNORECASE,
)

_MONTH_WORD = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
_DATE_WORD_RE = re.compile(r"\b(" + _MONTH_WORD + r")\s+(\d{1,2}(?:st|nd|rd|th)?)\b", re.IGNORECASE)
_DATE_NUM_RE = re.compile(r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b")

_ENTITY_WORD_RE = re.compile(r"[A-Z\u00c0-\u00de][a-z\u00e0-\u00ff]*(?:['\u2019][A-Za-z]+)?|[A-Z\u00c0-\u00de]{2,}")

_SENTENCE_SPLIT_RE = re.compile(r"[.!?\u3002\uff01\uff1f]+\s*|\n+")

_MONTHS = {
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "jan", "feb", "mar", "apr",
    "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
}
_WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}

_NON_ENTITY_WORDS = {
    "the", "this", "that", "these", "those", "it", "its", "also", "but", "and",
    "so", "our", "my", "your", "i", "he", "his", "she", "her", "they", "their",
    "we", "you", "us", "there", "here", "however", "therefore", "because", "if",
    "when", "then", "well", "okay", "yes", "no", "how", "what", "which", "who",
    "whose", "where", "why", "do", "does", "did", "don't", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "will", "would",
    "should", "could", "can", "may", "might", "must", "not", "for", "from",
    "with", "without", "about", "into", "over", "after", "before", "between",
    "during", "while", "although", "rather", "quite", "very", "more", "most",
    "less", "some", "any", "each", "every", "both", "neither", "at", "by", "in",
    "on", "off", "of", "to", "too", "up", "as", "or", "nor", "than", "now",
    "also", "just", "even", "only", "one", "two", "first", "second", "last",
    "next", "now", "please", "tell", "explain", "describe", "let", "say", "said",
    "says", "good", "bad", "great", "new", "old",
}

_NON_ASCII_LETTERS = "\u00e0\u00e1\u00e2\u00e3\u00e4\u00e5\u00e6\u00e7\u00e8\u00e9\u00ea\u00eb\u00ec\u00ed\u00ee\u00ef\u00f1\u00f2\u00f3\u00f4\u00f5\u00f6\u00f8\u00f9\u00fa\u00fb\u00fc\u00fd\u00fe\u00ff\u00df\u0153\u0161\u017e\u010c\u010d\u011b\u0142\u0144\u015b"

_QUOTE_RE = re.compile(r""""[^"]*"|'[^']*'|\u201c[^\u201d]*\u201d|\u2018[^\u2019]*\u2019""")


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    variant_type: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    issues: list[ValidationIssue]

    @property
    def summary(self) -> str:
        if self.valid:
            return "valid"
        codes = sorted({i.code for i in self.issues})
        return f"invalid ({len(self.issues)} issue(s)): {', '.join(codes)}"


def _issue(code: str, variant_type: str, severity: Severity, message: str) -> ValidationIssue:
    return ValidationIssue(code=code, variant_type=variant_type, severity=severity, message=message)


def _looks_non_english(text: str) -> bool:
    lower = text.lower()
    return any(ch in _NON_ASCII_LETTERS for ch in lower)


def _strip_quotes(text: str) -> str:
    return _QUOTE_RE.sub(" ", text)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]


def _normalize_number(token: str) -> str:
    return _DIGITS_ONLY_RE.sub("", token)


def extract_numbers(text: str) -> list[str]:
    return [_normalize_number(m) for m in _NUMERAL_RE.findall(text)]


def extract_units(text: str) -> set[str]:
    return {m.lower() for m in _UNIT_RE.findall(text)}


def extract_dates(text: str) -> set[str]:
    dates: set[str] = set()
    for m in _DATE_WORD_RE.finditer(text):
        dates.add(f"{m.group(1).lower()} {m.group(2).lower() if m.group(2) else ''}".strip())
    for m in _DATE_NUM_RE.finditer(text):
        dates.add(m.group(0).lower())
    return dates


def extract_proper_nouns(text: str) -> set[str]:
    found: set[str] = set()
    for sentence in _sentences(text):
        tokens = _ENTITY_WORD_RE.findall(sentence)
        if not tokens:
            continue
        first = tokens[0]
        for token in tokens:
            low = token.lower()
            if low in _NON_ENTITY_WORDS or low in _MONTHS or low in _WEEKDAYS:
                continue
            if token == first and sentence.lstrip().startswith(token):
                continue
            found.add(low)
    return found


def _is_question(text: str) -> bool:
    return text.rstrip().endswith(("?", "\uff1f"))


def _source_is_hedged(source: str, non_english: bool) -> bool:
    if non_english:
        return False
    lower = source.lower()
    return any(marker in lower for marker in HEDGE_MARKERS)


def _common_checks(
    source: str,
    variant_type: str,
    text: str,
    source_numbers: Counter,
    source_units: set[str],
    source_dates: set[str],
    source_entities: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not text.strip():
        issues.append(_issue("EMPTY_VARIANT", variant_type, "error", "candidate text is empty"))
        return issues

    variant_numbers = Counter(extract_numbers(text))
    missing_numbers = sorted(
        n for n, count in (source_numbers - variant_numbers).items() for _ in range(count)
    )
    if missing_numbers:
        issues.append(
            _issue(
                "NUMBER_DROPPED",
                variant_type,
                "error",
                f"numbers missing (or modified): {', '.join(missing_numbers)}",
            )
        )

    missing_units = sorted(source_units - extract_units(text))
    if missing_units:
        issues.append(
            _issue("UNIT_DROPPED", variant_type, "error", f"units missing: {', '.join(missing_units)}")
        )

    missing_dates = sorted(source_dates - extract_dates(text))
    if missing_dates:
        issues.append(
            _issue("DATE_DROPPED", variant_type, "error", f"dates missing: {', '.join(missing_dates)}")
        )

    missing_entities = sorted(source_entities - extract_proper_nouns(text))
    if missing_entities and source_entities:
        issues.append(
            _issue(
                "ENTITY_MISSING",
                variant_type,
                "error",
                "named entities missing (heuristic extraction): " + ", ".join(missing_entities),
            )
        )

    if variant_type != "original" and len(source.split()) >= 8:
        variant_words = len(text.split())
        if variant_words < 0.3 * len(source.split()):
            issues.append(
                _issue(
                    "CONTEXT_SHRUNK",
                    variant_type,
                    "warning",
                    f"variant is much shorter than the source ({variant_words} vs {len(source.split())} words)",
                )
            )
    return issues


def _type_specific_checks(
    source: str,
    first: dict[str, object],
    non_english: bool,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if "question" in first:
        q = getattr(first["question"], "text")
        if not _is_question(q):
            if _is_question(source):
                issues.append(
                    _issue(
                        "QUESTION_REQUIRED",
                        "question",
                        "error",
                        "the source is already a question but the variant is not",
                    )
                )
            else:
                issues.append(
                    _issue(
                        "QUESTION_REQUIRED",
                        "question",
                        "error",
                        "the statement must be turned into a genuine question",
                    )
                )

    if "hedged" in first and not non_english:
        h = getattr(first["hedged"], "text")
        if _source_is_hedged(source, non_english):
            if CANONICAL_HEDGE in h.lower():
                issues.append(
                    _issue(
                        "HEDGE_STACKED",
                        "hedged",
                        "error",
                        "hedged variant stacks the canonical hedge on an already-hedged source",
                    )
                )
        else:
            if CANONICAL_HEDGE not in h.lower():
                issues.append(
                    _issue(
                        "HEDGE_MISSING",
                        "hedged",
                        "error",
                        "hedged variant must apply the canonical hedge and the source is not already hedged",
                    )
                )

    if "third_person" in first and not non_english:
        t = getattr(first["third_person"], "text")
        source_scan = _strip_quotes(source)
        variant_scan = _strip_quotes(t)
        if FIRST_PERSON_RE.search(source_scan):
            if FIRST_PERSON_RE.search(variant_scan):
                issues.append(
                    _issue(
                        "FIRST_PERSON_UNCONVERTED",
                        "third_person",
                        "error",
                        "first-person framing in the source was not converted to third person",
                    )
                )
        else:
            if FIRST_PERSON_RE.search(variant_scan):
                issues.append(
                    _issue(
                        "FIRST_PERSON_ADDED",
                        "third_person",
                        "error",
                        "first-person framing was introduced although the source had none",
                    )
                )

    return issues


def validate_variants(source_prompt: str, candidates: Sequence[object]) -> ValidationResult:
    """Return a structured validation result for ``candidates`` vs ``source_prompt``.

    ``candidates`` are any objects exposing ``variant_type`` and ``text``.
    """
    issues: list[ValidationIssue] = []
    counts: dict[str, int] = {}
    first: dict[str, object] = {}

    for candidate in candidates:
        t = getattr(candidate, "variant_type")
        counts[t] = counts.get(t, 0) + 1
        first.setdefault(t, candidate)

    unknown = sorted(set(counts) - set(VARIANT_TYPES))
    for t in unknown:
        issues.append(_issue("UNKNOWN_VARIANT_TYPE", t, "error", f"unexpected variant type '{t}'"))
    for t, n in counts.items():
        if t in VARIANT_TYPES and n > 1:
            issues.append(
                _issue("DUPLICATE_VARIANT_TYPE", t, "error", f"variant type '{t}' appears {n} times")
            )
    for t in VARIANT_TYPES:
        if counts.get(t, 0) == 0:
            issues.append(_issue("MISSING_VARIANT_TYPE", t, "error", f"required variant type '{t}' is missing"))

    if "original" in first:
        if getattr(first["original"], "text") != source_prompt:
            issues.append(
                _issue(
                    "ORIGINAL_MISMATCH",
                    "original",
                    "error",
                    "the original variant is not byte-for-byte identical to the source",
                )
            )

    non_english = _looks_non_english(source_prompt)
    source_numbers = Counter(extract_numbers(source_prompt))
    source_units = extract_units(source_prompt)
    source_dates = extract_dates(source_prompt)
    source_entities = extract_proper_nouns(source_prompt)

    for t in VARIANT_TYPES:
        if t in first:
            issues.extend(
                _common_checks(
                    source_prompt,
                    t,
                    getattr(first[t], "text"),
                    source_numbers,
                    source_units,
                    source_dates,
                    source_entities,
                )
            )

    issues.extend(_type_specific_checks(source_prompt, first, non_english))

    valid = not any(i.severity == "error" for i in issues)
    return ValidationResult(valid=valid, issues=issues)