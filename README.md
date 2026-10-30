# Mental Health Skills App

IST 402 — Assignment 3 starter

## Purpose

Build a local application that lets someone practice a short skill, stop at any
point, and return to useful session history. The interface should ask for little
reading or typing and keep the person in control. A conversational model can
help introduce the skill and explain the app, using reviewed content and saved
context.

This is a coursework prototype, tested only with fictional scenarios. It must
not diagnose, provide therapy, imply human monitoring, or be offered as a real
mental health support service.

## Startup scope

Create the base folders, README.md, and AGENTS.md. This step establishes project
context. The application capabilities below are plans for later implementation.
There is no selected interface design or running application yet.

## Your design guidelines — to be completed

Before asking an agent to build the interface, add your own design guidelines
here. Use the principles taught in class and the research discussed for
Assignment 3 to explain your choices. The starter does not choose the skill,
screen layout, or interaction flow for you.

Class principles to carry into your design:

- Keep the guided skill within 90 seconds at its intended pace. Show one clear
  action at a time and keep reading, typing, and configuration demands low.
- Let people start, stop, skip, and change their choices. Keep support information
  visible and usable independently of model responses.
- Use calm, readable language, sufficient contrast, visible keyboard focus,
  a narrow-screen layout, and an alternative to motion.
- Make personalization understandable and changeable. Keep self-report,
  observed behavior, and interpretation distinct; clicks do not establish an
  emotional state or diagnosis.
- Explain how a design choice follows from a class finding, what alternative
  you considered, and what tradeoff you accepted. Check the running result later.

Add your project-specific decisions when you are ready:

- Chosen skill and fictional user/task: [to be decided]
- Main interaction flow and user controls: [to be decided]
- Interface guidelines and their class/research rationale: [to be added]
- Model's role, saved context, and useful personalization: [to be decided]
- Alternative designs and reasons for the selected direction: [to be added]

You may choose paced breathing, sensory grounding, STOP, or a cognitive reframe
within the assignment's scope. Record detailed design decisions in
`docs/design-pipeline.md` as the design develops.

## Technology and separation

- Frontend: Vue with JavaScript, HTML, and CSS. It presents the interface,
  responds to input, and sends HTTP requests to the backend. Node.js provides
  the frontend development tools.
- Backend: Python with FastAPI. It exposes the API, validates requests, applies
  business rules, calls the conversational model, and reads/writes the database.
- Database: SQLite. The planned database is data/app.sqlite3. Only the Python
  backend accesses it; the frontend receives data through the API.

The application runs on localhost.

## Secrets and APIs

Store model-provider API keys and other secrets in `backend/.env`. Keep this
file out of Git with `.gitignore` before adding credentials. Provide a
`backend/.env.example` containing variable names and empty or dummy values so
another developer knows what to configure. The backend must explicitly load its
configuration; placing a file in the folder does not load it automatically.
Never put private keys in Vue code, browser-exposed environment variables,
API responses, logs, screenshots, prompts, or Figma.

Vue calls our FastAPI endpoints using HTTP and JSON. FastAPI validates requests,
calls the external model API, and reads or writes SQLite. Document each endpoint's
input, response, and failure behavior in `docs/design-pipeline.md`. Use finite
timeouts, clear loading and failure states, and a bounded number of provider
calls. A configured key, a mocked response, and a successful live API call are
different checks. Ordinary history browsing should not require a model call.

## Conversations, RAG, and data views

Save submitted user messages and actual model replies in SQLite, linked by a
conversation ID. Keep a message ID, role, content, timestamp, and request status
so the app can reconstruct the conversation in order. Store exercise outcomes
and preferences in related records. A failed model request must not create a
fabricated reply, and a failed database write must not appear as a successful
save. Saved records should survive refresh and backend restart without duplicates.

**Retrieval-augmented generation (RAG)** supplies relevant stored information to
the model before it answers. Use the SQL-based pattern covered in class:

1. FastAPI sends the question and relevant database schema to the model API.
2. The model proposes a retrieval query. FastAPI checks it, restricts it to
   allowed data for the current conversation or demo user, and executes it using
   read-only SQLite access with limits on the results.
