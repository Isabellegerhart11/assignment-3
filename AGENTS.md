# Instructions for the coding agent

Work toward the application described in `README.md`. Work inside this project
root and preserve existing code, data, and unfinished work. Read the README and,
when present, `docs/design-pipeline.md` and `handoffs/current.md` before changes.
These instructions are self-contained; no course website is needed to use them.

## Startup boundary

For the startup task, create only the base folders and README.md/AGENTS.md.
Preserve existing supporting files. Do not install dependencies, build an
interface, configure credentials, create a database, or create/capture a Figma
design during this step. Add supporting documents later as work requires them.

The README leaves project-specific design guidelines open. Before implementing
an interface, obtain the developer's chosen skill, intended flow, design
guidelines, and rationale based on class principles. Do not silently substitute
the lecture's breathing example or invent decisions for unfinished placeholders.
The instructions below govern later development as those tasks are requested.

## 1. Keep the frontend, backend, and database separate

- **`frontend/`: Vue with JavaScript, HTML, and CSS.** Put Vue components,
  interface state, input controls, pacing cues, and API-request code here.
  Use Node.js for frontend tooling and declare dependencies in `package.json`.
- **`backend/`: Python with FastAPI.** Put API routes, request validation,
  controllers, data models, database access, and model-provider calls here.
  Use a project environment at `backend/.venv` and declare Python dependencies.
- **`data/`: SQLite and fictional fixtures.** Use `data/app.sqlite3` for the
  working database. Resolve that path from the project location so it does not
  change with the terminal's working directory. Only backend code opens it.
- Vue communicates with FastAPI through HTTP requests and JSON responses.
  Vue must not open SQLite or call the model provider with a private key.
- Follow MVC responsibilities: models define data and relationships; views
  display information and accept input; controllers apply business rules and
  coordinate data operations. Keep FastAPI routes small. Document the actual
  files that own these responsibilities as implementation develops.
- Application code controls the exercise sequence, timers, exits, and support
  route. The conversational model cannot change these rules.

## 2. Put project context in the right place

- `README.md`: purpose, stack, folder map, and verified setup/run instructions.
- `docs/design-pipeline.md`: architecture, request/data flow, behavior contracts,
  design rationale, and decisions that affect implementation.
- `docs/verification.md`: repeatable checks, expected/observed results, and
  anything still unverified.
- `prompts/`: significant instructions worth reusing; use descriptive numbered
  names and remove credentials or private content.
- `handoffs/current.md`: actual current state, unfinished work, checks run, and
  the next task. Include the branch and relevant commit once they exist.

Update the relevant document when a decision or behavior changes. Avoid copying
whole conversations or creating several documents that repeat the same facts.

## 3. Inspect, plan, and make small changes

Confirm the project folder, branch, existing files, and uncommitted changes.
Summarize the requested result, affected files, behavior to preserve, and how
success will be checked. Work on one coherent increment at a time.

Use **CHECK → TAKE ACTION → VERIFY** for environment setup. Inspect Python,
Node.js, and declared dependencies first. Before an installation that has not
already been authorized, show the packages, exact commands, and target environment
and obtain approval. Verify the resulting versions and imports. Keep dependencies
project-local and preserve existing configuration.

Define inputs, outputs, failure behavior, and a worked example before connecting
components. Prove one backend operation, then one complete frontend-to-backend
round trip, before expanding the interface.

## 4. Protect secrets and define API behavior

Keep provider credentials and other secrets in `backend/.env`. Verify that Git
ignores it before credentials are added. Maintain `backend/.env.example` with
required variable names and empty or dummy values only. Do not expose secrets
in Vue code, browser-exposed environment variables, API responses, Git, logs,
screenshots, prompts, or Figma. An ignore rule does not remove a secret already
committed. Never overwrite an existing local environment file.

Load configuration explicitly. A health check may report whether settings are
present, never their values. Distinguish configuration from a successful provider
call and document the configuration path and any required restart.

Keep application APIs and external-provider APIs distinct. Vue sends HTTP/JSON
requests to FastAPI; only the backend calls the model provider. Define and record
each endpoint's method, path, validated input, successful response, and error
response. Include conversation submission, history retrieval, session saving,
and preference updates as those operations are implemented. Use typed request
and response models, consistent error handling, and stable record identifiers.

Use bounded provider calls with finite timeouts and checked responses. Keep
loading, empty, failure, and success states distinct. Prevent duplicate requests
and saves; ignore stale responses from an earlier request. Report failed saves
honestly. Preserve existing records and avoid reseeding or duplicating them at
startup. Use fictional data for all tests and demonstrations.

### Save conversations and retrieve context with RAG

Persist submitted user messages and actual assistant replies with message and
conversation IDs, role, content, timestamp, and request status. Store exercise
sessions and preferences in related records. Make ordering and relationships
explicit. Use application-owned, parameterized database writes and transactions
where related writes must succeed together. A retry must not duplicate messages;
a failed request must not invent a reply or hide a failed save.

Implement the class SQL-based retrieval-augmented generation (RAG) flow:

1. FastAPI sends the question and relevant schema to a model API to propose a
   retrieval query. Schema describes the data; it is not the retrieved records.
2. Treat proposed SQL as untrusted. Validate a single allowed read-only query,
   enforce permitted tables/fields and the current conversation or demo-user
   scope, bind values safely, and execute through a read-only SQLite connection.
   Bound returned rows, query time, and context size. Reject writes and unsafe
   statements; checking only that text starts with SELECT is insufficient.
