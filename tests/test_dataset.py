import json
from pathlib import Path

import pytest

from evalguard.dataset import load_dataset


def write_jsonl(tmp_path: Path, lines: list[dict]) -> Path:
    path = tmp_path / "dataset.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line) + "\n")
    return path


def test_load_valid_dataset(tmp_path: Path) -> None:
    path = write_jsonl(
        tmp_path,
        [
            {"id": "case-a", "inputs": {"x": 1}, "expected": {"value": "y"}},
            {"inputs": {"x": 2}, "expected": {"value": "z"}},
        ],
    )
    cases = load_dataset(path)
    assert len(cases) == 2
    assert cases[0].id == "case-a"
    assert cases[0].inputs == {"x": 1}
    assert cases[1].id == "case-2"  # auto-generated from line number


def test_load_dataset_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    path.write_text(
        '{"inputs": {"a": 1}, "expected": {"value": "1"}}\n\n\n'
        '{"inputs": {"a": 2}, "expected": {"value": "2"}}\n',
        encoding="utf-8",
    )
    cases = load_dataset(path)
    assert len(cases) == 2


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "missing.jsonl")


def test_invalid_json_raises_with_line_number(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    path.write_text('{"inputs": {}, "expected": {}}\nnot json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_dataset(path)


def test_non_object_line_raises(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    path.write_text("[1, 2, 3]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_dataset(path)


def test_empty_dataset_raises(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    path.write_text("\n\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no cases"):
        load_dataset(path)
