# RAG chatbot verification

## Repeatable automated checks

Run all routine checks in deterministic mode; they make no OpenAI request and
use fictional text only.

```sh
cd backend
export QUIET_STEPS_RAG_MODE="mock"
.venv/bin/python -m pytest tests -q

cd ../frontend
npm run test
npm run build
```

Observed on 2026-10-29:

- Backend: `33 passed`; only the existing Starlette/TestClient deprecation
  warning was emitted.
- Frontend: `33 passed`; production build completed successfully.

## What the automated checks establish

| Check | Evidence |
| --- | --- |
| Conversation persistence | A fictional user/assistant exchange remains available to a new FastAPI client using the same SQLite file. |
| RAG retrieval scope | Mock RAG records the exact allowed `SELECT` template and retrieved message IDs. |
| Duplicate prevention | Reusing a client message ID returns `409` without a second reply. |
| Provider failure | Failure mode retains only a user message marked `failed`; no assistant reply is invented. |
| Unsafe plan | A simulated unsafe retrieval plan returns `502`, marks the user message failed, and saves no assistant message. |
| OpenAI request contract | A synthetic Responses API payload verifies the HTTPS endpoint, server-side Authorization header, `store: false`, and strict JSON-schema request. |
| Anonymous profile persistence | An accountless profile retains only a preferred skill, motion preference, and chat-personalization opt-in across a new FastAPI lifecycle; it rejects unexpected reflection data and can be reset. |
| Profile-aware chat boundary | When opt-in is enabled, the RAG service receives only the preferred skill, latest completed skill, and completed-practice counts. |
| One-time reflection handoff | An explicit selected-response handoff generates the app-owned practice suggestion even in forced model-failure mode. The response labels are absent from SQLite messages and never reach the RAG model. |
| Daily mood boundary | The API accepts only a selected calendar day and one of five labels, rejects unexpected free-text fields, supports revision and removal, and the RAG-context test confirms an existing mood entry is not included in the model context. |
| Vue flow | The UI sends a fictional message, shows a reviewed description and direct DOI source link for the allowlisted suggested practice plus its launch control, shows cited IDs, and keeps Crisis Support reachable after a failed RAG request. |
| Profile adaptation and accessibility | The UI test confirms the selected skill changes Home’s featured practice, a person can choose another activity or clear preferences, and a reduced-motion preference reaches the visual shell. |
| Existing skill safety | Existing tests still cover paced-breathing completion, STOP/breathing exits, optional check-in skip, timing, and Crisis Support. |
| Bottom navigation | The UI test opens the Activities, Calendar, Profile, Chat, and Crisis routes using the new icon bar, and verifies the bar is absent while paced breathing or Crisis Support is open. |
| Mocked WebRTC voice flow | The controller checks configuration before microphone permission; validates the `oai-events`-before-offer sequence; remains connecting until `session.started`; sends only mute/unmute input commands and waits for their matching confirmations; ignores a fictional transcript event; handles closure; offers a blocked-playback retry; and leaves text chat usable after unavailable or denied voice. |

## Manual local checks

1. Start the API and Vue app in `mock` mode. Open **Open fictional RAG
   chatbot**, ask a fictional question, reopen the saved chat, and confirm the
   user/assistant message order, timestamp, status, and cited record IDs.
2. With the API stopped and restarted using the same `QUIET_STEPS_DB_PATH`,
   reopen the chat and confirm the saved conversation remains.
3. Set `QUIET_STEPS_RAG_MODE="failure"`, send a fictional message, and confirm
   the failure text appears, the saved user message is `failed`, no assistant
   reply is shown, and Crisis Support is still usable.
4. With a real key held only in ignored `backend/.env`, set
   `QUIET_STEPS_RAG_MODE="openai"` and use one fictional test message. Confirm
   the app shows a response with record IDs. Return to `mock` mode afterwards.
5. In **Profile setup**, choose STOP and **Less motion**, enable the optional
   practice-context checkbox, then return Home. Confirm the featured card names
   STOP, **Choose another activity** still opens both skills, and clearing the
   preferences restores the default. Restart FastAPI and confirm the selected
   preferences remain until cleared.
6. With chat personalization enabled, send a fictional chat message. Confirm
   the small context notice is visible and the reply remains a neutral,
   allowlisted suggestion. Turn the option off and confirm the notice says chat
   uses the saved conversation only. Do not enter real or sensitive text.
7. Use keyboard navigation through Profile, the Home feature actions, and the
   breathing Pause/Leave controls. With reduced motion enabled, confirm the
   written phase/count still changes while the circle does not animate.
8. Open **Your days**. Use the month arrows, select a date, choose one mood
   label, then change and remove it. Confirm the calendar shows a mood marker
   separately from an activity marker. Use **Clear all moods** only with
   fictional test entries. Confirm no text-note field is present and that
   Check-in Chat and Crisis Support continue to work independently.

Observed local live-key check on 2026-10-28: one fictional message completed
through the OpenAI-backed path after the local Python HTTPS trust store was
configured with `certifi`. The response saved a completed assistant message,
cited only a retrieved record ID, and chose an allowlisted skill. This is one
local configuration check, not evidence of billing limits, provider-wide
reliability, deployment readiness, or variation across future model responses.

Observed browser path on 2026-10-28: after replacing a stale Vite development
server with one configured for the active local API, the browser's CORS
preflight and `POST /api/conversations` and `/messages` calls succeeded. The
visible chat showed a pending state, then distinguishable completed user and
assistant messages. A fictional follow-up correctly used the earlier saved
greeting as retrieved context. The browser-facing API module contained only
the local application URL; the OpenAI key remains server-side.

## Read-only SQLite inspection

With the API stopped or using a copy of the runtime file, inspect only
fictional records:

```sh
sqlite3 backend/data/quiet_steps.sqlite3 \
  "SELECT id, role, status, created_at FROM messages ORDER BY rowid;"
sqlite3 backend/data/quiet_steps.sqlite3 \
  "SELECT retrieval_status, planned_sql FROM rag_requests ORDER BY created_at;"
```

Compare message IDs in the second query with the cited IDs displayed in the Vue
chat. Do not put a real key or non-fictional message content in screenshots or
submitted evidence.

## GPT-Live session boundary — mocked backend increment

Run without a provider call:

```sh
cd backend
QUIET_STEPS_RAG_MODE=mock .venv/bin/python -m pytest tests/test_voice.py -q
```

Observed on 2026-10-29: `12 passed`, with the same existing
Starlette/TestClient deprecation warning. The full backend suite then passed:
`33 passed`.

These tests verify the new FastAPI boundary only: a configuration response
reveals only setup status and a clamped duration; a local API key alone cannot
enable voice; missing, extra, or oversized SDP inputs never reach a provider;
server-owned `gpt-live-1`, `gpt-6-luna`, `store: false`, the reviewed spoken
and delegated prompts, and `tool_choice: "none"` are used once with a synthetic
response; and provider errors or malformed results return app-owned wording
that leaves text chat available. CORS is also verified for the active local
Vite origin.

No actual microphone permission, WebRTC connection, or live OpenAI provider
request was made in this increment. The mocked Vue controller covers the
browser sequence and the provider-confirmed Mute/Unmute controls, but graceful
user-initiated End, final session confirmation, and one short live-call
observation remain unverified until later increments.
