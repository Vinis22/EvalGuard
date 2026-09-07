"""Orchestrates a full EvalGuard run: render -> generate -> evaluate -> aggregate."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Template

from evalguard.config import EvalGuardConfig
from evalguard.dataset import EvalCase, load_dataset
from evalguard.evaluators import EvaluationResult, run_evaluator
from evalguard.providers import get_provider


@dataclass
class CaseResult:
    case_id: str
    description: str | None
    inputs: dict[str, Any]
    prompt: str
    expected: dict[str, Any]
    actual: str
    evaluations: list[EvaluationResult]
    score: float
    passed: bool


@dataclass
class RunResult:
    name: str
    provider_type: str
    provider_model: str
    min_score: float
    overall_score: float
    overall_passed: bool
    total_cases: int
    passed_cases: int
    failed_cases: int
    duration_seconds: float
    cases: list[CaseResult] = field(default_factory=list)


def _score_case(config: EvalGuardConfig, case: EvalCase, actual: str) -> tuple[list[EvaluationResult], float]:
    evaluations: list[EvaluationResult] = []
    for evaluator_cfg in config.evaluators:
        result = run_evaluator(
            evaluator_cfg.type,
            actual=actual,
            expected=case.expected,
            options=evaluator_cfg.options,
        )
        result.weight = evaluator_cfg.weight
        evaluations.append(result)

    total_weight = sum(e.weight for e in evaluations) or 1.0
    weighted_score = sum(e.score * e.weight for e in evaluations) / total_weight
    return evaluations, weighted_score


def run_eval(config: EvalGuardConfig, base_dir: Path) -> RunResult:
    """Execute the full eval pipeline described by ``config`` and return results."""
    started = time.perf_counter()

    dataset_path = config.resolve_dataset_path(base_dir)
    cases = load_dataset(dataset_path)

    template_text = config.prompt.resolve(base_dir)
    template = Template(template_text)

    provider = get_provider(
        config.provider.type,
        model=config.provider.model,
        options=config.provider.options,
    )

    case_results: list[CaseResult] = []
    for case in cases:
        rendered_prompt = template.render(**case.inputs)
        actual = provider.complete(rendered_prompt)
        evaluations, score = _score_case(config, case, actual)
        case_passed = score >= config.min_score

        case_results.append(
            CaseResult(
                case_id=case.id,
                description=case.description,
                inputs=case.inputs,
                prompt=rendered_prompt,
                expected=case.expected,
                actual=actual,
                evaluations=evaluations,
                score=score,
                passed=case_passed,
            )
        )

    total = len(case_results)
    passed_count = sum(1 for c in case_results if c.passed)
    overall_score = sum(c.score for c in case_results) / total if total else 0.0
    overall_passed = overall_score >= config.min_score

    duration = time.perf_counter() - started

    return RunResult(
        name=config.name,
        provider_type=config.provider.type,
        provider_model=config.provider.model,
        min_score=config.min_score,
        overall_score=overall_score,
        overall_passed=overall_passed,
        total_cases=total,
        passed_cases=passed_count,
        failed_cases=total - passed_count,
        duration_seconds=duration,
        cases=case_results,
    )
