# Part 3.1 — Research and Design Report

## Submission identifiers

- Repository URL: [github.com/Isabellegerhart11/assignment-3](https://github.com/Isabellegerhart11/assignment-3)
- Submitted Part 3.1 package commit: [`70879e20edf1e303030e246460d85864adc8cf62`](https://github.com/Isabellegerhart11/assignment-3/commit/70879e20edf1e303030e246460d85864adc8cf62)
- Submission reference tag: [`part-3.1-submission`](https://github.com/Isabellegerhart11/assignment-3/tree/part-3.1-submission), which resolves to the submitted package commit above.
- Design file: [Quiet Steps Figma design](https://www.figma.com/design/dDWNzyxOVEEoOPLYcuiLr2/Assignment3?node-id=1-3)

## Linked evidence and design documents

- [Design rationale and flow](docs/design.md)
- [Curated, redacted evidence log](docs/evidence.md)
- [AI-use disclosure](AI-USE.md)
- [Project and handoff notes](README.md)
- [Instructions for future coding work](AGENTS.md)

No recording was needed for this research-and-design milestone because no working application or interactive prototype was submitted. The Figma design and the evidence log are the verification evidence.

## What is complete

The proposed mobile experience, **Quiet Steps**, is documented and designed in Figma. It provides a user-controlled choice between a 60-second paced-breathing practice and a STOP skill. The design includes an optional check-in, a breathing screen, a one-step-at-a-time STOP screen, a completion/history screen, and crisis-support access that is visible throughout the experience.

The design intentionally presents a skills-practice prototype rather than therapy, diagnosis, monitoring, or emergency support. It includes clear exit controls, low-stimulus copy, and a persistent safety path. The full flow, model boundaries, data plan, research/design connections, personalization approach, and unresolved questions are in [docs/design.md](docs/design.md).

## What the evidence shows

The evidence log records the selected prompts and decisions that produced the Figma design. A structural review confirmed the six named Figma screens, and a visual review confirmed the entry screen's hierarchy, full-width primary action, readable content, and visible crisis-support control. The log also records a revised component approach after the original editable text-property approach was unsupported by the Figma API.

## What remains unresolved

- Verify every screen visually after the Figma connector's preview limit resets.
- Decide the exact region-appropriate crisis resources before implementation.
- Test the copy, STOP sequence, and optional check-in with intended users and revise based on findings.
- Confirm whether optional device-local history is desirable and provide a clear delete/reset control if it is retained.
