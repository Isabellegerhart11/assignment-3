"""Bounded optional check-in adapter for the Quiet Steps prototype.

The caller may pass optional text to this module for the duration of one
request. It is never written to SQLite, returned to the client, or included
in errors. A live demo provider is treated as untrusted: application code
accepts only a fixed acknowledgement allowlist and a two-skill suggestion
allowlist, otherwise it uses the safe fallback.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Literal, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


Skill = Literal["paced_breathing", "stop"]
ReplySource = Literal["deterministic_mock", "live_validated", "fallback"]
ALLOWED_SKILLS: frozenset[str] = frozenset({"paced_breathing", "stop"})
SAFE_ACKNOWLEDGEMENTS: frozenset[str] = frozenset(
    {
        "Thanks for naming that.",
        "Thanks for sharing that.",
    }
)
FALLBACK_ACKNOWLEDGEMENT = "You can continue without sharing anything."


class CheckinServiceUnavailable(RuntimeError):
    """The optional service is unavailable or returned an unsafe response."""


@dataclass(frozen=True)
class BoundedReply:
    acknowledgement: str
    suggested_skill: Skill
    source: ReplySource


def _safe_suggestion_for(selected_skill: Skill) -> Skill:
    """Return an application-owned option, never an inference about the user."""
    return selected_skill


def _validate_model_output(output: object) -> tuple[str, Skill]:
    """Accept exactly the two approved response fields from an untrusted model."""
    if not isinstance(output, dict) or set(output) != {
        "acknowledgement",
        "suggested_skill",
    }:
        raise CheckinServiceUnavailable("Optional check-in returned an invalid format.")

    acknowledgement = output["acknowledgement"]
    suggested_skill = output["suggested_skill"]
    if not isinstance(acknowledgement, str) or acknowledgement not in SAFE_ACKNOWLEDGEMENTS:
        raise CheckinServiceUnavailable("Optional check-in returned an unapproved acknowledgement.")
    if not isinstance(suggested_skill, str) or suggested_skill not in ALLOWED_SKILLS:
        raise CheckinServiceUnavailable("Optional check-in returned an unapproved suggestion.")
    return acknowledgement, cast(Skill, suggested_skill)


def _live_timeout_seconds() -> float:
    try:
        configured = float(os.getenv("QUIET_STEPS_LIVE_MODEL_TIMEOUT_SECONDS", "4"))
    except ValueError:
        return 4.0
    return min(10.0, max(1.0, configured))


def _request_live_model(checkin_text: str) -> object:
    """Send text transiently to an explicitly configured fictional demo endpoint.

    This function must not log the request, response, or exception detail; any
    of those could contain free text. The provider's reply remains untrusted.
    """
    endpoint = os.getenv("QUIET_STEPS_LIVE_MODEL_URL", "").strip()
    if not endpoint or urlparse(endpoint).scheme != "https":
        raise CheckinServiceUnavailable("Optional live demo is not configured.")

    request_body = {
        "checkin": checkin_text,
        "required_output": {
            "acknowledgement": sorted(SAFE_ACKNOWLEDGEMENTS),
            "suggested_skill": sorted(ALLOWED_SKILLS),
        },
        "constraints": [
            "Return JSON only.",
            "Return exactly acknowledgement and suggested_skill.",
            "Do not diagnose, assess risk, offer therapy or medical advice, make treatment claims, or route crisis support.",
        ],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    token = os.getenv("QUIET_STEPS_LIVE_MODEL_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        endpoint,
        data=json.dumps(request_body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=_live_timeout_seconds()) as response:  # noqa: S310
            if response.status != 200:
                raise CheckinServiceUnavailable("Optional live demo did not respond successfully.")
            return json.loads(response.read().decode("utf-8"))
    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise CheckinServiceUnavailable("Optional live demo is unavailable.") from exc


def create_bounded_reply(checkin_text: str, selected_skill: Skill) -> BoundedReply:
    """Return a validated two-field reply for the optional check-in.

    ``mock`` is deterministic and is the default for routine local work and
    tests. ``live`` requires an explicit HTTPS demo endpoint. Any other mode,
    unavailable provider, malformed JSON, extra field, unapproved wording, or
    unapproved suggestion raises into the fallback path in the API endpoint.
    ``local`` remains a temporary alias for mock during this coursework update.
    """
    mode = os.getenv("QUIET_STEPS_CHECKIN_MODE", "mock").strip().lower()
    if mode in {"mock", "local"}:
        acknowledgement, suggested_skill = _validate_model_output(
            {
                "acknowledgement": "Thanks for naming that.",
                "suggested_skill": _safe_suggestion_for(selected_skill),
            }
        )
        return BoundedReply(
            acknowledgement=acknowledgement,
            suggested_skill=suggested_skill,
            source="deterministic_mock",
        )
    if mode == "live":
        acknowledgement, suggested_skill = _validate_model_output(
            _request_live_model(checkin_text)
        )
        return BoundedReply(
            acknowledgement=acknowledgement,
            suggested_skill=suggested_skill,
            source="live_validated",
        )
    if mode in {"failure", "unavailable"}:
        # Deliberate local test mode: no provider is called and the API takes
        # its normal calm fallback path.
        raise CheckinServiceUnavailable("Optional check-in failure mode is enabled.")
    raise CheckinServiceUnavailable("Optional check-in is unavailable.")


def fallback_reply(selected_skill: Skill) -> BoundedReply:
    return BoundedReply(
        acknowledgement=FALLBACK_ACKNOWLEDGEMENT,
        suggested_skill=_safe_suggestion_for(selected_skill),
        source="fallback",
    )
