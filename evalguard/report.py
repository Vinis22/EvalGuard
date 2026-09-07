"""Generates JSON (machine-readable) and HTML (human-readable) reports."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from evalguard.runner import RunResult

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _run_to_dict(run: RunResult) -> dict[str, Any]:
    """Serialize a RunResult into the JSON shape consumed by the CLI report
    and the frontend/index.html viewer. Keep this shape stable — the
    frontend depends on it.
    """
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "name": run.name,
        "provider": {"type": run.provider_type, "model": run.provider_model},
        "min_score": run.min_score,
        "overall_score": round(run.overall_score, 4),
        "overall_passed": run.overall_passed,
        "total_cases": run.total_cases,
        "passed_cases": run.passed_cases,
        "failed_cases": run.failed_cases,
        "duration_seconds": round(run.duration_seconds, 4),
        "cases": [
            {
                "id": case.case_id,
                "description": case.description,
                "inputs": case.inputs,
                "prompt": case.prompt,
                "expected": case.expected,
                "actual": case.actual,
                "score": round(case.score, 4),
                "passed": case.passed,
                "evaluations": [
                    {
                        "evaluator": e.evaluator,
                        "score": round(e.score, 4),
                        "passed": e.passed,
                        "detail": e.detail,
                        "weight": e.weight,
                    }
                    for e in case.evaluations
                ],
            }
            for case in run.cases
        ],
    }


def write_json_report(run: RunResult, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = _run_to_dict(run)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def write_html_report(run: RunResult, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html.jinja")

    data = _run_to_dict(run)
    html = template.render(report=data)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def generate_reports(run: RunResult, report_dir: str | Path) -> tuple[Path, Path]:
    """Write both JSON and HTML reports into ``report_dir``. Returns (json_path, html_path)."""
    report_dir = Path(report_dir)
    json_path = write_json_report(run, report_dir / "report.json")
    html_path = write_html_report(run, report_dir / "report.html")
    return json_path, html_path
