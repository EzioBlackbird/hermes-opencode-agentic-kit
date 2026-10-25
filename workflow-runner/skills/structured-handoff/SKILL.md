---
name: Structured Handoff
description: Report delegated coding results with task identity, actual verification evidence, unresolved blockers, and review-ready status.
---

# Structured Handoff

Use the exact report schema supplied by the runner. Never infer schema fields from this skill when a versioned schema is available.

- Preserve task ID, attempt ID, and contract hash verbatim.
- Report changed files and observable behavior.
- Associate every acceptance criterion with actual evidence or an explicit unresolved status.
- Record exact commands, exit codes, and evidence paths; do not reconstruct successful output.
- Include blockers, scope-change requests, and remaining concerns.
- Submit `ready_for_review` only when required worker checks pass. Otherwise submit `blocked` or `failed` as supported by the contract.
- Write only to the assigned report path. Never modify runner-owned state or approval records.
- Do not claim final acceptance, independent review, or verified TDD ordering without the corresponding runner evidence.
