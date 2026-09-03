from unittest.mock import Mock

import requests
import pytest

from app.config import settings
from app.services.evaluation_service import EvaluationService, ProviderUnavailableError


class FakeSession:
    def __init__(self, posts, discovery=None):
        self.posts = iter(posts)
        self.discovery = discovery
        self.post_calls = []

    def get(self, *args, **kwargs):
        return self.discovery

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        result = next(self.posts)
        if isinstance(result, Exception):
            raise result
        return result


def response(status, body=None):
    result = Mock(status_code=status, ok=status < 400)
    result.json.return_value = body or {}
    return result


def success_response(text="real Gemini response"):
    return response(200, {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]})


def discovery(*models):
    return response(200, {"models": [{"name": f"models/{model}", "supportedGenerationMethods": ["generateContent"]} for model in models]})


def service(session, monkeypatch, fallbacks=(), retries=0):
    monkeypatch.setattr(settings, "gemini_model", "primary-model")
    monkeypatch.setattr(settings, "gemini_fallback_models", list(fallbacks))
    monkeypatch.setattr(settings, "gemini_retry_attempts", retries)
    monkeypatch.setattr(settings, "gemini_retry_backoff_seconds", 0)
    return EvaluationService("test-key", http_session=session, sleep=lambda _: None)


def test_successful_gemini_response(monkeypatch):
    session = FakeSession([success_response()])
    result = service(session, monkeypatch)._call_gemini_api("prompt", timeout=1)

    assert result == "real Gemini response"
    assert session.post_calls[0][0].endswith("/models/primary-model:generateContent")


def test_429_retries_with_bounded_attempts(monkeypatch):
    session = FakeSession([response(429), response(429)])
    provider = service(session, monkeypatch, retries=1)

    with pytest.raises(ProviderUnavailableError) as error:
        provider._call_gemini_api("prompt", timeout=1)

    assert error.value.failures[-1].category == "quota_or_rate_limit"
    assert len(session.post_calls) == 2


def test_503_retries_with_bounded_attempts(monkeypatch):
    session = FakeSession([response(503), response(503)])
    provider = service(session, monkeypatch, retries=1)

    with pytest.raises(ProviderUnavailableError) as error:
        provider._call_gemini_api("prompt", timeout=1)

    assert error.value.failures[-1].category == "overloaded"
    assert len(session.post_calls) == 2


def test_timeout_is_categorized_and_bounded(monkeypatch):
    session = FakeSession([requests.Timeout("timed out")])
    provider = service(session, monkeypatch)

    with pytest.raises(ProviderUnavailableError) as error:
        provider._call_gemini_api("prompt", timeout=1)

    assert error.value.failures[-1].category == "timeout"
    assert len(session.post_calls) == 1


def test_invalid_api_key_is_categorized_without_retry(monkeypatch):
    session = FakeSession([], discovery=response(401))
    provider = service(session, monkeypatch, fallbacks=("fallback-model",), retries=1)

    with pytest.raises(ProviderUnavailableError) as error:
        provider._call_gemini_api("prompt", timeout=1)

    assert error.value.failures[0].category == "invalid_api_key"
    assert not session.post_calls


def test_unavailable_primary_model_is_categorized(monkeypatch):
    session = FakeSession([response(404)])
    provider = service(session, monkeypatch)

    with pytest.raises(ProviderUnavailableError) as error:
        provider._call_gemini_api("prompt", timeout=1)

    assert error.value.failures[-1].category == "unavailable_model"


def test_fallback_requires_catalog_support_and_succeeds(monkeypatch):
    session = FakeSession(
        [success_response("fallback response")],
        discovery=discovery("fallback-model"),
    )
    provider = service(session, monkeypatch, fallbacks=("fallback-model",))

    assert provider._call_gemini_api("prompt", timeout=1) == "fallback response"
    assert session.post_calls[0][0].endswith("/models/fallback-model:generateContent")


def test_all_verified_models_unavailable_returns_provider_error(monkeypatch):
    session = FakeSession(
        [response(503), response(429)],
        discovery=discovery("primary-model", "fallback-model"),
    )
    provider = service(session, monkeypatch, fallbacks=("fallback-model",))

    with pytest.raises(ProviderUnavailableError) as error:
        provider._call_gemini_api("prompt", timeout=1)

    assert {failure.category for failure in error.value.failures} == {"overloaded", "quota_or_rate_limit"}
    assert len(session.post_calls) == 2
