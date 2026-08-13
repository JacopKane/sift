"""Steps for tests/features/provider.feature.

No network: this builds real clients and inspects them. Constructing a client
does not call anything, so the whole provider switch is verifiable for free.
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from pytest_bdd import given, parsers, scenarios, then, when

from sift import config
from sift.classify.classifier import chat_model

scenarios("provider.feature")

KEYS = {
    "google_genai": "google_api_key",
    "openai": "openai_api_key",
    "anthropic": "anthropic_api_key",
}


@given(parsers.parse('the provider is "{provider}" using "{model}"'))
def the_provider_is(monkeypatch: pytest.MonkeyPatch, provider: str, model: str) -> None:
    # Every provider gets a distinct fake key, so "was it handed the right one"
    # is answerable rather than assumed.
    monkeypatch.setenv("SIFT_PROVIDER", provider)
    monkeypatch.setenv("SIFT_MODEL", model)
    for name, field in KEYS.items():
        monkeypatch.setenv(field.upper(), f"test-key-for-{name}")
    config.settings.cache_clear()


@when("the chat model is built", target_fixture="client")
def the_chat_model_is_built() -> BaseChatModel:
    return chat_model()


@then(parsers.parse("it is a {name}"))
def it_is_a(client: BaseChatModel, name: str) -> None:
    assert type(client).__name__ == name


@then("it was given the key for that provider")
def given_the_right_key(client: BaseChatModel) -> None:
    expected = f"test-key-for-{config.settings().provider}"
    assert expected in _secrets(client), (
        f"the {config.settings().provider} client did not receive its own key"
    )


@then("thinking is disabled")
def thinking_is_disabled(client: BaseChatModel) -> None:
    assert getattr(client, "thinking_budget", None) == 0


@then("it was not handed a thinking budget")
def no_thinking_budget(client: BaseChatModel) -> None:
    # Gemini's option passed to another provider is a startup crash, not a
    # graceful ignore, so the guard around it has to hold.
    assert getattr(client, "thinking_budget", None) is None


@then("it is paced by the shared limiter")
def paced_by_the_limiter(client: BaseChatModel) -> None:
    assert client.rate_limiter is not None


def _secrets(client: BaseChatModel) -> str:
    """Every stored value, with SecretStr unwrapped, as one searchable string."""
    found: list[str] = []
    for value in client.model_dump().values():
        found.append(str(value))
    for name in ("api_key", "google_api_key", "openai_api_key", "anthropic_api_key"):
        attribute: Any = getattr(client, name, None)
        if attribute is not None:
            unwrap = getattr(attribute, "get_secret_value", None)
            found.append(unwrap() if unwrap else str(attribute))
    return " ".join(found)
