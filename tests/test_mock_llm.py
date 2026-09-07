from evalguard.providers.mock_llm import MockLLMProvider


def test_mock_llm_is_deterministic() -> None:
    provider = MockLLMProvider(model="mock-llm-v1")
    prompt = "Please help regarding a refund. Customer message: I want my money back."
    first = provider.complete(prompt)
    second = provider.complete(prompt)
    assert first == second


def test_mock_llm_refund_branch() -> None:
    provider = MockLLMProvider(model="mock-llm-v1")
    response = provider.complete("Customer message: please refund my last charge")
    assert "refund" in response.lower()
    assert "billing team" in response.lower()


def test_mock_llm_password_branch() -> None:
    provider = MockLLMProvider(model="mock-llm-v1")
    response = provider.complete("Customer message: my password does not work")
    assert "password" in response.lower()


def test_mock_llm_technical_branch() -> None:
    provider = MockLLMProvider(model="mock-llm-v1")
    response = provider.complete("Customer message: I found a bug in the app")
    assert "engineering team" in response.lower()


def test_mock_llm_generic_branch() -> None:
    provider = MockLLMProvider(model="mock-llm-v1")
    response = provider.complete("Customer message: what are your business hours")
    assert "support team" in response.lower()


def test_mock_llm_greeting_branch() -> None:
    provider = MockLLMProvider(model="mock-llm-v1")
    response = provider.complete("Hello there, just checking in")
    assert "how can i help you today" in response.lower()


def test_mock_llm_classification_mode() -> None:
    provider = MockLLMProvider(model="mock-llm-v1")
    response = provider.complete("Classify the following ticket into a category: I need a refund")
    assert response in {"billing", "technical", "account", "general"}
