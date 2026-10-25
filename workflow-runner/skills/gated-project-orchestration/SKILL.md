---
name: Gated Project Orchestration
description: Coordinate requirements approval, design approval, contracted OpenCode execution, independent verification, and explicit task acceptance.
---

# Gated Project Orchestration

1. Read existing project artifacts and canonical state before asking questions or dispatching work.
2. Resolve product ambiguity one high-value question at a time. Investigate repository facts directly. When the user presents a concept without naming a reference product (or names an existing reference), proactively scout and recommend 1–3 matching real-world Web/Desktop/APK targets for REA (`reverse-engineer-anything`) inspection and check `cli-hub` (`cli-hub-meta-skill`) before finalizing `docs/design.md` (storing discovery outputs in `artifacts/discovery/<target>/`).
3. Record requirements approval and design approval separately, each with exact user evidence and document hashes.
4. Prepare a bounded task contract with dependencies, allowed paths, acceptance criteria, required skills, and verification commands.
5. Delegate production implementation through the validated runner. Never treat a direct CLI invocation as equivalent to a gated run.
6. Inspect worker evidence and changed-file scope. Rerun acceptance checks against the exact reviewed source.
7. Record criterion-level review before requesting acceptance. A worker completion event is not acceptance.
8. Synchronize Kanban after canonical state changes. Preserve canonical state when synchronization fails.
9. On interruption, inspect active processes and partial results before retrying. Escalate unresolved product changes to the user.

Only use runner capabilities that have actually been implemented and verified. If a required gate is unavailable, identify it as a blocker rather than simulating enforcement.
