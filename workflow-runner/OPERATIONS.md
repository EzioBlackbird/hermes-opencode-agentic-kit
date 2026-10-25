# Local Workflow Operations

## Scope of this delivery

The runner is a working serial execution integration with project-local skills, prerequisite checks, explicit approval records, measured file scope, independent checks, explicit acceptance, and a tested OpenCode adapter. It is not a security sandbox or a complete implementation of every item in the approved architecture.

## Install into an existing project

Use Python 3.10 or newer, Git, the installed OpenCode CLI, and `jsonschema` from `requirements.txt`. The inspected Python environment already had jsonschema 4.26.0; no package installation was performed. For a new environment, install requirements in a dedicated virtual environment.

```powershell
python install_project.py --root C:/path/to/project
```

The installer writes two project-local OpenCode skills and `.workflow/instructions/gated-project-orchestration.md`. Existing differing files are backed up under `.workflow/install-backups/<timestamp>/`; a manifest records installed hashes. Hermes must explicitly read the orchestration instruction file when starting work in this project. This installation does not automatically reroute every Hermes conversation.

Rollback: inspect the manifest; restore each previously existing file from the adjacent backup path. For newly created files, remove only those whose current hash still matches `installedHash`, after obtaining any locally required deletion approval. Do not overwrite subsequent user edits.

## Define the contract

Use the generated integration pilot's `tasks/T001.json` as a concrete working example. Required keys are validated with unknown keys rejected:

- `schemaVersion`: integer `1`.
- `projectId`, `title`, `objective`: project identity and concrete task intent.
- `contextFiles`: existing project-relative reference files, hash-bound at dispatch.
- `nonGoals`: explicitly excluded behaviors.
- `taskId`: letters, digits, and hyphens, maximum 64 characters.
- `baseRevision`: Git baseline commit. A subsequent metadata-only commit may contain the tracked contract.
- `approvalFiles`: requirements and design approval records, each binding document hashes and actual approval evidence.
- `allowedPaths`: exact project-relative paths or directory prefixes ending in `/`.
- `verification`: nonempty executable/argument arrays.
- `workerCommand`: Python, absolute `opencode_worker.py` path, `--executable`, native OpenCode executable, `--contract`, task path, and explicitly chosen optional flags.
- `timeoutSeconds`: 1–3600.
- `dependsOn`: prerequisite task IDs.
- `acceptanceCriteria`: unique ID, description, and zero-based `checkIndexes` for each criterion.
- `requiredSkills`: exact skill IDs mapped to project-relative instruction files.

Do not use the fixture's approval evidence for another product. Record that user's actual requirement/design decisions.

Commit the project baseline and contract. Ignore runtime `artifacts/`, `.workflow/state.json`, `.workflow/runner.lock`, and `.workflow/events/`. Retain approvals, contracts, and acceptance records. Formatter caches may appear even when ignored by Git; authorize a specific cache directory only when appropriate. The runner intentionally inspects ignored files.

## Execute and review

```powershell
python workflow.py preflight --root C:/path/to/project --task tasks/T001.json
python workflow.py dispatch --root C:/path/to/project --task tasks/T001.json
python workflow.py verify --root C:/path/to/project
python workflow.py accept --root C:/path/to/project --review .workflow/reviews/T001.json
```

Hermes reads the measured diff/source, independent logs, and criteria before writing the review. A review contains exact task/attempt/contract identities, reviewer, accepted decision, empty unresolved findings, rationale, and a decision/rationale for each criterion. It cannot skip independent verification.

On failure, inspect logs and the workspace, resolve the issue, record `recover --reason`, and commit the inspected recovery baseline before redispatch. Never clear a lock without first checking that its owning process and children have stopped. The runner does not automatically discard partial work.

## Verified live integration

Pilot: `~/AppData/Local/Temp/opencode/workflow-integration-pilot-20261025`.

- Attempt `1792884818303866800`: OpenCode implemented `sum_even`; scope validation rejected formatter-created `.ruff_cache` files.
- The implementation was inspected and preserved, the specific cache path was authorized, and recovery was recorded.
- Attempt `1792884976961734600`: `ready_for_review` → `verified` → `accepted`.
- Independent `python -B check.py`: exit 0, checking empty input, positive parity, zero, and negative values.
- Final transport: 124 events, zero malformed lines, zero error events.
- Session: `ses_e8fba5110ffeS7fxlVjsNN1S7Q`.

