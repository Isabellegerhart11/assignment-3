"""Local API for the Quiet Steps coursework skills-practice prototype."""

from __future__ import annotations

import os
import json
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from .checkin import (
    CheckinServiceUnavailable,
    create_bounded_reply,
    fallback_reply,
)
from .database import connection, initialise_database
from .rag import (
    GroundedReply,
    PracticeContext,
    RAGServiceUnavailable,
    RetrievedMessage,
    TransientReflectionContext,
    UnsafeRetrievalPlan,
    create_grounded_reply,
    create_retrieval_plan,
)
from .voice import (
    MAX_SDP_CHARACTERS,
    VoiceConfigurationUnavailable,
    VoiceProviderUnavailable,
    create_voice_session,
    public_voice_configuration,
)

Skill = Literal["paced_breathing", "stop"]
SessionStatus = Literal["active", "completed", "left"]
MotionPreference = Literal["system", "reduce", "standard"]
Mood = Literal["very_low", "low", "in_between", "good", "very_good"]
ReflectionResponse = Literal["Not at all", "A little", "Mostly", "Very much"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialise_database()
    yield


app = FastAPI(
    title="Quiet Steps API",
    version="0.1.0",
    description=(
        "Local API for a coursework skills-practice prototype. "
        "It is not therapy, diagnosis, monitoring, or emergency care."
    ),
    lifespan=lifespan,
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "QUIET_STEPS_CORS_ORIGINS",
        # Vite starts at 5173 and increments when that port is already in use.
        # Keep the common local fallback ports working without requiring a
        # frontend restart or a user-supplied CORS setting.
        (
            "http://127.0.0.1:5173,http://localhost:5173,"
            "http://127.0.0.1:5174,http://localhost:5174,"
            "http://127.0.0.1:5175,http://localhost:5175"
        ),
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill: Skill


class SessionFinish(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["completed", "left"]
    seconds_completed: Annotated[int, Field(ge=0, le=90)]


class CheckinCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Annotated[str, Field(min_length=1, max_length=280)]


class VoiceConfiguration(BaseModel):
    """Public configuration that never includes a secret or provider details."""

    configured: bool
    max_session_seconds: int


class VoiceSessionCreate(BaseModel):
    """One browser-generated SDP offer; all policy stays server-owned."""

    model_config = ConfigDict(extra="forbid")
    sdp: Annotated[str, Field(min_length=1, max_length=MAX_SDP_CHARACTERS)]


class VoiceSessionResponse(BaseModel):
    session_id: str
    sdp_answer: str
    max_session_seconds: int


class ConversationEvent(BaseModel):
    role: Literal["user_event", "assistant"]
    event_type: Literal["checkin_submitted", "bounded_acknowledgement"]
    content: str | None = None
    suggested_skill: Skill | None = None
    created_at: str


class SessionSummary(BaseModel):
    id: str
    skill: Skill
    started_at: str
    updated_at: str
    status: SessionStatus
    seconds_completed: int
    checkin_submitted: bool


class SessionDetail(SessionSummary):
    conversation: list[ConversationEvent]


class CheckinResponse(BaseModel):
    acknowledgement: str
    suggested_skill: Skill


class ProfileSettings(BaseModel):
    """Anonymous, non-clinical preferences for this local app installation."""

    preferred_skill: Skill | None
    motion_preference: MotionPreference
    chat_personalization_enabled: bool
    updated_at: str


class ProfileSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_skill: Skill | None
    motion_preference: MotionPreference
    chat_personalization_enabled: bool


class MoodEntry(BaseModel):
    day: str
    mood: Mood
    updated_at: str


class MoodEntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mood: Mood


class ChatPersonalization(BaseModel):
    enabled: bool
    preferred_skill: Skill | None = None
    last_completed_skill: Skill | None = None
    completed_practice_counts: dict[Skill, int] = Field(default_factory=dict)


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TransientReflectionInput(BaseModel):
    """Optional, one-request inputs for an app-owned practice suggestion."""

    model_config = ConfigDict(extra="forbid")

    body_tension: ReflectionResponse | None = None
    thoughts_calm: ReflectionResponse | None = None
    at_ease: ReflectionResponse | None = None
    on_edge: ReflectionResponse | None = None


class ConversationMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: Annotated[str, Field(min_length=1, max_length=800)]
    client_message_id: Annotated[str, Field(min_length=8, max_length=100)]
    reflection: TransientReflectionInput | None = None


class ChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    status: Literal["pending", "complete", "failed"]
    suggested_skill: Skill | None = None
    supporting_message_ids: list[str]
    created_at: str


class ConversationSummary(BaseModel):
    id: str
    created_at: str
    updated_at: str
    message_count: int


class ConversationDetail(ConversationSummary):
    messages: list[ChatMessage]
    personalization: ChatPersonalization


def to_summary(row: sqlite3.Row) -> SessionSummary:
    return SessionSummary(
        id=row["id"],
        skill=row["skill"],
        started_at=row["started_at"],
        updated_at=row["updated_at"],
        status=row["status"],
        seconds_completed=row["seconds_completed"],
        checkin_submitted=bool(row["checkin_submitted"]),
    )


def find_session_or_404(db: sqlite3.Connection, session_id: str) -> sqlite3.Row:
    row = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="That practice session was not found.")
    return row


def find_conversation_or_404(
    db: sqlite3.Connection, conversation_id: str
) -> sqlite3.Row:
    row = db.execute(
        "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="That saved chat was not found.")
    return row


def to_conversation_summary(row: sqlite3.Row) -> ConversationSummary:
    return ConversationSummary(
        id=row["id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        message_count=row["message_count"],
    )


def load_profile_settings(db: sqlite3.Connection) -> ProfileSettings:
    """Return the single anonymous local profile, creating default settings if needed."""
    db.execute("INSERT OR IGNORE INTO local_profile (id) VALUES (1)")
    row = db.execute("SELECT * FROM local_profile WHERE id = 1").fetchone()
    if row is None:  # Defensive: the default row could not be re-read.
        raise sqlite3.DatabaseError("Profile settings are unavailable.")
    return ProfileSettings(
        preferred_skill=row["preferred_skill"],
        motion_preference=row["motion_preference"],
        chat_personalization_enabled=bool(row["chat_personalization_enabled"]),
        updated_at=row["updated_at"],
    )


def load_chat_personalization(db: sqlite3.Connection) -> ChatPersonalization:
    """Build the allowlisted summary used only when chat personalization is on."""
    profile = load_profile_settings(db)
    if not profile.chat_personalization_enabled:
        return ChatPersonalization(enabled=False)

    last_row = db.execute(
        """
        SELECT skill FROM sessions
        WHERE status = 'completed'
        ORDER BY updated_at DESC
        LIMIT 1
        """
    ).fetchone()
    count_rows = db.execute(
        """
        SELECT skill, COUNT(*) AS practice_count FROM sessions
        WHERE status = 'completed'
        GROUP BY skill
        """
    ).fetchall()
    counts: dict[Skill, int] = {
        row["skill"]: row["practice_count"] for row in count_rows
    }
    return ChatPersonalization(
        enabled=True,
        preferred_skill=profile.preferred_skill,
        last_completed_skill=last_row["skill"] if last_row else None,
        completed_practice_counts=counts,
    )


def to_practice_context(summary: ChatPersonalization) -> PracticeContext:
    return PracticeContext(
        preferred_skill=summary.preferred_skill,
        last_completed_skill=summary.last_completed_skill,
        completed_practice_counts=summary.completed_practice_counts,
    )


def to_transient_reflection_context(
    reflection: TransientReflectionInput | None,
) -> TransientReflectionContext | None:
    """Keep selected reflection answers out of database and RAG-model context."""
    if reflection is None:
        return None
    answers = {
        name: value
        for name, value in {
            "body_tension": reflection.body_tension,
            "thoughts_calm": reflection.thoughts_calm,
            "at_ease": reflection.at_ease,
            "on_edge": reflection.on_edge,
        }.items()
        if value is not None
    }
    return TransientReflectionContext(answers=answers) if answers else None


def calendar_day_or_422(day_value: str) -> str:
    """Validate a date-only local reflection key without inferring location."""
    try:
        parsed = date.fromisoformat(day_value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Use a calendar date in YYYY-MM-DD format.") from exc
    if parsed.isoformat() != day_value:
        raise HTTPException(status_code=422, detail="Use a calendar date in YYYY-MM-DD format.")
    return parsed.isoformat()


def month_bounds_or_422(month_value: str) -> tuple[str, str]:
    """Return inclusive/exclusive date bounds for the visible calendar month."""
    try:
        first = date.fromisoformat(f"{month_value}-01")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Use a month in YYYY-MM format.") from exc
    if len(month_value) != 7 or first.strftime("%Y-%m") != month_value:
        raise HTTPException(status_code=422, detail="Use a month in YYYY-MM format.")
    if first.month == 12:
        next_month = date(first.year + 1, 1, 1)
    else:
        next_month = date(first.year, first.month + 1, 1)
    return first.isoformat(), next_month.isoformat()


def load_conversation_detail(
    db: sqlite3.Connection, conversation_id: str
) -> ConversationDetail:
    conversation = find_conversation_or_404(db, conversation_id)
    message_rows = db.execute(
        """
        SELECT id, role, content, status, suggested_skill, supporting_message_ids, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY rowid ASC
        """,
        (conversation_id,),
    ).fetchall()
    messages = []
    for row in message_rows:
        try:
            supporting_ids = json.loads(row["supporting_message_ids"])
        except (TypeError, json.JSONDecodeError):
            supporting_ids = []
        messages.append(
            ChatMessage(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                status=row["status"],
                suggested_skill=row["suggested_skill"],
                supporting_message_ids=supporting_ids
                if isinstance(supporting_ids, list)
                else [],
                created_at=row["created_at"],
            )
        )
    return ConversationDetail(
        id=conversation["id"],
        created_at=conversation["created_at"],
        updated_at=conversation["updated_at"],
        message_count=len(messages),
        messages=messages,
        personalization=load_chat_personalization(db),
    )


def mark_rag_failure(
    *,
    conversation_id: str,
    user_message_id: str,
    planned_sql: str | None,
    status: Literal["rejected", "provider_failed"],
    retrieved_message_ids: list[str] | None = None,
) -> None:
    """Persist the truthful failed state without fabricating an assistant reply."""
    timestamp = now()
    with connection() as db:
        db.execute(
            "UPDATE messages SET status = 'failed' WHERE id = ?",
            (user_message_id,),
        )
        db.execute(
            """
            INSERT INTO rag_requests
                (id, conversation_id, user_message_id, planned_sql, retrieval_status,
                 retrieved_message_ids, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                conversation_id,
                user_message_id,
                planned_sql,
                status,
                json.dumps(retrieved_message_ids or []),
                timestamp,
                timestamp,
            ),
        )
        db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (timestamp, conversation_id),
        )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "prototype": "quiet-steps"}


@app.get("/api/voice/config", response_model=VoiceConfiguration)
def get_voice_configuration() -> VoiceConfiguration:
    """Report only whether local voice setup is present and its duration cap."""

    configured, max_session_seconds = public_voice_configuration()
    return VoiceConfiguration(
        configured=configured,
        max_session_seconds=max_session_seconds,
    )


@app.post(
    "/api/voice/sessions",
    response_model=VoiceSessionResponse,
    status_code=201,
)
def start_voice_session(payload: VoiceSessionCreate) -> VoiceSessionResponse:
    """Exchange a browser SDP offer for a server-created GPT-Live session."""

    if not payload.sdp.strip():
        raise HTTPException(status_code=422, detail="An SDP offer is required.")
    try:
        result = create_voice_session(payload.sdp)
    except VoiceConfigurationUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="Voice is not configured. You can keep using text chat.",
        ) from exc
    except (ValueError, VoiceProviderUnavailable) as exc:
        raise HTTPException(
            status_code=503,
            detail="Voice is unavailable right now. You can keep using text chat.",
        ) from exc
    return VoiceSessionResponse(
        session_id=result.session_id,
        sdp_answer=result.sdp_answer,
        max_session_seconds=result.max_session_seconds,
    )


@app.get("/api/profile", response_model=ProfileSettings)
def get_profile() -> ProfileSettings:
    try:
        with connection() as db:
            return load_profile_settings(db)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Profile preferences are unavailable.") from exc


@app.put("/api/profile", response_model=ProfileSettings)
def update_profile(payload: ProfileSettingsUpdate) -> ProfileSettings:
    """Save only voluntary, non-identifying interface/practice preferences."""
    timestamp = now()
    try:
        with connection() as db:
            db.execute("INSERT OR IGNORE INTO local_profile (id) VALUES (1)")
            db.execute(
                """
                UPDATE local_profile
                SET preferred_skill = ?, motion_preference = ?,
                    chat_personalization_enabled = ?, updated_at = ?
                WHERE id = 1
                """,
                (
                    payload.preferred_skill,
                    payload.motion_preference,
                    int(payload.chat_personalization_enabled),
                    timestamp,
                ),
            )
            return load_profile_settings(db)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Profile preferences could not be saved.") from exc


@app.delete("/api/profile", response_model=ProfileSettings)
def clear_profile() -> ProfileSettings:
    """Reset the accountless profile without touching session or chat history."""
    timestamp = now()
    try:
        with connection() as db:
            db.execute("INSERT OR IGNORE INTO local_profile (id) VALUES (1)")
            db.execute(
                """
                UPDATE local_profile
                SET preferred_skill = NULL, motion_preference = 'system',
                    chat_personalization_enabled = 0, updated_at = ?
                WHERE id = 1
                """,
                (timestamp,),
            )
            return load_profile_settings(db)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Profile preferences could not be cleared.") from exc


@app.get("/api/moods", response_model=list[MoodEntry])
def list_moods(
    month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")],
) -> list[MoodEntry]:
    start_day, next_month = month_bounds_or_422(month)
    try:
        with connection() as db:
            rows = db.execute(
                """
                SELECT day, mood, updated_at FROM mood_entries
                WHERE day >= ? AND day < ?
                ORDER BY day ASC
                """,
                (start_day, next_month),
            ).fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Daily reflections are unavailable.") from exc
    return [MoodEntry(**dict(row)) for row in rows]


@app.put("/api/moods/{day}", response_model=MoodEntry)
def save_mood(day: str, payload: MoodEntryUpdate) -> MoodEntry:
    """Save one explicit mood label for a selected day; no free text is accepted."""
    calendar_day = calendar_day_or_422(day)
    timestamp = now()
    try:
        with connection() as db:
            db.execute(
                """
                INSERT INTO mood_entries (day, mood, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(day) DO UPDATE SET mood = excluded.mood, updated_at = excluded.updated_at
                """,
                (calendar_day, payload.mood, timestamp),
            )
            row = db.execute(
                "SELECT day, mood, updated_at FROM mood_entries WHERE day = ?",
                (calendar_day,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="This daily reflection could not be saved.") from exc
    if row is None:
        raise HTTPException(status_code=503, detail="This daily reflection could not be saved.")
    return MoodEntry(**dict(row))


@app.delete("/api/moods/{day}", status_code=204)
def remove_mood(day: str) -> Response:
    calendar_day = calendar_day_or_422(day)
    try:
        with connection() as db:
            db.execute("DELETE FROM mood_entries WHERE day = ?", (calendar_day,))
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="This daily reflection could not be cleared.") from exc
    return Response(status_code=204)


@app.delete("/api/moods", status_code=204)
def clear_moods() -> Response:
    try:
        with connection() as db:
            db.execute("DELETE FROM mood_entries")
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Daily reflections could not be cleared.") from exc
    return Response(status_code=204)


@app.post(
    "/api/conversations",
    response_model=ConversationSummary,
    status_code=201,
)
def create_conversation(_: ConversationCreate) -> ConversationSummary:
    """Create one local conversation before the fictional user sends a message."""
    conversation_id = str(uuid.uuid4())
    timestamp = now()
    try:
        with connection() as db:
            db.execute(
                "INSERT INTO conversations (id, created_at, updated_at) VALUES (?, ?, ?)",
                (conversation_id, timestamp, timestamp),
            )
            row = db.execute(
                """
                SELECT conversations.*, 0 AS message_count
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Local chat history is unavailable.") from exc
    if row is None:  # Defensive: the insert succeeded but could not be re-read.
        raise HTTPException(status_code=503, detail="Local chat history is unavailable.")
    return to_conversation_summary(row)


@app.get("/api/conversations", response_model=list[ConversationSummary])
def list_conversations() -> list[ConversationSummary]:
    try:
        with connection() as db:
            rows = db.execute(
                """
                SELECT conversations.*, COUNT(messages.id) AS message_count
                FROM conversations
                LEFT JOIN messages ON messages.conversation_id = conversations.id
                GROUP BY conversations.id
                ORDER BY conversations.updated_at DESC
                LIMIT 12
                """
            ).fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Local chat history is unavailable.") from exc
    return [to_conversation_summary(row) for row in rows]


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str) -> ConversationDetail:
    try:
        with connection() as db:
            return load_conversation_detail(db, conversation_id)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Local chat history is unavailable.") from exc


@app.post(
    "/api/conversations/{conversation_id}/messages",
    response_model=ConversationDetail,
    status_code=201,
)
def send_conversation_message(
    conversation_id: str, payload: ConversationMessageCreate
) -> ConversationDetail:
    """Save one message, retrieve scoped context, and save a grounded reply.

    An inserted user message starts as ``pending``. It becomes ``complete`` only
    in the transaction that saves a validated assistant reply. Failures keep the
    user message with a truthful ``failed`` status and never fabricate a reply.
    """
    user_message_id = str(uuid.uuid4())
    timestamp = now()
    transient_reflection = to_transient_reflection_context(payload.reflection)
    try:
        with connection() as db:
            find_conversation_or_404(db, conversation_id)
            existing = db.execute(
                """
                SELECT id FROM messages
                WHERE conversation_id = ? AND client_message_id = ?
                """,
                (conversation_id, payload.client_message_id),
            ).fetchone()
            if existing is not None:
                raise HTTPException(
                    status_code=409,
                    detail="That chat message was already submitted. Reload the saved chat.",
                )
            db.execute(
                """
                INSERT INTO messages
                    (id, conversation_id, client_message_id, role, content, status,
                     suggested_skill, supporting_message_ids, created_at)
                VALUES (?, ?, ?, 'user', ?, 'pending', NULL, '[]', ?)
                """,
                (
                    user_message_id,
                    conversation_id,
                    payload.client_message_id,
                    payload.content.strip(),
                    timestamp,
                ),
            )
            db.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (timestamp, conversation_id),
            )
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="The chat message could not be saved.") from exc

    try:
        if transient_reflection:
            plan = create_retrieval_plan(
                payload.content.strip(), use_transient_reflection=True
            )
        else:
            plan = create_retrieval_plan(payload.content.strip())
    except UnsafeRetrievalPlan as exc:
        try:
            mark_rag_failure(
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                planned_sql=None,
                status="rejected",
            )
        except sqlite3.Error as database_exc:
            raise HTTPException(
                status_code=503,
                detail="The chat request could not be saved locally.",
            ) from database_exc
        raise HTTPException(
            status_code=502,
            detail="The chatbot rejected an unsafe retrieval plan. Your message is saved.",
        ) from exc
    except RAGServiceUnavailable as exc:
        try:
            mark_rag_failure(
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                planned_sql=None,
                status="provider_failed",
            )
        except sqlite3.Error as database_exc:
            raise HTTPException(
                status_code=503,
                detail="The chat request could not be saved locally.",
            ) from database_exc
        raise HTTPException(
            status_code=503,
            detail="The chatbot is unavailable. Your message is saved without a reply.",
        ) from exc

    try:
        with connection() as db:
            rows = db.execute(plan.sql, (conversation_id, plan.limit)).fetchall()
            personalization = load_chat_personalization(db)
    except sqlite3.Error as exc:
        try:
            mark_rag_failure(
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                planned_sql=plan.sql,
                status="provider_failed",
            )
        except sqlite3.Error:
            pass
        raise HTTPException(status_code=503, detail="Local chat retrieval is unavailable.") from exc

    records = [
        RetrievedMessage(
            id=row["id"],
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"],
        )
        for row in reversed(rows)
    ]
    retrieved_message_ids = [record.id for record in records]
    try:
        reply_kwargs: dict[str, object] = {}
        if personalization.enabled:
            reply_kwargs["practice_context"] = to_practice_context(personalization)
        if transient_reflection:
            reply_kwargs["transient_reflection"] = transient_reflection
        reply: GroundedReply = create_grounded_reply(
            payload.content.strip(), records, **reply_kwargs
        )
    except RAGServiceUnavailable as exc:
        try:
            mark_rag_failure(
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                planned_sql=plan.sql,
                status="provider_failed",
                retrieved_message_ids=retrieved_message_ids,
            )
        except sqlite3.Error as database_exc:
            raise HTTPException(
                status_code=503,
                detail="The chat request could not be saved locally.",
            ) from database_exc
        raise HTTPException(
            status_code=503,
            detail="The chatbot is unavailable. Your message is saved without a reply.",
        ) from exc

    reply_timestamp = now()
    try:
        with connection() as db:
            db.execute(
                "UPDATE messages SET status = 'complete' WHERE id = ?",
                (user_message_id,),
            )
            db.execute(
                """
                INSERT INTO messages
                    (id, conversation_id, client_message_id, role, content, status,
                     suggested_skill, supporting_message_ids, created_at)
                VALUES (?, ?, NULL, 'assistant', ?, 'complete', ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    conversation_id,
                    reply.reply,
                    reply.suggested_skill,
                    json.dumps(reply.supporting_message_ids),
                    reply_timestamp,
                ),
            )
            db.execute(
                """
                INSERT INTO rag_requests
                    (id, conversation_id, user_message_id, planned_sql, retrieval_status,
                     retrieved_message_ids, created_at, completed_at)
                VALUES (?, ?, ?, ?, 'completed', ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    conversation_id,
                    user_message_id,
                    plan.sql,
                    json.dumps(retrieved_message_ids),
                    timestamp,
                    reply_timestamp,
                ),
            )
            db.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (reply_timestamp, conversation_id),
            )
            return load_conversation_detail(db, conversation_id)
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="The chatbot reply could not be saved locally.",
        ) from exc


@app.delete("/api/conversations", status_code=204)
def clear_conversations() -> Response:
    try:
        with connection() as db:
            db.execute("DELETE FROM conversations")
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Local chats could not be cleared.") from exc
    return Response(status_code=204)


@app.post("/api/sessions", response_model=SessionSummary, status_code=201)
def start_session(payload: SessionCreate) -> SessionSummary:
    session_id = str(uuid.uuid4())
    timestamp = now()
    try:
        with connection() as db:
            db.execute(
                """
                INSERT INTO sessions (id, skill, started_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, payload.skill, timestamp, timestamp),
            )
            row = find_session_or_404(db, session_id)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Local history is temporarily unavailable.") from exc
    return to_summary(row)


@app.post("/api/sessions/{session_id}/checkin", response_model=CheckinResponse)
def submit_checkin(session_id: str, payload: CheckinCreate) -> CheckinResponse:
    """Acknowledge a check-in without storing or logging its free text."""
    if not payload.text.strip():
        raise HTTPException(status_code=422, detail="Write a word or continue without sharing.")

    try:
        with connection() as db:
            session = find_session_or_404(db, session_id)
            selected_skill: Skill = session["skill"]
            try:
                # Free text exists only for this adapter call. It is never used
                # in an INSERT, returned, or included in an exception message.
                reply = create_bounded_reply(payload.text, selected_skill)
            except CheckinServiceUnavailable:
                reply = fallback_reply(selected_skill)

            # A user-event marker documents the interaction without retaining text.
            timestamp = now()
            db.execute(
                """
                INSERT INTO conversation_events
                    (session_id, role, event_type, content, suggested_skill, created_at)
                VALUES (?, 'user_event', 'checkin_submitted', NULL, NULL, ?)
                """,
                (session_id, timestamp),
            )
            db.execute(
                """
                INSERT INTO conversation_events
                    (session_id, role, event_type, content, suggested_skill, created_at)
                VALUES (?, 'assistant', 'bounded_acknowledgement', ?, ?, ?)
                """,
                (session_id, reply.acknowledgement, reply.suggested_skill, timestamp),
            )
            db.execute(
                """
                UPDATE sessions
                SET checkin_submitted = 1, updated_at = ?
                WHERE id = ?
                """,
                (timestamp, session_id),
            )
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="The check-in could not be saved locally.") from exc
    return CheckinResponse(
        acknowledgement=reply.acknowledgement,
        suggested_skill=reply.suggested_skill,
    )


@app.post("/api/sessions/{session_id}/finish", response_model=SessionSummary)
def finish_session(session_id: str, payload: SessionFinish) -> SessionSummary:
    try:
        with connection() as db:
            find_session_or_404(db, session_id)
            timestamp = now()
            db.execute(
                """
                UPDATE sessions
                SET status = ?, seconds_completed = ?, updated_at = ?
                WHERE id = ?
                """,
                (payload.status, payload.seconds_completed, timestamp, session_id),
            )
            row = find_session_or_404(db, session_id)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="This practice could not be saved locally.") from exc
    return to_summary(row)


@app.get("/api/sessions", response_model=list[SessionSummary])
def list_sessions() -> list[SessionSummary]:
    try:
        with connection() as db:
            rows = db.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT 12"
            ).fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Local history is temporarily unavailable.") from exc
    return [to_summary(row) for row in rows]


@app.get("/api/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: str) -> SessionDetail:
    try:
        with connection() as db:
            session = find_session_or_404(db, session_id)
            event_rows = db.execute(
                """
                SELECT role, event_type, content, suggested_skill, created_at
                FROM conversation_events
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Local history is temporarily unavailable.") from exc
    return SessionDetail(
        **to_summary(session).model_dump(),
        conversation=[ConversationEvent(**dict(row)) for row in event_rows],
    )


@app.delete("/api/sessions", status_code=204)
def clear_sessions() -> Response:
    try:
        with connection() as db:
            db.execute("DELETE FROM sessions")
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Local history could not be cleared.") from exc
    return Response(status_code=204)
