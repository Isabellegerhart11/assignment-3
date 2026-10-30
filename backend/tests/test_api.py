"""Integration coverage for the prototype's API and privacy boundaries."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

os.environ["QUIET_STEPS_DB_PATH"] = str(
    Path(tempfile.gettempdir()) / "quiet_steps_api_test.sqlite3"
)
os.environ["QUIET_STEPS_CHECKIN_MODE"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def fresh_client() -> TestClient:
    database = Path(os.environ["QUIET_STEPS_DB_PATH"])
    if database.exists():
        database.unlink()
    return TestClient(app)


def test_session_checkin_history_redacts_free_text() -> None:
    fictional_text = "Fictional check-in fixture that must not be saved."
    with fresh_client() as client:
        created = client.post("/api/sessions", json={"skill": "paced_breathing"})
        assert created.status_code == 201
        session_id = created.json()["id"]

        reply = client.post(
            f"/api/sessions/{session_id}/checkin",
            json={"text": fictional_text},
        )
        assert reply.status_code == 200
        assert reply.json() == {
            "acknowledgement": "Thanks for naming that.",
            "suggested_skill": "paced_breathing",
        }
        assert reply.json()["suggested_skill"] == "paced_breathing"

        detail = client.get(f"/api/sessions/{session_id}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["checkin_submitted"] is True
        assert body["conversation"][0]["content"] is None
        assert fictional_text not in str(body)
        assert body["conversation"][1]["content"] == "Thanks for naming that."
        assert body["conversation"][1]["suggested_skill"] in {
            "paced_breathing",
            "stop",
        }

    # The API view is not the only privacy boundary: inspect SQLite directly.
    with sqlite3.connect(os.environ["QUIET_STEPS_DB_PATH"]) as db:
        rows = db.execute(
            "SELECT content, suggested_skill FROM conversation_events ORDER BY id"
        ).fetchall()
    assert rows == [(None, None), ("Thanks for naming that.", "paced_breathing")]
    assert fictional_text not in str(rows)


def test_anonymous_profile_persists_only_preferences_and_can_be_cleared() -> None:
    with fresh_client() as client:
        default_profile = client.get("/api/profile")
        assert default_profile.status_code == 200
        assert default_profile.json() == {
            "preferred_skill": None,
            "motion_preference": "system",
            "chat_personalization_enabled": False,
            "updated_at": default_profile.json()["updated_at"],
        }

        updated = client.put(
            "/api/profile",
            json={
                "preferred_skill": "stop",
                "motion_preference": "reduce",
                "chat_personalization_enabled": True,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["preferred_skill"] == "stop"
        assert updated.json()["motion_preference"] == "reduce"
        assert updated.json()["chat_personalization_enabled"] is True

        unexpected_data = client.put(
            "/api/profile",
            json={
                "preferred_skill": "stop",
                "motion_preference": "reduce",
                "chat_personalization_enabled": True,
                "reflection_answer": "Fictional sensitive value",
            },
        )
        assert unexpected_data.status_code == 422

    with TestClient(app) as restarted_app:
        restored = restarted_app.get("/api/profile")
        assert restored.status_code == 200
        assert restored.json()["preferred_skill"] == "stop"
        assert restored.json()["motion_preference"] == "reduce"
        assert restored.json()["chat_personalization_enabled"] is True

        cleared = restarted_app.delete("/api/profile")
        assert cleared.status_code == 200
        assert cleared.json()["preferred_skill"] is None
        assert cleared.json()["motion_preference"] == "system"
        assert cleared.json()["chat_personalization_enabled"] is False

    with sqlite3.connect(os.environ["QUIET_STEPS_DB_PATH"]) as db:
        columns = [row[1] for row in db.execute("PRAGMA table_info(local_profile)")]
    assert columns == [
        "id",
        "preferred_skill",
        "motion_preference",
        "chat_personalization_enabled",
        "updated_at",
    ]


def test_optional_daily_mood_is_editable_and_contains_no_free_text() -> None:
    with fresh_client() as client:
        empty = client.get("/api/moods?month=2026-10")
        assert empty.status_code == 200
        assert empty.json() == []

        unexpected_content = client.put(
            "/api/moods/2026-10-22",
            json={"mood": "good", "note": "Fictional text that must be rejected."},
        )
        assert unexpected_content.status_code == 422

        first_choice = client.put(
            "/api/moods/2026-10-22",
            json={"mood": "low"},
        )
        assert first_choice.status_code == 200
        assert first_choice.json()["day"] == "2026-10-22"
        assert first_choice.json()["mood"] == "low"

    with TestClient(app) as restarted_app:
        restored = restarted_app.get("/api/moods?month=2026-10")
        assert restored.status_code == 200
        assert [entry["mood"] for entry in restored.json()] == ["low"]

        revised_choice = restarted_app.put(
            "/api/moods/2026-10-22",
            json={"mood": "good"},
        )
        assert revised_choice.status_code == 200
        assert revised_choice.json()["mood"] == "good"

        month_entries = restarted_app.get("/api/moods?month=2026-10")
        assert month_entries.status_code == 200
        assert [entry["mood"] for entry in month_entries.json()] == ["good"]

        removed = restarted_app.delete("/api/moods/2026-10-22")
        assert removed.status_code == 204
        assert restarted_app.get("/api/moods?month=2026-10").json() == []

    with sqlite3.connect(os.environ["QUIET_STEPS_DB_PATH"]) as db:
        columns = [row[1] for row in db.execute("PRAGMA table_info(mood_entries)")]
    assert columns == ["day", "mood", "updated_at"]


def test_duration_is_limited_to_ninety_seconds() -> None:
    with fresh_client() as client:
        session_id = client.post("/api/sessions", json={"skill": "stop"}).json()["id"]
        rejected = client.post(
            f"/api/sessions/{session_id}/finish",
            json={"status": "completed", "seconds_completed": 91},
        )
        assert rejected.status_code == 422

        saved = client.post(
            f"/api/sessions/{session_id}/finish",
            json={"status": "completed", "seconds_completed": 60},
        )
        assert saved.status_code == 200
        assert saved.json()["seconds_completed"] == 60


def test_deliberate_failure_mode_uses_safe_fallback(monkeypatch) -> None:
    monkeypatch.setenv("QUIET_STEPS_CHECKIN_MODE", "failure")
    with fresh_client() as client:
        session_id = client.post("/api/sessions", json={"skill": "stop"}).json()["id"]
        response = client.post(
            f"/api/sessions/{session_id}/checkin",
            json={"text": "Fictional optional check-in."},
        )
        assert response.status_code == 200
        assert response.json() == {
            "acknowledgement": "You can continue without sharing anything.",
            "suggested_skill": "stop",
        }


@pytest.mark.parametrize("skill", ["paced_breathing", "stop"])
def test_each_skill_can_be_left_without_a_checkin(skill: str) -> None:
    with fresh_client() as client:
        session_id = client.post("/api/sessions", json={"skill": skill}).json()["id"]
        exited = client.post(
            f"/api/sessions/{session_id}/finish",
            json={"status": "left", "seconds_completed": 0},
        )

        assert exited.status_code == 200
        assert exited.json()["status"] == "left"
        assert exited.json()["checkin_submitted"] is False

        history = client.get("/api/sessions")
        assert history.status_code == 200
        assert history.json()[0]["id"] == session_id
        assert history.json()[0]["skill"] == skill
        assert history.json()[0]["status"] == "left"


def test_optional_checkin_can_be_skipped_without_conversation_storage() -> None:
    with fresh_client() as client:
        session_id = client.post(
            "/api/sessions", json={"skill": "paced_breathing"}
        ).json()["id"]
        completed = client.post(
            f"/api/sessions/{session_id}/finish",
            json={"status": "completed", "seconds_completed": 60},
        )

        assert completed.status_code == 200
        detail = client.get(f"/api/sessions/{session_id}").json()
        assert detail["checkin_submitted"] is False
        assert detail["conversation"] == []


def test_session_history_survives_an_application_restart() -> None:
    with fresh_client() as first_run:
        session_id = first_run.post(
            "/api/sessions", json={"skill": "paced_breathing"}
        ).json()["id"]
        checkin = first_run.post(
            f"/api/sessions/{session_id}/checkin",
            json={"text": "Fictional fixture text must not survive a restart."},
        )
        assert checkin.status_code == 200
        first_run.post(
            f"/api/sessions/{session_id}/finish",
            json={"status": "completed", "seconds_completed": 60},
        )

    # A new TestClient runs the FastAPI lifespan again against the same SQLite file.
    with TestClient(app) as restarted_app:
        restored = restarted_app.get(f"/api/sessions/{session_id}")
        assert restored.status_code == 200
        body = restored.json()
        assert body["status"] == "completed"
        assert body["seconds_completed"] == 60
        assert body["conversation"][0]["content"] is None
        assert "Fictional fixture text" not in str(body)
