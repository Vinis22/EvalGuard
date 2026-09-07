"""Provider interface. Implement this to plug a real LLM into EvalGuard."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract interface for anything that can turn a prompt into text.

    To add a real backend (OpenAI, Anthropic, a local model, ...):

    1. Subclass ``LLMProvider`` and implement :meth:`complete`.
    2. Register it in ``evalguard.providers.registry.PROVIDERS`` under a
       unique ``type`` key.
    3. Reference that key as ``provider.type`` in the YAML config, and put
       any provider-specific settings (API key env var name, temperature,
       base URL, ...) under ``provider.options``.

    See ``evalguard/providers/mock_llm.py`` for a complete, dependency-free
    example implementation.
    """

    def __init__(self, model: str, options: dict[str, Any] | None = None) -> None:
        self.model = model
        self.options = options or {}

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Return the model's completion for the given rendered prompt."""
        raise NotImplementedError
