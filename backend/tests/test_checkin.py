"""Tests for the application-enforced model output boundary."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import checkin
from app.main import app


def test_live_model_response_is_allowlist_validated(monkeypatch) -> None:
    observed: list[str] = []

    def fake_live_request(transient_text: str) -> object:
        observed.append(transient_text)
        return {
            "acknowledgement": "Thanks for sharing that.",
            "suggested_skill": "stop",
        }

    monkeypatch.setenv("QUIET_STEPS_CHECKIN_MODE", "live")
    monkeypatch.setattr(checkin, "_request_live_model", fake_live_request)

    reply = checkin.create_bounded_reply("Fictional transient fixture.", "paced_breathing")

    assert observed == ["Fictional transient fixture."]
    assert reply.acknowledgement == "Thanks for sharing that."
    assert reply.suggested_skill == "stop"
    assert reply.source == "live_validated"


def test_invalid_live_model_output_uses_endpoint_fallback(monkeypatch) -> None:
    def unsafe_live_request(_: str) -> object:
        return {
            "acknowledgement": "You should seek treatment immediately.",
            "suggested_skill": "paced_breathing",
            "crisis_route": "hidden extra field",
        }

    monkeypatch.setenv("QUIET_STEPS_CHECKIN_MODE", "live")
    monkeypatch.setattr(checkin, "_request_live_model", unsafe_live_request)

    with TestClient(app) as client:
        session_id = client.post("/api/sessions", json={"skill": "stop"}).json()["id"]
        response = client.post(
            f"/api/sessions/{session_id}/checkin",
            json={"text": "Fictional transient fixture."},
        )

    assert response.status_code == 200
    assert response.json() == {
        "acknowledgement": "You can continue without sharing anything.",
        "suggested_skill": "stop",
    }
