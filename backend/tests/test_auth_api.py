"""Authentication and user-isolation smoke tests."""

from fastapi.testclient import TestClient
import uuid
from unittest.mock import patch

from app.main import app


def test_register_login_me_and_invalid_credentials():
    client = TestClient(app)
    email = "auth-suite@example.com"
    register = client.post("/api/auth/register", json={"name": "Auth Suite", "email": email, "password": "StrongPass123!"})
    assert register.status_code in (201, 409)
    login = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert client.post("/api/auth/login", json={"email": email, "password": "wrong"}).status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_user_owned_session_is_hidden_from_other_user():
    client = TestClient(app)
    users = []
    for index in (1, 2):
        email = f"owner-{index}-{uuid.uuid4().hex[:8]}@example.com"
        response = client.post("/api/auth/register", json={"name": f"Owner {index}", "email": email, "password": "StrongPass123!"})
        users.append(response.json()["access_token"])
    session = client.post(
        "/api/interview/start",
        headers={"Authorization": f"Bearer {users[0]}"},
        json={"job_role": "Python Developer", "skills": ["Python"], "total_questions": 1},
    )
    assert session.status_code == 200
    session_id = session.json()["session_id"]
    assert client.get(f"/api/interview/{session_id}", headers={"Authorization": f"Bearer {users[1]}"}).status_code == 404
    assert client.get(f"/api/interview/{session_id}").status_code == 401


def test_history_is_persisted_and_isolated_by_user_id():
    client = TestClient(app)
    tokens = []
    for index in (1, 2):
        email = f"history-owner-{index}-{uuid.uuid4().hex[:8]}@example.com"
        response = client.post("/api/auth/register", json={"name": f"History Owner {index}", "email": email, "password": "StrongPass123!"})
        tokens.append(response.json()["access_token"])

    session = client.post(
        "/api/interview/start",
        headers={"Authorization": f"Bearer {tokens[0]}"},
        json={"job_role": "Data Analyst", "skills": ["SQL"], "total_questions": 5},
    )
    assert session.status_code == 200
    session_id = session.json()["session_id"]

    restored = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tokens[0]}"})
    assert restored.status_code == 200
    first_history = client.get("/api/interview/history", headers={"Authorization": f"Bearer {tokens[0]}"})
    second_history = client.get("/api/interview/history", headers={"Authorization": f"Bearer {tokens[1]}"})
    assert first_history.status_code == 200
    assert [item["sessionId"] for item in first_history.json()] == [session_id]
    assert second_history.status_code == 200
    assert second_history.json() == []


def test_hint_is_question_specific_and_requires_session_ownership():
    client = TestClient(app)
    email = f"hint-{uuid.uuid4().hex}@example.com"
    auth = client.post(
        "/api/auth/register",
        json={"name": "Hint User", "email": email, "password": "StrongPass123!"},
    )
    headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}
    session = client.post(
        "/api/interview/start",
        headers=headers,
        json={"job_role": "Python Developer", "skills": ["Python"], "total_questions": 1},
    )
    assert session.status_code == 200
    session_data = session.json()
    hint = client.post(
        f"/api/interview/{session_data['session_id']}/hint",
        headers=headers,
        json={"question_id": session_data["current_question"]["question_id"]},
    )
    assert hint.status_code == 200
    assert hint.json()["hint"]
    assert session_data["current_question"]["question"] not in hint.json()["hint"]


def test_answer_handles_provider_unavailable_without_fake_scores():
    client = TestClient(app)
    email = f"answer-{uuid.uuid4().hex}@example.com"
    auth = client.post(
        "/api/auth/register",
        json={"name": "Answer User", "email": email, "password": "StrongPass123!"},
    )
    headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}
    session = client.post(
        "/api/interview/start",
        headers=headers,
        json={"job_role": "Python Developer", "skills": ["Python"], "total_questions": 2},
    ).json()
    with patch("app.services.evaluation_service.EvaluationService.evaluate_answer", side_effect=RuntimeError("provider unavailable")):
        response = client.post(
            "/api/interview/answer",
            headers=headers,
            json={
                "session_id": session["session_id"],
                "question_id": session["current_question"]["question_id"],
                "answer": "I will define the concept and explain it with a Python example.",
            },
        )
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "EVALUATION_UNAVAILABLE"
    assert detail["answer_saved"] is True