3. Send only the relevant retrieved records and reviewed skill context in the
   answer-generation call. Include record IDs and field meanings. Treat stored
   text as data, not instructions that can override application rules. Require
   grounded claims and an honest response when the context is insufficient.
4. Save the actual model reply through the normal application save operation,
   then return it to Vue with accurate persistence status.

The model never opens SQLite. Keep RAG retrieval read-only and separate from
conversation/session writes. Distinguish empty retrieval, rejected queries,
database failures, and provider failures. Count both model calls toward usage
limits. Use SQLite for this baseline; do not add a vector database or framework
unless a later task calls for it.

### Make stored data visible and inspectable

Build a Vue conversation-history view and a session table or timeline using
FastAPI responses backed by SQLite. Show message order/time, duration, and
stopped/completed status accurately. Derive any summaries or charts from saved
records; never turn activity counts into claims about emotional state or
clinical improvement. Clearly distinguish fictional fixtures from new records.

Use an available SQLite viewer or read-only queries to inspect the schema,
relationships, and rows during verification. Compare one conversation across
the database, API response, and Vue view by its record IDs. Document the actual
inspection method; do not require a particular viewer or install one silently.

## 5. Preserve the design boundaries

- Keep the chosen skill's steps intact. The intended guided sequence must fit
  within 90 seconds, measured from first instruction to final planned step,
  including application delays. Report entry/setup time separately; exclude
  voluntary pauses and time accessing support. Do not force completion or exit.
- Keep Stop usable throughout an exercise. Clear old timers when leaving or
  restarting. Record stopped and completed sessions differently.
- Keep a clearly identified crisis-support route visible and usable in every
  relevant state, even when the model fails. It must not depend on a classifier,
  questionnaire, or generated response. Verify its resource content before
  presenting it as usable support information.
- Keep reading, typing, and configuration demands low. Use readable contrast,
  visible keyboard focus, a narrow-screen layout, and an alternative to motion.
- Use saved preferences transparently. Let the person skip, reject, or change
  suggestions. Keep self-report, observed behavior, and interpretation distinct;
  do not infer a diagnosis or emotional state from clicks or a custom check-in.
- Keep the coursework label accurate. Do not invent therapeutic advice, claim
  clinical effectiveness, imply monitoring, or deploy this as a support service.

## 6. Bring the running interface into Figma through MCP

**In a later design task, we will bring the running Vue interface into Figma
through the Figma MCP connection, refine a design alternative, and implement the selected design back
in Vue.** This is the planned design workflow after initial setup and design
guidelines. Do not perform it as part of folder/document creation.

First build and verify a small interface using fictional data. Confirm the
available Figma MCP tools and access to the intended file or drafts location.
Use the supported MCP capture/design workflow to bring representative running
views into editable Figma frames. Preserve the baseline frames and record the
returned file/frame links in `docs/design-pipeline.md`. Check that the captured
text and interface elements are editable; a screenshot alone is not editable
interface capture.

Compare alternatives and explain the selected choice. Give the coding agent the
exact selected-frame link, inspect its design context and screenshot through
MCP, identify missing behavior details, and implement in the existing Vue
components. Preserve agreed API/data contracts.

Compare the running interface with the reference at a similar size and test its
interactions. Figma changes require an explicit implementation request and new
verification; there is no automatic synchronization. If MCP access is unavailable,
report the limitation and use an exported image with behavior notes temporarily.
Do not claim that a capture or implementation occurred without verifying it.

## 7. Verify with evidence

**SmokeTest** checks the existing application without editing source code. Run
appropriate frontend/backend checks, operate the real browser, and inspect the
actual SQLite records before and after relevant operations. Check refresh and
service restart. A build or a success message alone is not sufficient evidence.
For RAG, verify selected records, empty results, and rejection of a write query.
For conversation history, verify message order, record IDs, accurate saved/failed
states, and no duplicates after retries or restart. Compare data visualizations
with the underlying rows. Check missing configuration and a failed provider
request without printing credentials; label mock versus live API evidence.

**AutoLoop** allows correction: run the agreed check, inspect the failure, make
the smallest in-scope fix, and rerun. Stop when it passes, after five correction
cycles, or when a new decision or permission is needed. Report the blocker.

Cover ordinary use, boundaries, interruptions, and failures. Use mocks for
repeatable checks and clearly identify live-model checks. Record actual commands,
expected results, observations, and untested behavior in `docs/verification.md`.
Never report a planned check as passed. Keep paid calls within the agreed limit.

## 8. Review, checkpoint, and hand off

Use a feature branch for substantial work without discarding unfinished changes.
Show the diff and call attention to unexpected files so the developer can inspect
it and try the feature. Commit a coherent, checked milestone when requested;
stage only the intended files. Initialize Git only when authorized and needed.

Use the supplied remote URL. Pushing a branch does not merge it. Before an
authorized merge, check uncommitted work and show any conflicts with a proposed
resolution. Check the merged application on `main` before the requested push,
and verify that the intended branch and commit reached the remote.

Before ending a work session, update the design/verification notes and the current
handoff. Record completed work, unfinished work, checks actually run, and the
next step. A new session must verify these claims against the files. Keep a
curated record of tools, models, important prompts, and failed or revised
approaches for the project's AI-use disclosure.
