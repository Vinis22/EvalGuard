"""Pydantic models and loader for EvalGuard YAML config files."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class ProviderConfig(BaseModel):
    """Configuration for the LLM provider used to generate responses."""

    type: Literal["mock", "openai", "anthropic"] = "mock"
    model: str = "mock-llm-v1"
    options: dict[str, Any] = Field(default_factory=dict)


class PromptConfig(BaseModel):
    """Where the prompt template comes from: an inline string or a file path."""

    template: str | None = None
    template_path: str | None = None

    @model_validator(mode="after")
    def _one_of_template_or_path(self) -> "PromptConfig":
        if not self.template and not self.template_path:
            raise ValueError(
                "prompt config must define either 'template' (inline) or 'template_path'"
            )
        if self.template and self.template_path:
            raise ValueError(
                "prompt config must define only one of 'template' or 'template_path', not both"
            )
        return self

    def resolve(self, base_dir: Path) -> str:
        """Return the raw Jinja2 template text."""
        if self.template is not None:
            return self.template
        path = Path(self.template_path)  # type: ignore[arg-type]
        if not path.is_absolute():
            path = base_dir / path
        return path.read_text(encoding="utf-8")


class EvaluatorConfig(BaseModel):
    """A single evaluator to run against each case's response."""

    type: Literal["exact_match", "contains", "regex_match", "keyword_overlap"]
    options: dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0


class EvalGuardConfig(BaseModel):
    """Top-level EvalGuard run configuration, loaded from YAML."""

    name: str = "evalguard-run"
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    prompt: PromptConfig
    dataset_path: str
    evaluators: list[EvaluatorConfig] = Field(min_length=1)
    min_score: float = Field(default=0.8, ge=0.0, le=1.0)
    report_dir: str = "reports"

    def resolve_dataset_path(self, base_dir: Path) -> Path:
        path = Path(self.dataset_path)
        if not path.is_absolute():
            path = base_dir / path
        return path

    def resolve_report_dir(self, base_dir: Path) -> Path:
        path = Path(self.report_dir)
        if not path.is_absolute():
            path = base_dir / path
        return path


def load_config(config_path: str | Path) -> EvalGuardConfig:
    """Load and validate an EvalGuard YAML config file."""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Config file {config_path} must contain a YAML mapping at the top level")

    return EvalGuardConfig.model_validate(raw)