3. FastAPI sends the selected records and reviewed skill information in a second
   model call. The answer should identify its supporting records and acknowledge
   missing information instead of inventing history.
4. Backend application code saves the actual reply and returns the result to Vue.

The model never connects directly to SQLite. RAG retrieval cannot insert,
update, or delete records; normal conversation saves use separate, parameterized
backend operations. The query-planning and answer-generation calls both count
toward the API budget. SQLite is sufficient for this baseline; it does not
require a vector database.

Make the saved data visible. Provide a Vue conversation-history view and a
session table or timeline, both populated through FastAPI from SQLite. Show
message order and time, plus exercise duration and stopped/completed status.
Any summary or chart must come from those records and must not imply a diagnosis
or improvement in mental health. During development, also inspect the schema,
relationships, and rows with an available SQLite viewer or read-only queries.
Compare the database, API response, and displayed history for the same fictional
conversation, including after a refresh and backend restart.

## Project folders

```text
project-root/
|-- README.md                 Project purpose and starting direction
|-- AGENTS.md                  Instructions for the coding agent
|-- .gitignore                 Local files to exclude from Git
|-- frontend/                  Vue interface and frontend dependencies
|-- backend/                   Python/FastAPI API and application logic
|   |-- .env                   Local secrets; ignored by Git
|   `-- .env.example           Configuration names with safe placeholders
|-- data/                      Local SQLite database and fictional fixtures
|-- docs/
|   |-- design-pipeline.md     Architecture, behavior, and design decisions
|   `-- verification.md        Checks to run and evidence of what happened
|-- prompts/
|   `-- 01-start.md            First scoped instruction for the agent
`-- handoffs/
    `-- current.md            Current state and next step for a new session
```

This map includes files to add as the project develops. At startup, create only
the base folders and the two root documents, README.md and AGENTS.md. Leave
existing supporting files intact if you already have them. Add the ignore rules
before introducing credentials or runtime data; create environment files and
the SQLite database during implementation. Keep fictional fixtures separate
from runtime records and do not commit the working database.

## Later design workflow

The separate Figma and MCP activity covers building a small interface, bringing
it into editable Figma frames, and using a selected design to guide a Vue
revision. That work comes after this startup step and your initial design
guidelines. Figma edits do not automatically update application code.

## Getting started

Read `AGENTS.md`, create the base folders, and keep the undecided design items
visible. Startup is complete when the folders and these two documents are in
place. Complete your design guidelines before requesting implementation.

Add supporting project notes as work requires them. Installation, interface
building, FastAPI/model connections, SQLite, RAG, and data views are later tasks.
Record actual setup, configuration, run, stop, and test commands here only after
they have been implemented and checked.

## Implemented RAG chatbot increment

The repository now includes a localhost Vue + FastAPI + SQLite prototype. The
saved-context chatbot is for **fictional coursework scenarios only**; it is not
therapy, diagnosis, crisis support, clinical monitoring, or an emergency
service. Crisis Support remains visible and works separately from the chatbot.

### Run locally

Use Python 3.11+ and Node.js 20+. In one terminal:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export QUIET_STEPS_RAG_MODE="mock"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd frontend
npm install
export VITE_API_BASE_URL="http://127.0.0.1:8000/api"
npm run dev
```

Open the local Vite URL. Routine development and tests use `mock` mode, which
makes no OpenAI request. The SQLite runtime database defaults to
`backend/data/quiet_steps.sqlite3`; set `QUIET_STEPS_DB_PATH` before starting
the API to use another local path.

If Vite reports that port 5173 is already occupied, start it on an allowed
local fallback port instead:

