from __future__ import annotations

import hashlib
import re

from evalguard.providers.base import LLMProvider

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "billing": ("invoice", "charge", "refund", "payment", "billing", "subscription", "price"),
    "technical": ("error", "bug", "crash", "not working", "broken", "exception", "fails", "failing"),
    "account": ("password", "login", "account", "locked", "email address", "username"),
    "general": ("hours", "location", "contact", "hello", "thanks", "thank you"),
}

_GREETINGS = ("hi", "hello", "hey", "greetings")


class MockLLMProvider(LLMProvider):

    def complete(self, prompt: str) -> str:
        lowered = prompt.lower()
        if "categor" in lowered or "classif" in lowered:
            return self._classify(lowered)
        return self._reply(prompt, lowered)

    def _classify(self, lowered_prompt: str) -> str:
        scores: dict[str, int] = {}
        for category, keywords in _CATEGORY_KEYWORDS.items():
            scores[category] = sum(1 for kw in keywords if kw in lowered_prompt)

        best_score = max(scores.values())
        if best_score == 0:
            return "general"

        top_categories = sorted(c for c, s in scores.items() if s == best_score)
        if len(top_categories) > 1:
            digest = hashlib.sha256(lowered_prompt.encode("utf-8")).hexdigest()
            index = int(digest[:8], 16) % len(top_categories)
            return top_categories[index]
        return top_categories[0]

    def _reply(self, prompt: str, lowered_prompt: str) -> str:
        if any(greeting in lowered_prompt for greeting in _GREETINGS):
            return "Hello! Thanks for reaching out. How can I help you today?"

        subject = self._extract_subject(prompt)
        digest = hashlib.sha256(lowered_prompt.encode("utf-8")).hexdigest()[:6]

        if "refund" in lowered_prompt:
            return (
                f"I understand you're asking about a refund regarding {subject}. "
                f"I've flagged this for our billing team (ref #{digest})."
            )
        if "password" in lowered_prompt or "login" in lowered_prompt:
            return (
                "You can reset your password from the login screen by clicking "
                f"'Forgot password'. Reference #{digest}."
            )
        if "error" in lowered_prompt or "bug" in lowered_prompt or "crash" in lowered_prompt:
            return (
                f"Thanks for reporting this issue with {subject}. Our engineering "
                f"team has been notified (ref #{digest})."
            )
        return (
            f"Thanks for your message about {subject}. A member of our support "
            f"team will follow up shortly (ref #{digest})."
        )

    @staticmethod
    def _extract_subject(prompt: str) -> str:
        match = re.search(r"(?:about|regarding|with)\s+([a-zA-Z0-9 _-]{3,40})", prompt)
        if match:
            return match.group(1).strip().rstrip(".,!?")
        words = prompt.split()
        return " ".join(words[:5]) if words else "your request"
