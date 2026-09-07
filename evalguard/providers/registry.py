from __future__ import annotations

from typing import Any

from evalguard.providers.base import LLMProvider
from evalguard.providers.mock_llm import MockLLMProvider

PROVIDERS: dict[str, type[LLMProvider]] = {
    "mock": MockLLMProvider,
}


def get_provider(provider_type: str, model: str, options: dict[str, Any] | None = None) -> LLMProvider:
    try:
        provider_cls = PROVIDERS[provider_type]
    except KeyError as exc:
        available = ", ".join(sorted(PROVIDERS))
        raise ValueError(
            f"Unknown provider type '{provider_type}'. Available providers: {available}. "
            "See evalguard/providers/base.py to add a new one."
        ) from exc
    return provider_cls(model=model, options=options)
