"""Focused tests for the secure InterviewIQ AI Coach endpoint."""

from unittest.mock import MagicMock, Mock, patch
import uuid

import requests
from fastapi.testclient import TestClient

from app.main import app
from app.services.evaluation_service import EvaluationService


def authenticated_client():
    client = TestClient(app)
    email = f"chat-{uuid.uuid4().hex}@example.com"
    auth = client.post(
        "/api/auth/register",
        json={"name": "Chat Test", "email": email, "password": "StrongPass123!"},
    )
    return client, {"Authorization": f"Bearer {auth.json()['access_token']}"}


def test_chat_returns_response_and_conversation_id():
    mock_langchain = MagicMock()
    mock_langchain.side_effect = [
        "Focus on joins and window functions.",
        "Next, practice aggregations.",
    ]
    client, headers = authenticated_client()

    with patch(
        "app.services.chat_service.ChatService._invoke_langchain",
        side_effect=mock_langchain,
    ):
        first = client.post(
            "/api/chat",
            headers=headers, json={"message": "How can I improve SQL?"},
        )
        conversation_id = first.json()["conversation_id"]
        second = client.post(
            "/api/chat",
                headers=headers, json={
                "message": "What should I practice next?",
                "conversation_id": conversation_id,
            },
        )

    assert first.status_code == 200
    assert first.json()["success"] is True
    assert first.json()["response"] == "Focus on joins and window functions."
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id
    assert mock_langchain.call_count == 2


def test_chat_hides_provider_failure():
    mock_langchain = MagicMock(side_effect=RuntimeError("secret internal provider details"))
    client, headers = authenticated_client()

    with patch(
        "app.services.chat_service.ChatService._invoke_langchain",
        side_effect=mock_langchain,
    ), patch(
        "app.services.chat_service.get_gemini_provider",
        side_effect=RuntimeError("secret internal provider details"),
    ):
        response = client.post("/api/chat", headers=headers, json={"message": "Hello"})

    assert response.status_code == 503
    assert "secret internal provider details" not in response.text
    assert "API key" not in response.text


def test_gemini_rest_response_keeps_all_text_parts():
    provider_response = Mock(ok=True, status_code=200)
    provider_response.json.return_value = {
        "candidates": [{
            "finishReason": "STOP",
            "content": {"parts": [{"text": "first "}, {"text": "second"}]},
        }],
    }
    provider_response.raise_for_status.return_value = None

    with patch(
        "app.services.gemini_provider.requests.post",
        return_value=provider_response,
    ) as post, patch(
        "app.services.gemini_provider.requests.get",
        return_value=Mock(
            status_code=200,
            json=lambda: {
                "models": [{
                    "name": "models/gemini-3.5-flash",
                    "supportedGenerationMethods": ["generateContent"],
                }]
            },
        ),
    ):
        result = EvaluationService("test-key")._call_gemini_api(
            "prompt", timeout=15, max_output_tokens=1024
        )

    assert result == "first second"
    assert post.call_args.kwargs["json"]["generationConfig"]["maxOutputTokens"] == 1024


def test_incomplete_response_retries_once_and_returns_only_complete_text():
    mock_langchain = MagicMock(side_effect=[
        {"text": "List comprehension is a concise way to create a new list from an...", "finish_reason": "MAX_TOKENS"},
        {"text": "List comprehension creates a list from an iterable. Example: squares = [x * x for x in range(5)]. This produces [0, 1, 4, 9, 16].", "finish_reason": "STOP"},
    ])

    client, headers = authenticated_client()
    with patch("app.services.chat_service.ChatService._invoke_langchain", mock_langchain):
        response = client.post(
            "/api/chat",
            headers=headers,
            json={"message": "Explain Python list comprehension with a simple example."},
        )

    assert response.status_code == 200
    assert response.json()["response"].endswith("[0, 1, 4, 9, 16].")
    assert "from an..." not in response.json()["response"]
    assert mock_langchain.call_count == 2


def test_second_incomplete_response_returns_clean_error_without_partial_text():
    mock_langchain = MagicMock(return_value={
        "text": "The answer starts but never finishes...",
        "finish_reason": "MAX_TOKENS",
    })

    client, headers = authenticated_client()
    with patch("app.services.chat_service.ChatService._invoke_langchain", mock_langchain):
        response = client.post("/api/chat", headers=headers, json={"message": "Explain Python lists"})

    assert response.status_code == 503
    assert "The answer starts" not in response.text
    assert mock_langchain.call_count == 2


def test_follow_up_preserves_conversation_history():
    calls = []

    def respond(history, context, mode, retry=False):
        calls.append(list(history))
        return {"text": "Here are three list-comprehension interview questions.", "finish_reason": "STOP"}

    with patch("app.services.chat_service.ChatService._invoke_langchain", side_effect=respond):
        client, headers = authenticated_client()
        first = client.post("/api/chat", headers=headers, json={"message": "Explain list comprehensions"})
        conversation_id = first.json()["conversation_id"]
        second = client.post(
            "/api/chat",
            headers=headers, json={"message": "Give me 3 questions about it", "conversation_id": conversation_id},
        )

    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id
    assert len(calls[1]) == 3
    assert calls[1][0]["text"] == "Explain list comprehensions"
    assert calls[1][1]["role"] == "assistant"


def test_provider_timeout_is_bounded_and_does_not_retry_at_chat_layer():
    mock_langchain = MagicMock(side_effect=requests.Timeout("timed out"))

    client, headers = authenticated_client()
    with patch("app.services.chat_service.ChatService._invoke_langchain", mock_langchain):
        response = client.post("/api/chat", headers=headers, json={"message": "hello"})

    assert response.status_code == 503
    assert mock_langchain.call_count == 1