This validates a bounded integration fixture. It is not the planned UI/API/database vertical slice and does not prove TDD ordering.

## Remaining architecture gaps

- A runner-owned red checkpoint is implemented for prewritten behavioral tests. It captures nonzero results before worker dispatch, requires expected failure markers, rejects common import/syntax failures, binds test hashes, and compares the source manifest before dispatch. Independent verification supplies green evidence. Automated tests cover this path; the real-model fixture used verification mode, so it does not prove a real-model TDD run. Test authorship and semantic quality still require review.
- Kanban defaults to comments. Explicit `syncStatus: true` additionally maps accepted to complete and failed/blocked/interrupted/changes_requested to needs-input blocked via official CLI commands, without force. Running, ready, and review states remain comments because native transitions may claim or dispatch workers. Real-board mutations have not been tested; adapter transitions are covered by mocks.
- Contracts/reports have published Draft 2020-12 schemas in `schemas/`, enforced at runtime. These cover the current operational format; additional architecture fields such as project identity, context references, and worker evidence references remain to be incorporated.
- Approvals are recorded evidence, not authenticated human signatures; control files are checked, not OS-protected.
- Crash-consistent recovery, process identity checks after machine restart, large dependency/cache exclusions, and cross-project task history require further work.
- Hermes now has a targeted global routing section and a precedence note in its OpenCode delegation skill. Discovery confirms the new orchestration skill is enabled; live conversational compliance has not been tested. The runner still resides in the scratch directory and must be checked for availability.
- The full-stack product pilot requires its own requirements and design approvals.

These gaps are not hidden behind successful unit tests or the fixture acceptance.

## Live Kanban terminal projection validation

On 2026-10-25, the official Hermes CLI created board `workflow-integration-20261025` and ticket `t_b1ad9716` with initial status `blocked`, no assignee, and no worker session. The projection adapter published the accepted pilot snapshot and completed the ticket. A separate `hermes kanban --board workflow-integration-20261025 show t_b1ad9716 --json` confirmed status `done`, the expected task/attempt result, the fingerprinted comment, and `worker_pid: null`. The active board was not switched.

This verifies the accepted-to-done transition on a real local board. Other transitions and dispatcher interactions retain their stated limits.

## Hermes activation record

## Full-stack pilot execution checkpoint

Final update: task T001 reached `accepted` on attempt `1792904685773968500`. Source review requested an OPTIONS/HEAD correction, which OpenCode implemented with regression tests. Independent verification passed 17 tests. The third worker report omitted authorized cache files; `reconcile-report` preserved the original and generated a measured corrected file list, followed by independent verification and explicit review. No fourth worker attempt was launched. Review: `.workflow/reviews/T001.json`; immutable attempt evidence: `artifacts/T001/1792904685773968500/`. Earlier checkpoint paragraphs below describe the preceding state.

The runner regression suite now has 48 passing tests. `reconcile-report --reason` is restricted to failed file-list mismatches, checks scope and bindings again, preserves the original report, and returns only to review-ready, never directly to accepted.

The user approved the pilot requirements/design by replying `Lanjut` to the explicit approval request. A dedicated repository was prepared at `~/AppData/Local/Temp/opencode/fullstack-workflow-pilot-20261025`. The current runner dispatched real OpenCode execution with both approved documents and required skill attachments.

Attempt one produced the Python/SQLite/static-frontend implementation but was rejected for Python bytecode cache outside the allowlist. The partial implementation was preserved and committed; explicit cache scope and recovery were recorded. Attempt two reached `ready_for_review`, followed by independently rerun API/database tests reaching `verified`.

Browser interaction, mobile viewport inspection, final source review, and product acceptance are still outstanding. `verified` is not `accepted`.

On 2026-10-25, installed `skills/software-development/gated-project-orchestration/SKILL.md` under the active Hermes home. Added a targeted gated-project routing section to `SOUL.md` and a precedence note to `skills/autonomous-ai-agents/opencode/SKILL.md`. `hermes skills list` reports the orchestration skill as local and enabled.

Pre-change copies are in `~/AppData/Local/hermes/backups/workflow-activation-20261025/` (`SOUL.md` and `opencode-SKILL.md`). Restore those exact files to their original locations to roll back routing, after checking for subsequent user edits. The new skill can remain installed without the routing changes. This is configuration/discovery verification, not an end-to-end Hermes conversation test.
