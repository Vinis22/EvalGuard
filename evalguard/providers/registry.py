"""Maps config `provider.type` strings to LLMProvider implementations."""
from __future__ import annotations

from typing import Any

from evalguard.providers.base import LLMProvider
from evalguard.providers.mock_llm import MockLLMProvider

PROVIDERS: dict[str, type[LLMProvider]] = {
    "mock": MockLLMProvider,
}


def get_provider(provider_type: str, model: str, options: dict[str, Any] | None = None) -> LLMProvider:
    """Instantiate the LLMProvider registered under ``provider_type``.

    To plug in a real provider (e.g. OpenAI or Anthropic), implement
    ``LLMProvider`` in a new module under ``evalguard/providers/`` and add
    it to the ``PROVIDERS`` dict above, e.g.::

        from evalguard.providers.openai_llm import OpenAIProvider
        PROVIDERS["openai"] = OpenAIProvider

    then set ``provider.type: openai`` in your YAML config.
    """
    try:
        provider_cls = PROVIDERS[provider_type]
    except KeyError as exc:
        available = ", ".join(sorted(PROVIDERS))
        raise ValueError(
            f"Unknown provider type '{provider_type}'. Available providers: {available}. "
            "See evalguard/providers/base.py to add a new one."
        ) from exc
    return provider_cls(model=model, options=options)
