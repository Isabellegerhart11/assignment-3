# AI-USE.md

## Disclosure

AI assistance was used for this coursework project. The work remains the student's responsibility, including checking that the design, claims, and final submission accurately represent the project.

| Tool or model | Version / identifier available | Role in this project |
| --- | --- | --- |
| Codex, GPT-5 | Identified in the workspace as Codex based on GPT-5; exact serving-model identifier was not displayed | Helped organize the assignment requirements, develop the Quiet Steps concept, draft design copy, create the markdown documentation, and review the submission package. |
| Figma connector | OpenAI-curated Figma plugin, version 16.0.0 | Created a small token set, reusable Figma elements, and six mobile-interface frames in the linked Figma file. |
| In-app browser control | Browser plugin, version 26.825.32147 | Attempted a fallback connection after the Figma connector reached its preview/edit limit. It was not signed in and made no Figma changes. |
| Codex, GPT-5 | Identified in the workspace as Codex based on GPT-5; exact serving-model identifier was not displayed | For Part 3.2, scaffolded the localhost Vue, FastAPI, and SQLite coursework prototype; translated the existing Figma screens into the interface; and added automated verification. |
| Figma connector | OpenAI-curated Figma plugin, version 16.0.0 | Retrieved a rendered reference of the six existing Quiet Steps screens to guide the Part 3.2 interface. The connector's structured layer export was unavailable because no layer was selected; no Figma content was changed. |

## Boundaries used for this project

- AI was not used to fabricate user research, participant data, citations, test results, or recordings.
- The proposed check-in behaviour is a design constraint, not a deployed model feature.
- The planned in-product model, if implemented later, may only return a short neutral acknowledgement and a suggestion from a fixed allowlist. It must not diagnose, provide therapy, monitor a person, or route a person away from the independent crisis-support control.
- The final repository contains a curated, redacted evidence log rather than a complete chat export.

## Part 3.2 implementation note

The local prototype defaults to a deterministic mock rather than a deployed model. It includes an optional, fictional live-demo adapter configuration for code-path testing only. Any live response is checked in application code against a fixed acknowledgement allowlist and the two allowed skill suggestions before it reaches the UI or local history; invalid output becomes a fixed fallback. No real provider URL or credential is included in this repository.

## Part 3.2 documentation and verification note

Codex assisted with drafting the separate Part 3.2 report, the repeatable test cases, the manual verification checklist, and the curated evidence wording. The student remains responsible for reviewing the claims, creating the final submission commit, and adding any course-required recording link. Automated results were run locally with deterministic mocked-model fixtures and fictional check-in wording; AI was not used to fabricate a recording, participant feedback, deployment claim, or sensitive data.

For a later Profile revision, Codex used the supplied questionnaire only to identify the distinction between a present-moment, standardized anxiety instrument and an original prototype reflection. It implemented four new, unscored statements with original wording rather than copying, adapting, scoring, or presenting the STAI. At the student's request, Codex later added an explicit one-request handoff: selected reflection labels can feed an application-owned two-skill starting-point rule, but are discarded after the request and are not stored or sent to the model.

For a later presentation-focused revision, Codex assisted with an accountless preference-profile design, a limited practice-history adaptation, the allowlisted RAG context boundary, and corresponding deterministic tests. The profile stores only voluntarily selected practice and motion preferences plus an opt-in flag; it does not make a health inference or include questionnaire/check-in/crisis data. The separate transient reflection handoff is not profile data, RAG context, or persistent storage.

For the later daily-calendar revision, Codex used the supplied visual reference as layout inspiration and implemented a voluntary five-label mood choice with month navigation, edit/remove controls, and tests. It intentionally omitted the reference’s optional free-text note field; the date-plus-label record is not an assessment and is excluded from chatbot context.

For a later chat-detail revision, Codex added reviewed, application-owned
descriptions of the two approved practices beneath their chatbot suggestion
controls. This detail is not model-generated, does not alter the practice
sequence, and does not expand the chatbot beyond its existing fictional,
non-clinical boundary.

At the student's request, Codex then used two supplied academic PDFs to add
direct source links and deliberately qualified research-context notes for the
two approved practices. The source notes are static application copy: they do
not provide model internet access, are excluded from prompts and saved messages,
and explicitly distinguish the short prototype exercises from the studies'
longer interventions or curriculum.

## RAG chatbot increment

Codex assisted with implementing a separate fictional-conversation RAG path:
SQLite conversation/message records, application-validated read-only retrieval,
an OpenAI Responses API adapter, a Vue saved-chat view, and deterministic
mock/failure tests. Official OpenAI documentation was consulted for the
Responses API Structured Outputs request shape. No API key was shared with
Codex, no live OpenAI call was made during development, and no non-fictional
conversation was used. A revised approach is recorded in `docs/evidence.md`:
the first implementation ordered messages by random UUID before testing exposed
the issue; it was changed to SQLite insertion order (`rowid`).

## GPT-Live configuration increments

Codex consulted official OpenAI GPT-Live documentation while adding the
server-only session boundary and the next role-configuration increment. It
separated a brief spoken-model prompt from a detailed delegated Responses-model
prompt, declared no tools, kept voice disabled by default, and added mocked
payload tests. No API key was shared with Codex, no microphone was enabled, no
audio or transcript was persisted, and no live OpenAI request was made.

For the following Vue increment, Codex added a native WebRTC controller with
mocked browser/media tests, a Chat-screen voice state panel, and an autoplay
retry action. A later revision used the official GPT-Live session-management
guidance to add provider-confirmed Mute/Unmute controls and a matching
least-privilege data-channel allowlist. It used no browser microphone permission
and made no live provider request; graceful End remains separate future work.
