---
name: Task Contract Execution
description: Execute a delegated engineering task with approved requirements, bounded file scope, explicit acceptance checks, and evidence-backed escalation.
---

# Task Contract Execution

1. Read the supplied task contract and referenced requirements/design before editing.
2. Confirm that the runner validated approvals and assigned a task ID, attempt ID, and contract hash. If missing, return a blocker rather than implementing.
3. Load the exact relevant technical and testing skills required by the contract. Report unavailable skills.
4. Implement only the authorized behavior and paths. Never edit approvals, task definitions, runner state, or acceptance criteria to make the work pass.
5. Follow the specified test strategy. For TDD, obtain a meaningful failing test checkpoint before production changes and a passing checkpoint afterwards.
6. Run required checks; preserve actual output. Distinguish failed, passed, and not-run checks.
7. If implementation requires a broader scope or a product decision, report the reason and requested change to Hermes. Do not silently expand the task.
8. Use `structured-handoff` to submit results. The worker may request review but cannot accept its own task.

Do not restart product brainstorming for a valid approved contract. Resolve technical facts by inspection; route product ambiguities through Hermes.
