"""End-to-end test running the actual CLI against the bundled examples."""
import json
from pathlib import Path

from typer.testing import CliRunner

from evalguard.cli import app

runner = CliRunner()

EXAMPLES_CONFIG = Path(__file__).parent.parent / "examples" / "config.yaml"


def test_cli_run_end_to_end(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    result = runner.invoke(
        app,
        ["run", str(EXAMPLES_CONFIG), "--report-dir", str(report_dir)],
    )

    assert result.exit_code == 0, result.output

    json_report = report_dir / "report.json"
    html_report = report_dir / "report.html"
    assert json_report.exists()
    assert html_report.exists()
    assert json_report.stat().st_size > 0
    assert html_report.stat().st_size > 0

    data = json.loads(json_report.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["total_cases"] == 10
    assert data["passed_cases"] > 0
    assert data["failed_cases"] > 0
    assert 0.0 <= data["overall_score"] <= 1.0
    assert isinstance(data["overall_passed"], bool)
    assert len(data["cases"]) == data["total_cases"]

    first_case = data["cases"][0]
    for key in ("id", "inputs", "prompt", "expected", "actual", "score", "passed", "evaluations"):
        assert key in first_case

    html_content = html_report.read_text(encoding="utf-8")
    assert "EvalGuard" in html_content
    assert data["name"] in html_content


def test_cli_run_fails_when_threshold_not_met(tmp_path: Path) -> None:
    config_path = tmp_path / "strict-config.yaml"
    config_path.write_text(
        f"""
name: strict-suite
provider:
  type: mock
  model: mock-llm-v1
prompt:
  template_path: {(EXAMPLES_CONFIG.parent / 'prompt.jinja').as_posix()}
dataset_path: {(EXAMPLES_CONFIG.parent / 'dataset.jsonl').as_posix()}
evaluators:
  - type: contains
    options:
      case_sensitive: false
min_score: 0.99
report_dir: {(tmp_path / 'reports').as_posix()}
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["run", str(config_path)])
    assert result.exit_code == 1


def test_cli_run_missing_config_exits_nonzero(tmp_path: Path) -> None:
    result = runner.invoke(app, ["run", str(tmp_path / "nope.yaml")])
    assert result.exit_code != 0


def test_cli_init_scaffolds_project(tmp_path: Path) -> None:
    target = tmp_path / "my-project"
    result = runner.invoke(app, ["init", str(target)])
    assert result.exit_code == 0
    assert (target / "config.yaml").exists()
    assert (target / "dataset.jsonl").exists()


def test_cli_init_refuses_to_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "my-project"
    runner.invoke(app, ["init", str(target)])
    result = runner.invoke(app, ["init", str(target)])
    assert result.exit_code == 1
