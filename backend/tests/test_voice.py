"""Mocked checks for the protected GPT-Live session boundary."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import voice
from app.main import app


class FakeProviderResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


@pytest.fixture()
def isolated_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUIET_STEPS_DB_PATH", str(tmp_path / "voice_test.sqlite3"))


def test_voice_config_reports_only_safe_status_and_clamped_duration(
    isolated_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "fictional-test-key")
    monkeypatch.setenv("VOICE_LIVE_AUDIO_ENABLED", "true")
    monkeypatch.setenv("VOICE_MAX_SESSION_SECONDS", "999")
    monkeypatch.setenv("VOICE_LIVE_MODEL", "fictional-private-model-name")

    with TestClient(app) as client:
        response = client.get("/api/voice/config")

    assert response.status_code == 200
    assert response.json() == {"configured": True, "max_session_seconds": 300}
    assert "fictional-test-key" not in response.text
    assert "fictional-private-model-name" not in response.text


def test_voice_session_requires_an_explicit_live_audio_opt_in(
    isolated_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "fictional-test-key")
    calls = 0

    def should_not_call_provider(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("Provider should not be called")

    monkeypatch.setattr(voice, "_post_provider_session", should_not_call_provider)
    with TestClient(app) as client:
        response = client.post("/api/voice/sessions", json={"sdp": "v=0"})

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Voice is not configured. You can keep using text chat."
    )
    assert calls == 0


def test_voice_session_rejects_missing_or_browser_selected_configuration(
    isolated_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    calls = 0

    def should_not_call_provider(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("Provider should not be called")

    monkeypatch.setattr(voice, "_post_provider_session", should_not_call_provider)
    with TestClient(app) as client:
        missing_configuration = client.post("/api/voice/sessions", json={"sdp": "v=0"})
        browser_configuration = client.post(
            "/api/voice/sessions",
            json={"sdp": "v=0", "model": "browser-selected-model"},
        )

    assert missing_configuration.status_code == 503
    assert missing_configuration.json()["detail"] == (
        "Voice is not configured. You can keep using text chat."
    )
    assert browser_configuration.status_code == 422
    assert calls == 0


@pytest.mark.parametrize("offer", ["", "   ", "x" * (voice.MAX_SDP_CHARACTERS + 1)])
def test_voice_session_rejects_invalid_or_oversized_sdp_before_provider_call(
    isolated_database: None, monkeypatch: pytest.MonkeyPatch, offer: str
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "fictional-test-key")
    calls = 0

    def should_not_call_provider(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("Provider should not be called")

    monkeypatch.setattr(voice, "_post_provider_session", should_not_call_provider)
    with TestClient(app) as client:
        response = client.post("/api/voice/sessions", json={"sdp": offer})

    assert response.status_code == 422
    assert calls == 0


def test_voice_session_uses_server_owned_live_configuration_once(
    isolated_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "fictional-test-key")
    monkeypatch.setenv("VOICE_LIVE_AUDIO_ENABLED", "1")
    monkeypatch.setenv("VOICE_LIVE_MODEL", "gpt-live-1")
    monkeypatch.setenv("VOICE_BACKEND_MODEL", "gpt-6-luna")
    monkeypatch.setenv("VOICE_MAX_SESSION_SECONDS", "300")
    monkeypatch.setenv("VOICE_BACKEND_MAX_OUTPUT_TOKENS", "999")
    captured: dict[str, object] = {}

    def provider_response(settings: voice.VoiceSettings, payload: dict[str, object]):
        captured["settings"] = settings
        captured["payload"] = payload
        return FakeProviderResponse(
            201,
            {
                "session": {"id": "live_fictional_001", "unexpected": "not returned"},
                "transport": {"type": "webrtc", "sdp": "v=0\r\nanswer", "extra": True},
                "provider_debug": "not returned",
            },
        )

    monkeypatch.setattr(voice, "_post_provider_session", provider_response)
    with TestClient(app) as client:
        response = client.post("/api/voice/sessions", json={"sdp": "v=0\r\noffer"})

    assert response.status_code == 201
    assert response.json() == {
        "session_id": "live_fictional_001",
        "sdp_answer": "v=0\r\nanswer",
        "max_session_seconds": 300,
    }
    settings = captured["settings"]
    assert isinstance(settings, voice.VoiceSettings)
    assert settings.api_key == "fictional-test-key"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload == {
        "session": {
            "model": "gpt-live-1",
            "instructions": voice.LIVE_INSTRUCTIONS,
            "delegation": {
                "type": "responses",
                "responses": {
                    "model": "gpt-6-luna",
                    "instructions": voice.BACKEND_DELEGATION_INSTRUCTIONS,
                    "max_output_tokens": 300,
                    "tool_choice": "none",
                },
            },
            "client": {
                "data_channel": {
                    "allowed_client_events": [
                        "session.input_audio.mute",
                        "session.input_audio.unmute",
                    ],
                    "allowed_server_events": [
                        {"type": "session.started"},
                        {"type": "session.closed"},
                        {"type": "session.input_audio.muted"},
                        {"type": "session.input_audio.unmuted"},
                        {"type": "error"},
                    ],
                }
            },
            "store": False,
        },
        "transport": {"type": "webrtc", "sdp": "v=0\r\noffer"},
    }
    assert "tools" not in payload["session"]
    delegation = payload["session"]["delegation"]
    assert isinstance(delegation, dict)
    assert delegation["responses"]["tool_choice"] == "none"


def test_voice_prompt_roles_preserve_the_app_owned_safety_boundary() -> None:
    assert "The application—not you—controls" in voice.LIVE_INSTRUCTIONS
    assert "Crisis Support route" in voice.LIVE_INSTRUCTIONS
    assert "not therapy" in voice.LIVE_INSTRUCTIONS
    assert "Generate <|SpawnThinking|>" in voice.LIVE_INSTRUCTIONS
    assert "The only skill names you may suggest are Paced Breathing and STOP." in (
        voice.BACKEND_DELEGATION_INSTRUCTIONS
    )
    assert "cannot execute actions" not in voice.BACKEND_DELEGATION_INSTRUCTIONS
    assert "Never claim to have started, stopped, saved, or changed anything." in (
        voice.BACKEND_DELEGATION_INSTRUCTIONS
    )


@pytest.mark.parametrize(
    "provider_payload",
    [
        {"error": {"message": "fictional provider detail"}},
        {"session": {"id": "live_fictional_001"}, "transport": {"type": "webrtc"}},
        ValueError("fictional malformed response"),
    ],
)
def test_voice_session_sanitises_provider_and_malformed_response_failures(
    isolated_database: None, monkeypatch: pytest.MonkeyPatch, provider_payload: object
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "fictional-test-key")
    monkeypatch.setenv("VOICE_LIVE_AUDIO_ENABLED", "yes")

    def provider_response(*_args, **_kwargs):
        return FakeProviderResponse(500 if isinstance(provider_payload, dict) and "error" in provider_payload else 201, provider_payload)

    monkeypatch.setattr(voice, "_post_provider_session", provider_response)
    with TestClient(app) as client:
        response = client.post("/api/voice/sessions", json={"sdp": "v=0\r\noffer"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Voice is unavailable right now. You can keep using text chat."
    assert "fictional provider detail" not in response.text
    assert "fictional malformed response" not in response.text
    assert "fictional-test-key" not in response.text


def test_voice_endpoints_allow_the_local_vite_origin(isolated_database: None) -> None:
    origin = "http://127.0.0.1:5174"
    with TestClient(app) as client:
        response = client.options(
            "/api/voice/sessions",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
