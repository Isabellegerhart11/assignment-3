# Project guidance for coding agents

## Project purpose

This repository currently documents **Quiet Steps**, a coursework design for a short, user-controlled skills-practice prototype. Do not present it as therapy, diagnosis, clinical monitoring, or emergency support.

## Product boundaries

- Keep crisis support visible and independent of any optional AI/check-in feature.
- Keep check-in optional; a user must be able to continue without writing anything.
- Prefer one small action per screen during a skill exercise.
- Include an obvious leave/stop control during every practice.
- Use neutral, non-judgmental, low-stimulus language.
- Do not store free-text check-ins, location, crisis use, or sensitive health data by default.

## Proposed model boundary

If a model is added later, constrain its output to a neutral acknowledgement plus a suggestion selected from an approved allowlist. It must not diagnose, give therapy or medical advice, assess risk, make treatment claims, or control safety routing.

## Documentation discipline

- Keep `report.md`, `AI-USE.md`, `docs/design.md`, and `docs/evidence.md` current.
- Record only curated, redacted evidence. Never add credentials, participant data, private messages, personal contact details, or full chat exports.
- Clearly separate completed work from proposed work and unresolved questions.
