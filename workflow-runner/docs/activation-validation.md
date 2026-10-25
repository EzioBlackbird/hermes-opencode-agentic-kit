# Stable installation and Hermes intake validation

Date: 2026-10-25

- Stable runner installed at `~/Jarvis/hermes-opencode-workflow`.
- Active Hermes orchestration skill points to this location instead of scratch.
- Executed the complete deterministic suite from the stable directory: 48 tests passed.
- Real Hermes one-shot intake test correctly refused to start coding before requirements/design approval but initially inferred a business domain from prior memories.
- Updated the orchestration skill to leave unanswered requirements unresolved and ask directly when interactive questions are unavailable.
- A second real Hermes intake response left the domain unresolved and confirmed that coding was blocked. It bundled domain/users/MVP into one sentence; instructions were further clarified to require one decision per question. That final phrasing refinement has not been retested.
- These tests explicitly instructed Hermes not to implement or delegate. They establish observed intake behavior, not an autonomous full Hermes-to-OpenCode project run.

## Follow-up live checks

- A third one-shot intake response asked only: `Jenis barang apa yang ingin dikelola?` It left approvals unresolved and described the subsequent requirement/design gates.
- A real Hermes read-only audit reported executing the stable runner's `status` command, inspecting the accepted pilot record, review, and logs, and distinguishing the 17 passing application tests from the single verification command. The audit explicitly did not claim that all orchestration behaviors had been exercised.
- The audit identified that browser observations were stored outside the pilot. A copy was added to `artifacts/T001/1792904685773968500/browser-verification.md`, SHA-256 `b783d1d4acb8652ca903cca9cc28884a6f10680d49503c2f6c0e702a4f8b7d95`. This is a supplemental observation record, not retroactively bound evidence in the historical acceptance record.
- No implementation was delegated during these follow-up checks. Full autonomous Hermes-led project execution remains a separate unperformed test.

Full-stack pilot acceptance and Kanban terminal projection were verified separately, as documented in OPERATIONS.md. Historical pilot contracts still reference their original runner path and must not be silently rewritten after acceptance. New tasks should use the stable installation.
