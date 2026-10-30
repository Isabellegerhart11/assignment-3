"""Deterministic coverage for the SQL RAG chatbot and its OpenAI boundary."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import rag
from app.main import app


@pytest.fixture()
def database_path(monkeypatch, tmp_path: Path) -> Path:
    path = tmp_path / "fictional_rag.sqlite3"
    monkeypatch.setenv("QUIET_STEPS_DB_PATH", str(path))
    monkeypatch.setenv("QUIET_STEPS_RAG_MODE", "mock")
    return path


def create_conversation(client: TestClient) -> str:
    response = client.post("/api/conversations", json={})
    assert response.status_code == 201
    return response.json()["id"]


def send_fictional_message(client: TestClient, conversation_id: str, suffix: str = "001"):
    return client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={
            "content": "In this fictional scenario, what short skill is available?",
            "client_message_id": f"fictional-client-message-{suffix}",
        },
    )


def test_default_cors_allows_vite_fallback_port() -> None:
    """Vite uses 5174 when the default 5173 port is occupied."""
    origin = "http://127.0.0.1:5174"
    with TestClient(app) as client:
        response = client.options(
            "/api/conversations",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
            },
        )
        profile_response = client.options(
            "/api/profile",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "PUT",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert profile_response.status_code == 200
    assert profile_response.headers["access-control-allow-origin"] == origin
    assert "PUT" in profile_response.headers["access-control-allow-methods"]


def test_mock_rag_saves_ordered_messages_and_readonly_retrieval(database_path: Path) -> None:
    with TestClient(app) as client:
        conversation_id = create_conversation(client)
        response = send_fictional_message(client, conversation_id)

        assert response.status_code == 201
        body = response.json()
        assert body["id"] == conversation_id
        assert [message["role"] for message in body["messages"]] == ["user", "assistant"]
        assert all(message["status"] == "complete" for message in body["messages"])
        assert body["messages"][1]["suggested_skill"] == "paced_breathing"
        assert body["messages"][1]["supporting_message_ids"] == [body["messages"][0]["id"]]

        duplicate = send_fictional_message(client, conversation_id)
        assert duplicate.status_code == 409

    with sqlite3.connect(database_path) as db:
        request = db.execute(
            "SELECT planned_sql, retrieval_status, retrieved_message_ids FROM rag_requests"
        ).fetchone()
        message_rows = db.execute(
            "SELECT role, status FROM messages ORDER BY rowid"
        ).fetchall()

    assert request is not None
    assert request[0] == rag.RECENT_MESSAGES_SQL
    assert request[1] == "completed"
    assert json.loads(request[2])
    assert message_rows == [("user", "complete"), ("assistant", "complete")]


def test_short_greeting_uses_the_fixed_opening_reply(database_path: Path) -> None:
    with TestClient(app) as client:
        conversation_id = create_conversation(client)
        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={
                "content": "Hi there!",
                "client_message_id": "fictional-greeting-message-001",
            },
        )

    assert response.status_code == 201
    assistant_message = response.json()["messages"][1]
    assert assistant_message["content"] == "hi there! what would you like to work on today?"
    assert assistant_message["suggested_skill"] == "paced_breathing"


def test_transient_reflection_selects_a_practice_without_becoming_chat_history(
    database_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("QUIET_STEPS_RAG_MODE", "failure")
    with TestClient(app) as client:
        conversation_id = create_conversation(client)
        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={
                "content": "Which practice could I start with?",
                "client_message_id": "fictional-reflection-message-001",
                "reflection": {
                    "body_tension": "Very much",
                    "on_edge": "Mostly",
                },
            },
        )

    assert response.status_code == 201
    assistant_message = response.json()["messages"][1]
    assert assistant_message["content"] == (
        "Thanks for sharing your optional reflection. You can use the suggested "
        "practice or choose another activity."
    )
    assert assistant_message["suggested_skill"] == "paced_breathing"

    with sqlite3.connect(database_path) as db:
        saved_content = [row[0] for row in db.execute("SELECT content FROM messages")]
        retrieval = db.execute(
            "SELECT planned_sql, retrieved_message_ids FROM rag_requests"
        ).fetchone()

    assert all("Very much" not in content and "Mostly" not in content for content in saved_content)
    assert retrieval is not None
    assert retrieval[0] == rag.RECENT_MESSAGES_SQL


def test_transient_reflection_rejects_unknown_response_values(database_path: Path) -> None:
    with TestClient(app) as client:
        conversation_id = create_conversation(client)
        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={
                "content": "Which practice could I start with?",
                "client_message_id": "fictional-invalid-reflection-message-001",
                "reflection": {"body_tension": "Completely"},
            },
        )
        detail = client.get(f"/api/conversations/{conversation_id}")

    assert response.status_code == 422
    assert detail.status_code == 200
    assert detail.json()["messages"] == []


def test_chat_receives_only_opted_in_non_sensitive_practice_context(
    database_path: Path, monkeypatch
) -> None:
    observed: dict[str, object] = {}

    def captured_reply(
        _question: str,
        records: list[rag.RetrievedMessage],
        practice_context: rag.PracticeContext | None = None,
    ) -> rag.GroundedReply:
        observed["context"] = practice_context
        return rag.GroundedReply(
            reply="A fictional, neutral reply.",
            suggested_skill="stop",
            supporting_message_ids=[record.id for record in records],
            source="deterministic_mock",
        )

    monkeypatch.setattr("app.main.create_grounded_reply", captured_reply)
    with TestClient(app) as client:
        mood = client.put(
            "/api/moods/2026-10-22",
            json={"mood": "very_low"},
        )
        assert mood.status_code == 200
        profile = client.put(
            "/api/profile",
            json={
                "preferred_skill": "stop",
                "motion_preference": "reduce",
                "chat_personalization_enabled": True,
            },
        )
        assert profile.status_code == 200
        session_id = client.post("/api/sessions", json={"skill": "stop"}).json()["id"]
        assert client.post(
            f"/api/sessions/{session_id}/finish",
            json={"status": "completed", "seconds_completed": 0},
        ).status_code == 200
        conversation_id = create_conversation(client)
        response = send_fictional_message(client, conversation_id, "profile-context")

    assert response.status_code == 201
    context = observed["context"]
    assert isinstance(context, rag.PracticeContext)
    assert context.preferred_skill == "stop"
    assert context.last_completed_skill == "stop"
    assert context.completed_practice_counts == {"stop": 1}
    assert context.as_model_context() == {
        "preferred_skill": "stop",
        "last_completed_skill": "stop",
        "completed_practice_counts": {"stop": 1},
    }
    body = response.json()
    assert body["personalization"] == {
        "enabled": True,
        "preferred_skill": "stop",
        "last_completed_skill": "stop",
        "completed_practice_counts": {"stop": 1},
    }


def test_rag_history_survives_a_new_fastapi_client(database_path: Path) -> None:
    with TestClient(app) as first_run:
        conversation_id = create_conversation(first_run)
        assert send_fictional_message(first_run, conversation_id, "002").status_code == 201

    with TestClient(app) as restarted:
        restored = restarted.get(f"/api/conversations/{conversation_id}")
        assert restored.status_code == 200
        assert len(restored.json()["messages"]) == 2
        assert restored.json()["messages"][0]["content"].startswith("In this fictional")


def test_provider_failure_marks_the_saved_user_message_failed(database_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QUIET_STEPS_RAG_MODE", "failure")
    with TestClient(app) as client:
        conversation_id = create_conversation(client)
        response = send_fictional_message(client, conversation_id, "003")
        assert response.status_code == 503

        detail = client.get(f"/api/conversations/{conversation_id}")
        assert detail.status_code == 200
        assert [(item["role"], item["status"]) for item in detail.json()["messages"]] == [
            ("user", "failed")
        ]

    with sqlite3.connect(database_path) as db:
        request_status = db.execute("SELECT retrieval_status FROM rag_requests").fetchone()
    assert request_status == ("provider_failed",)


def test_unsafe_retrieval_plan_is_rejected_without_an_assistant_message(
    database_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("QUIET_STEPS_RAG_MODE", "openai")

    def unsafe_plan(_: str) -> rag.RetrievalPlan:
        raise rag.UnsafeRetrievalPlan("fictional unsafe plan")

    monkeypatch.setattr("app.main.create_retrieval_plan", unsafe_plan)
    with TestClient(app) as client:
        conversation_id = create_conversation(client)
        response = send_fictional_message(client, conversation_id, "004")

        assert response.status_code == 502
        detail = client.get(f"/api/conversations/{conversation_id}").json()
        assert [(item["role"], item["status"]) for item in detail["messages"]] == [
            ("user", "failed")
        ]


def test_openai_retrieval_request_uses_responses_api_structured_output(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        status = 200

        def read(self) -> bytes:
            return json.dumps(
                {
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(
                                        {"sql": rag.RECENT_MESSAGES_SQL, "limit": 6}
                                    ),
                                }
                            ],
                        }
                    ],
                }
            ).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

    def fake_urlopen(request, timeout, context):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        captured["context"] = context
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setenv("QUIET_STEPS_RAG_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "fictional-test-key")
    monkeypatch.setenv("QUIET_STEPS_OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setattr(rag, "urlopen", fake_urlopen)

    plan = rag.create_retrieval_plan("A fictional question")

    assert plan.sql == rag.RECENT_MESSAGES_SQL
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["authorization"] == "Bearer fictional-test-key"
    assert captured["context"] is rag.OPENAI_SSL_CONTEXT
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "gpt-4o-mini"
    assert payload["store"] is False
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True
