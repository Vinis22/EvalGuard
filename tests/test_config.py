from pathlib import Path

import pytest
from pydantic import ValidationError

from evalguard.config import EvalGuardConfig, load_config


def write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_valid_config(tmp_path: Path) -> None:
    config_path = write_yaml(
        tmp_path,
        """
        name: my-suite
        provider:
          type: mock
          model: mock-llm-v1
        prompt:
          template: "Hello {{ name }}"
        dataset_path: dataset.jsonl
        evaluators:
          - type: contains
        min_score: 0.75
        """,
    )
    config = load_config(config_path)
    assert config.name == "my-suite"
    assert config.provider.type == "mock"
    assert config.prompt.template == "Hello {{ name }}"
    assert config.min_score == 0.75
    assert config.evaluators[0].type == "contains"


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "does-not-exist.yaml")


def test_config_requires_at_least_one_evaluator(tmp_path: Path) -> None:
    config_path = write_yaml(
        tmp_path,
        """
        prompt:
          template: "Hello"
        dataset_path: dataset.jsonl
        evaluators: []
        """,
    )
    with pytest.raises(ValidationError):
        load_config(config_path)


def test_prompt_requires_template_or_path() -> None:
    with pytest.raises(ValidationError):
        EvalGuardConfig.model_validate(
            {
                "prompt": {},
                "dataset_path": "dataset.jsonl",
                "evaluators": [{"type": "contains"}],
            }
        )


def test_prompt_rejects_both_template_and_path() -> None:
    with pytest.raises(ValidationError):
        EvalGuardConfig.model_validate(
            {
                "prompt": {"template": "hi", "template_path": "x.jinja"},
                "dataset_path": "dataset.jsonl",
                "evaluators": [{"type": "contains"}],
            }
        )


def test_default_min_score_and_provider(tmp_path: Path) -> None:
    config_path = write_yaml(
        tmp_path,
        """
        prompt:
          template: "Hello"
        dataset_path: dataset.jsonl
        evaluators:
          - type: exact_match
        """,
    )
    config = load_config(config_path)
    assert config.min_score == 0.8
    assert config.provider.type == "mock"


def test_resolve_dataset_path_relative_to_base_dir(tmp_path: Path) -> None:
    config_path = write_yaml(
        tmp_path,
        """
        prompt:
          template: "Hello"
        dataset_path: sub/dataset.jsonl
        evaluators:
          - type: exact_match
        """,
    )
    config = load_config(config_path)
    resolved = config.resolve_dataset_path(tmp_path)
    assert resolved == tmp_path / "sub" / "dataset.jsonl"


def test_prompt_resolve_from_inline_template(tmp_path: Path) -> None:
    config_path = write_yaml(
        tmp_path,
        """
        prompt:
          template: "Say hi to {{ name }}"
        dataset_path: dataset.jsonl
        evaluators:
          - type: exact_match
        """,
    )
    config = load_config(config_path)
    assert config.prompt.resolve(tmp_path) == "Say hi to {{ name }}"


def test_prompt_resolve_from_file(tmp_path: Path) -> None:
    template_file = tmp_path / "prompt.jinja"
    template_file.write_text("Template contents {{ x }}", encoding="utf-8")
    config_path = write_yaml(
        tmp_path,
        """
        prompt:
          template_path: prompt.jinja
        dataset_path: dataset.jsonl
        evaluators:
          - type: exact_match
        """,
    )
    config = load_config(config_path)
    assert config.prompt.resolve(tmp_path) == "Template contents {{ x }}"
