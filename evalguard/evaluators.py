from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class EvaluationResult:
    evaluator: str
    score: float
    passed: bool
    detail: str
    weight: float = 1.0


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def exact_match(actual: str, expected: dict[str, Any], options: dict[str, Any]) -> EvaluationResult:
    target = expected.get("value", expected.get("output", ""))
    case_sensitive = bool(options.get("case_sensitive", False))

    if case_sensitive:
        passed = actual.strip() == str(target).strip()
    else:
        passed = _normalize(actual) == _normalize(str(target))

    return EvaluationResult(
        evaluator="exact_match",
        score=1.0 if passed else 0.0,
        passed=passed,
        detail=f"expected exact match with {target!r}" if not passed else "exact match",
    )


def contains(actual: str, expected: dict[str, Any], options: dict[str, Any]) -> EvaluationResult:
    raw_targets = expected.get("value", expected.get("contains", []))
    targets: list[str] = [raw_targets] if isinstance(raw_targets, str) else list(raw_targets)
    case_sensitive = bool(options.get("case_sensitive", False))

    haystack = actual if case_sensitive else actual.lower()
    missing = [
        t for t in targets
        if (t if case_sensitive else t.lower()) not in haystack
    ]

    total = len(targets) or 1
    score = (total - len(missing)) / total
    passed = not missing

    detail = "all substrings found" if passed else f"missing substrings: {missing}"
    return EvaluationResult(evaluator="contains", score=score, passed=passed, detail=detail)


def regex_match(actual: str, expected: dict[str, Any], options: dict[str, Any]) -> EvaluationResult:
    pattern = expected.get("pattern", expected.get("value", ""))
    flags = re.IGNORECASE if options.get("case_insensitive", True) else 0

    try:
        match = re.search(pattern, actual, flags)
    except re.error as exc:
        return EvaluationResult(
            evaluator="regex_match",
            score=0.0,
            passed=False,
            detail=f"invalid regex pattern {pattern!r}: {exc}",
        )

    passed = match is not None
    detail = f"matched pattern {pattern!r}" if passed else f"no match for pattern {pattern!r}"
    return EvaluationResult(evaluator="regex_match", score=1.0 if passed else 0.0, passed=passed, detail=detail)


_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "and", "or", "in", "on", "at", "for", "with", "this",
    "that", "it", "as", "by", "from", "your", "you", "i", "we", "our",
}


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


def keyword_overlap(actual: str, expected: dict[str, Any], options: dict[str, Any]) -> EvaluationResult:
    reference = str(expected.get("reference", expected.get("value", "")))
    min_overlap = float(options.get("min_overlap", 0.5))

    expected_tokens = _tokenize(reference)
    actual_tokens = _tokenize(actual)

    if not expected_tokens:
        return EvaluationResult(
            evaluator="keyword_overlap",
            score=0.0,
            passed=False,
            detail="expected reference text has no meaningful keywords to compare",
        )

    overlap = expected_tokens & actual_tokens
    score = len(overlap) / len(expected_tokens)
    passed = score >= min_overlap

    detail = (
        f"matched {len(overlap)}/{len(expected_tokens)} keywords "
        f"({sorted(overlap)}), threshold={min_overlap}"
    )
    return EvaluationResult(evaluator="keyword_overlap", score=score, passed=passed, detail=detail)


EVALUATORS: dict[str, Callable[[str, dict[str, Any], dict[str, Any]], EvaluationResult]] = {
    "exact_match": exact_match,
    "contains": contains,
    "regex_match": regex_match,
    "keyword_overlap": keyword_overlap,
}


def run_evaluator(evaluator_type: str, actual: str, expected: dict[str, Any], options: dict[str, Any]) -> EvaluationResult:
    try:
        fn = EVALUATORS[evaluator_type]
    except KeyError as exc:
        available = ", ".join(sorted(EVALUATORS))
        raise ValueError(f"Unknown evaluator type '{evaluator_type}'. Available: {available}") from exc
    return fn(actual, expected, options)
