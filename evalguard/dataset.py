"""JSONL dataset loading for EvalGuard."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """A single test case: input variables plus expected criteria."""

    id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None


def load_dataset(dataset_path: str | Path) -> list[EvalCase]:
    """Load a JSONL dataset file into a list of EvalCase objects.

    Each non-blank line must be a JSON object with at least ``inputs`` and
    ``expected`` keys. An ``id`` is auto-generated from the line number if
    not provided.
    """
    dataset_path = Path(dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    cases: list[EvalCase] = []
    with dataset_path.open("r", encoding="utf-8") as fh:
        for line_number, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {dataset_path}: {exc}"
                ) from exc
            if not isinstance(data, dict):
                raise ValueError(
                    f"Line {line_number} of {dataset_path} must be a JSON object"
                )
            data.setdefault("id", f"case-{line_number}")
            cases.append(EvalCase.model_validate(data))

    if not cases:
        raise ValueError(f"Dataset file {dataset_path} contains no cases")

    return cases