```sh
npm run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

The backend's default local CORS settings allow Vite ports 5173 through 5175.

### Connect your OpenAI key for a fictional live check

Do not paste a key into chat, Vue code, or a `VITE_*` variable. Copy
`backend/.env.example` to the ignored `backend/.env` file, add your key only
there, and explicitly load it before starting FastAPI:

```sh
cd backend
cp .env.example .env
# Edit .env locally: set OPENAI_API_KEY and change QUIET_STEPS_RAG_MODE to openai.
set -a
source .env
set +a
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In `openai` mode, each submitted fictional chat message makes up to two
bounded Responses API calls: a strict JSON retrieval-plan response, then a
strict JSON grounded-reply response. The backend uses the key and OpenAI
directly; the browser receives only the application API response. The backend
validates both outputs even when Structured Outputs is enabled. OpenAI
Structured Outputs uses `text.format` with a strict JSON Schema; see the
[official OpenAI documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

### GPT-Live audio status

The repository has a GPT-Live WebRTC increment in the existing Chat screen.
The optional **Start voice** control requests microphone permission only after
selection, creates the browser SDP offer, and sends that offer only to the
local FastAPI endpoint. After the session starts, **Mute microphone** and
**Unmute microphone** send only their matching Live commands and wait for the
matching confirmation. The server restricts the browser data channel to those
two commands; it cannot alter the model, instructions, tools, storage,
exercises, or Crisis Support route. Voice is disabled by default, stores no
voice audio, transcript, or live-session record, and leaves text chat available
when voice is unavailable. It uses a brief `gpt-live-1` spoken role and a
separate `gpt-6-luna` Responses-delegation role with no tools.

A future, deliberately approved fictional live-audio check will require the
same server-only `OPENAI_API_KEY` described above and an explicit ignored
environment opt-in, `VOICE_LIVE_AUDIO_ENABLED=1`. Do not enable it for routine
development or tests; those use mocked provider responses. A graceful **End
voice** control is still the next increment. The model roles, gate, and
remaining browser work are documented in
[docs/design-pipeline.md](docs/design-pipeline.md).

### RAG data and failure behavior

For this assignment's RAG requirement, the local SQLite database stores the
fictional user and assistant messages, stable IDs, roles, timestamps, request
states, chosen skill, and cited record IDs. A live chat message is sent to
OpenAI only when `QUIET_STEPS_RAG_MODE=openai`; use fictional data only. The
first model response may propose only one application-allowlisted read-only SQL
template. FastAPI binds the current conversation ID and limit itself, runs the
query locally, and sends only those retrieved records plus the current question
to the second model call. The model never opens SQLite.

If model configuration, the provider, structured output, or a plan fails, the
user message remains in history with `failed` status and no assistant reply is
invented. The UI offers a calm retry/leave path and keeps Crisis Support
available. See [docs/design-pipeline.md](docs/design-pipeline.md) for endpoint
contracts and [docs/verification.md](docs/verification.md) for repeatable
checks.

### Reviewed chat source notes

When the chat suggests a practice, it displays a reviewed research-context note
and direct DOI link for that specific practice. Paced Breathing uses Bentley et
al. (2023), [*Breathing Practices for Stress and Anxiety
Reduction*](https://doi.org/10.3390/brainsci13121612); STOP uses Gasol et al.
(2022), [*Preventing Emotional Dysregulation*](https://doi.org/10.3390/ijerph19010494).
These are static app-authored explanations, not live web results or model
output. They spell out the research limitations: the app's 60-second breathing
exercise is shorter than the reviewed programs, and the compact STOP flow is
not the study's 30-lesson curriculum. No personal data is used to choose,
generate, or access either note.

### Daily mood calendar

**Your days** is a monthly calendar that displays activity records separately
from an optional daily self-report. A person deliberately chooses one label for
a selected calendar date: `very_low`, `low`, `in_between`, `good`, or
`very_good`. They can revise, remove, or clear these entries. The API accepts
only the date and one allowlisted label; it has no free-text-note field.

This feature is a reflection tool, not an assessment, score, diagnosis, or
evidence that a practice changed someone’s state. Mood entries do not change
the recommended activity, are not sent to OpenAI or the optional chatbot, and
do not affect independent Crisis Support.

### Checks run

```sh
cd backend && .venv/bin/python -m pytest tests -q
cd frontend && npm run test && npm run build
```

These automated checks run in deterministic mocked-model mode. A separate
fictional live-key smoke check passed locally on 2026-10-28; it verifies only
that machine's configuration, not billing limits, provider reliability, or
live-model variation.
