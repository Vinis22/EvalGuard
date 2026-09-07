from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):

    def __init__(self, model: str, options: dict[str, Any] | None = None) -> None:
        self.model = model
        self.options = options or {}

    @abstractmethod
    def complete(self, prompt: str) -> str:
        raise NotImplementedError
