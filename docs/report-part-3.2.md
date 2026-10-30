# Part 3.2 — Implementation and Verification Report

## Submission identifiers

- Repository URL: [github.com/Isabellegerhart11/assignment-3](https://github.com/Isabellegerhart11/assignment-3)
- Part 3.2 implementation commit: `PART_3_2_IMPLEMENTATION_COMMIT` — replace this placeholder with the full SHA of the first reviewed Part 3.2 delivery commit. Do not substitute the Part 3.1 commit or tag.
- Part 3.1 record retained separately: [`part-3.1-submission`](https://github.com/Isabellegerhart11/assignment-3/tree/part-3.1-submission) resolves to [`70879e20edf1e303030e246460d85864adc8cf62`](https://github.com/Isabellegerhart11/assignment-3/commit/70879e20edf1e303030e246460d85864adc8cf62).
- Design reference: [Quiet Steps Figma design](https://www.figma.com/design/dDWNzyxOVEEoOPLYcuiLr2/Assignment3?node-id=1-3)

## Linked materials

- [Part 3.2 setup, automated commands, and manual verification checklist](../README.md#part-32--local-working-prototype)
- [Design rationale, flow, implementation boundaries, and timing assumptions](design.md#part-32-implementation-supplement)
- [Curated, redacted verification evidence](evidence.md#part-32--implementation-evidence)
- [AI-use disclosure](../AI-USE.md)
- [Original Part 3.1 report](../report.md) — retained as the original submission record and not amended for Part 3.2.

## Recording placeholders

- Walkthrough recording: **TBD — add the course-approved URL or file reference if a recording is required.**
- Recording date / presenter: **TBD**
- Recording contents to show: a fictional check-in skip, paced-breathing completion, leaving paced breathing and STOP, local history after restart, and independent Crisis Support during forced model failure.

No recording is claimed or linked by this report yet.

## What is complete

Quiet Steps is now a localhost Vue + FastAPI + SQLite coursework skills-practice prototype. It is explicitly not therapy, diagnosis, monitoring, emergency care, or a live support service.

- A person can begin a 60-second paced-breathing skill with a circle that expands alongside a 1-to-4 inhale count-up and settles alongside a 6-to-1 exhale countdown, plus pause control, leave control, completion screen, repeat option, and a choice of another skill. Only the sixth planned exhale records completion; leaving returns immediately and records a voluntary exit without waiting on SQLite.
- The fixed STOP flow presents Stop, Take a step back, Observe, and Proceed mindfully one at a time. It has Back, Continue, Leave exercise, and Crisis Support controls; optional check-in output cannot alter this sequence.
- Check-in is optional. Routine verification uses a deterministic mocked-model mode. The backend stores only the check-in-submitted marker plus a fixed allowlisted acknowledgement and allowed skill suggestion, never the free text.
- SQLite session and allowed-conversation metadata can be reviewed, cleared, and recovered after a restart. The separate accountless preference profile retains only a selected practice, motion preference, and explicit chat-personalization opt-in; it has no identity or health fields and can be reset. Home visibly features that selected practice or, when no preference exists, the most recent completed practice. The person can always choose another skill or clear preferences.
- The Profile reflection uses four original, optional, unscored present-moment statements. It is not the STAI and is never saved. A person can explicitly hand selected labels to the next Check-in Chat request for a one-time, app-owned starting-practice suggestion; those labels are discarded before the request completes, are never added to chat history or SQLite, and are never sent to the model. The transparent rule suggests Paced Breathing only when body tension or feeling on edge is selected as “Mostly” or “Very much”; otherwise it suggests STOP. This produces no assessment or conclusion, and the person can always choose either skill. The separate saved chat-personalization path may receive only an application-generated preferred-skill and completed-practice summary after explicit opt-in; it excludes reflection answers, check-in text, location, crisis activity, and identity.
- **Your days** provides a separately marked practice calendar and an optional daily mood choice. A person actively selects one of five labels for a selected date, may revise or remove it, and can clear all entries. The record has no score, free-text note, diagnosis, or effect claim; it is not used to select a practice, passed to the chatbot, or used for Crisis Support.
- Crisis Support is independent from the model and remains reachable during ordinary use, an in-flight optional request, and fallback/failure states. Its U.S. prototype scope and limitations are visible in the interface.

## Measured exercise duration and assumptions

The planned paced-breathing exercise is **60 seconds**: six cycles × (4 seconds in + 6 seconds out). The timer starts only after the first “Breathe in” instruction has rendered and ends after the sixth planned exhale. There is no planned lead-in or closing dwell, so its intended active duration is 60 seconds, within the required 90-second maximum.

This measurement assumes the user does not pause. Pausing is intentionally allowed and can extend wall-clock time, but does not change the planned active exercise or its recorded active duration. The backend rejects any saved duration over 90 seconds.

## Repeatable verification and what it proves

All routine tests use fictional fixtures and `QUIET_STEPS_CHECKIN_MODE=mock`. Exact commands and manual steps are in the linked README.

| Verification | Result | What it proves |
| --- | --- | --- |
| `backend`: `pytest tests -q` | 21 tests passed | A fictional user can complete/leave saved sessions; both skills can be left; optional check-in can be skipped; 91-second records are rejected; SQLite data survives a new FastAPI lifecycle; only the bounded acknowledgement/suggestion is saved; invalid or forced-unavailable model output becomes the fixed fallback. Profile tests verify that only three non-sensitive preferences persist, unexpected reflection data is rejected, and RAG receives only the opted-in practice summary. The daily-mood test accepts only a date plus one label, rejects free text, permits edits/removal, and verifies the chat context excludes mood entries. A standalone greeting receives the fixed app-owned opening without depending on model wording. An explicit reflection request receives the app-owned suggestion without saving or sending response labels to the model, and unsupported labels are rejected. |
| `frontend`: `npm run test` | 26 tests passed | The rendered app verifies the expanding 1-to-4 inhale cue and settling 6-to-1 exhale cue, completes paced breathing only after its planned cycle, permits immediate leaving of paced breathing and STOP even when saving is delayed, skips check-in without a request, discards a late check-in response after leaving, hides unexpected backend-error contents, exposes Crisis Support in normal use, and keeps it reachable while a fictional request waits and after its fallback appears. It also verifies Home adaptation, direct override, preference reset, reduced-motion setting, a non-live accessible breathing cue, selecting/revising/removing/clearing an explicit no-free-text daily mood choice, one-time reflection handoff to chat, and the functional bottom navigation routes. Timing and immutable STOP-sequence tests are included. |
| `frontend`: `npm run build` | Passed | The current Vue application compiles to a production bundle. |
| Manual checklist | Documented; recording/TBD | Provides repeatable human checks for normal and forced-failure mode, persistent SQLite history, and the visible prototype disclosures. It is not a usability or clinical evaluation. |

## What remains unresolved

- Record the Part 3.2 implementation commit SHA above after the first reviewed delivery commit, and attach a recording only if required by the course.
- No user study, usability study, clinical evaluation, or crisis-service validation has been performed.
- The crisis panel is deliberately limited to U.S. prototype information. A real deployment would need independently selected, current resources for its jurisdiction and appropriate review.
- The optional live-model adapter is fictional demo configuration only; it has not been connected to a real provider or used with sensitive information.
- The current test-client dependency emits a deprecation warning from an upstream library. It does not fail the test suite, but should be revisited if this coursework prototype is maintained.
