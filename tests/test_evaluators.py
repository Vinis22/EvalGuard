from evalguard.evaluators import (
    contains,
    exact_match,
    keyword_overlap,
    regex_match,
    run_evaluator,
)


def test_exact_match_pass_case_insensitive() -> None:
    result = exact_match("Hello World", {"value": "hello world"}, {})
    assert result.passed is True
    assert result.score == 1.0


def test_exact_match_fail() -> None:
    result = exact_match("Hello World", {"value": "goodbye"}, {})
    assert result.passed is False
    assert result.score == 0.0


def test_exact_match_case_sensitive() -> None:
    result = exact_match("Hello", {"value": "hello"}, {"case_sensitive": True})
    assert result.passed is False


def test_contains_all_present() -> None:
    result = contains("The quick brown fox", {"value": ["quick", "fox"]}, {})
    assert result.passed is True
    assert result.score == 1.0


def test_contains_partial_missing() -> None:
    result = contains("The quick brown fox", {"value": ["quick", "elephant"]}, {})
    assert result.passed is False
    assert result.score == 0.5


def test_contains_single_string_target() -> None:
    result = contains("The quick brown fox", {"value": "quick"}, {})
    assert result.passed is True


def test_regex_match_pass() -> None:
    result = regex_match("Order #12345 confirmed", {"pattern": r"#\d+"}, {})
    assert result.passed is True


def test_regex_match_fail() -> None:
    result = regex_match("No order number here", {"pattern": r"#\d+"}, {})
    assert result.passed is False


def test_regex_match_invalid_pattern() -> None:
    result = regex_match("text", {"pattern": "(unclosed"}, {})
    assert result.passed is False
    assert result.score == 0.0


def test_keyword_overlap_full_match() -> None:
    result = keyword_overlap(
        "The billing team issued a refund for the duplicate charge",
        {"reference": "billing team refund duplicate charge"},
        {},
    )
    assert result.passed is True
    assert result.score == 1.0


def test_keyword_overlap_partial_below_threshold() -> None:
    result = keyword_overlap(
        "Thanks for your message",
        {"reference": "billing team refund duplicate charge investigation"},
        {"min_overlap": 0.5},
    )
    assert result.passed is False
    assert result.score < 0.5


def test_keyword_overlap_empty_reference() -> None:
    result = keyword_overlap("some response", {"reference": ""}, {})
    assert result.passed is False
    assert result.score == 0.0


def test_run_evaluator_dispatches_correctly() -> None:
    result = run_evaluator("exact_match", "abc", {"value": "abc"}, {})
    assert result.evaluator == "exact_match"
    assert result.passed is True


def test_run_evaluator_unknown_type_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="Unknown evaluator type"):
        run_evaluator("nonexistent", "abc", {}, {})
