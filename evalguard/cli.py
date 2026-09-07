from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from evalguard.config import load_config
from evalguard.report import generate_reports
from evalguard.runner import run_eval

app = typer.Typer(
    name="evalguard",
    help="EvalGuard — automated regression testing for LLM prompts and agents.",
    add_completion=False,
)
console = Console()

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@app.command()
def run(
    config_path: Path = typer.Argument(..., help="Path to the EvalGuard YAML config file."),
    report_dir: str | None = typer.Option(
        None, "--report-dir", help="Override the report output directory from the config."
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress the per-case table output."),
) -> None:
    config_path = config_path.resolve()
    base_dir = config_path.parent

    try:
        config = load_config(config_path)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Failed to load config:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    console.print(f"[bold]EvalGuard[/bold] running suite [cyan]{config.name}[/cyan] from {config_path}")

    try:
        result = run_eval(config, base_dir)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Eval run failed:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    if not quiet:
        table = Table(title="Case Results", show_lines=False)
        table.add_column("Case", style="cyan", no_wrap=True)
        table.add_column("Score", justify="right")
        table.add_column("Result", justify="center")
        for case in result.cases:
            status = "[green]PASS[/green]" if case.passed else "[red]FAIL[/red]"
            table.add_row(case.case_id, f"{case.score * 100:.1f}%", status)
        console.print(table)

    output_dir = Path(report_dir) if report_dir else config.resolve_report_dir(base_dir)
    json_path, html_path = generate_reports(result, output_dir)

    verdict_style = "green" if result.overall_passed else "red"
    verdict_text = "PASSED" if result.overall_passed else "FAILED"

    console.print("")
    console.print(
        f"Overall score: [bold]{result.overall_score * 100:.1f}%[/bold] "
        f"(threshold {config.min_score * 100:.1f}%) — "
        f"[bold {verdict_style}]{verdict_text}[/bold {verdict_style}]"
    )
    console.print(f"Cases: {result.passed_cases}/{result.total_cases} passed, {result.failed_cases} failed")
    console.print(f"JSON report: [underline]{json_path}[/underline]")
    console.print(f"HTML report: [underline]{html_path}[/underline]")

    if not result.overall_passed:
        raise typer.Exit(code=1)


@app.command()
def init(
    target_dir: Path = typer.Argument(
        Path("."), help="Directory to scaffold a new EvalGuard eval project into."
    ),
) -> None:
    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    dest_config = target_dir / "config.yaml"
    dest_dataset = target_dir / "dataset.jsonl"

    if dest_config.exists() or dest_dataset.exists():
        console.print(
            f"[bold yellow]Refusing to overwrite existing files in {target_dir}. "
            "Remove config.yaml/dataset.jsonl first, or choose a different directory.[/bold yellow]"
        )
        raise typer.Exit(code=1)

    src_config = EXAMPLES_DIR / "config.yaml"
    src_dataset = EXAMPLES_DIR / "dataset.jsonl"

    if not src_config.exists() or not src_dataset.exists():
        console.print("[bold red]Could not locate bundled example files to scaffold from.[/bold red]")
        raise typer.Exit(code=2)

    shutil.copyfile(src_config, dest_config)
    shutil.copyfile(src_dataset, dest_dataset)

    console.print(f"[bold green]Scaffolded new EvalGuard project in {target_dir}[/bold green]")
    console.print(f"  - {dest_config}")
    console.print(f"  - {dest_dataset}")
    console.print("")
    console.print(f"Run it with: [cyan]evalguard run {dest_config}[/cyan]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
