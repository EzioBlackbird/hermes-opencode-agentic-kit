---
name: gated-project-orchestration
description: Use for software project intake, requirements and design approvals, and gated coding delegation to the local OpenCode workflow runner.
---

# Gated Project Orchestration

## Local installation

Runner directory: `{{RUNNER_DIR}}`.
Python executable: `{{PYTHON_EXE}}`.
Read `OPERATIONS.md` in the runner directory before first use. Verify the runner exists before dispatch. If missing, report a blocker rather than falling back to ungated execution.

## Workflow

1. Read project artifacts before asking questions. Use brainstorming for product ambiguity and ask one high-value question per message.
   One question means one decision, not several questions joined into one sentence. For an unspecified inventory idea, ask only: "Jenis barang apa yang ingin dikelola?" Ask about users and MVP in subsequent turns.
   - **Proactive Reference Scouting & Pre-Design Discovery (REA & CLI-Hub)**:
     - If the user already names a reference app/web/APK, or if the user only provides a concept without naming a reference: once initial intake questions (domain, users, MVP) are clarified, **proactively search and recommend 1–3 top real-world benchmark targets** (live Web App, Desktop/Electron App, or Android APK) that can be inspected with REA (`reverse-engineer-anything`), alongside any relevant CLI harnesses from `cli-hub` (`cli-hub-meta-skill`).
     - Explain clearly what technical facts will be extracted (e.g., data schema, API/IPC contract, offline storage, state transitions, or bundle structure).
     - Upon confirmation, acquire/inspect the target using REA and store all outputs inside `artifacts/discovery/<target>/` (top-level `artifacts/` is excluded from the runner manifest) or an external temp directory to keep the Git baseline clean. Distinguish verified facts, inferences, and residual unknowns, and translate relevant findings into clean architectural specifications inside `docs/design.md` before Gate 2 without copying raw decompiled code.
2. Obtain explicit requirements and design approval separately. Preserve the user's actual text and hash the approved documents. Never reuse pilot approval evidence for a product.
   If an interactive question tool is unavailable or fails (including one-shot CLI mode), ask exactly one direct question in the final response. Leave the requirement unresolved. Do not infer the product domain, users, or MVP from unrelated memories, previous projects, or presumed ecosystem connections.
3. Use writing-plans to create bounded tasks. Contracts must conform strictly to `schemas/contract.schema.json` and runner validation:
   - `approvalFiles` must be an array of exactly 2 relative JSON file paths (e.g., `["docs/approvals/requirements-approval.json", "docs/approvals/design-approval.json"]`). Each approval JSON file must strictly match `{"gate": "requirements"|"design", "decision": "approved", "evidence": "<verbatim string>", "documentHashes": {"<path>": "<sha256>"}}`.
   - `requiredSkills` must be an object mapping valid identifier keys to existing project-relative instruction files (e.g. `{"task-contract-execution": ".opencode/skills/task-contract-execution/SKILL.md"}`), never an array or arbitrary text.
   - `allowedPaths` must only include implementation targets. Control documents (`.git`, `.workflow`, `tasks`, `artifacts`, `docs`) are prohibited in `allowedPaths`. For directory wildcards, use glob suffix `/**` (or ensure trailing `/`) so subdirectories match cleanly.
   - `testStrategy`: When `mode` is `"verification"`, all three arrays (`testFiles`, `failureMarkers`, `redCheckIndexes`) must be strictly empty `[]`. Non-empty lists are only permitted when `mode` is `"tdd"`.
   - `workerCommand` on Windows: Prefer the tested `opencode_worker.py` adapter (`["{{PYTHON_EXE}}", "{{RUNNER_DIR}}/opencode_worker.py", "--executable", "<native-opencode-exe>", "--contract", "tasks/<taskId>.json"]`, adding `--auto` or `--model` only when explicitly chosen). If invoking an npm/batch wrapper directly outside the adapter, wrap with `cmd.exe /c` to avoid `FileNotFoundError: [WinError 2]`.
   - `contextFiles`: Never include implementation files that will be modified by the task in `contextFiles`. Any hash mismatch between dispatch and verify triggers `GateError("Task context changed since dispatch")`. Only include static reference documents or immutable dependencies.
   - No top-level `$schema` field in task JSON contracts (`contract.schema.json` sets `additionalProperties: false`).
4. Verify repository baseline before preflight. The runner requires a valid Git repository and a clean commit hash for `baseRevision`. Ensure `.gitignore` explicitly ignores runner artifacts: `artifacts/`, `.workflow/state.json`, `.workflow/runner.lock`, `.workflow/events/`, `.workflow/accepted/`, and `.workflow/reviews/`. This prevents accepted task records and review files from dirtying `git status` or corrupting manifest comparisons between tasks. Commit the clean baseline.
5. Install project-local executor instructions with `install_project.py --root <project>`. Preserve backups. Commit the inspected baseline and contract.
6. Execute `workflow.py preflight --root <project> --task tasks/<task-id>.json`, then `dispatch` with the same arguments. Always invoke the scripts by absolute path using the Python executable above and native Windows paths.
7. Read the resulting canonical `.workflow/state.json`, artifact report, logs, and measured source changes. A worker report does not prove completion.
   - If worker execution completes successfully (code and tests pass) but fails to generate `report.json` (leaving state as `failed` due to missing `report.json`), inspect `artifacts/<taskId>/<attemptId>/worker.stdout.log` and git diff. You can synthesize a valid `report.json` conforming to `schemas/report.schema.json` with the measured changed files and check evidence, validate via `workflow.validate_report()`, update state status to `ready_for_review`, and proceed to verification without discarding valid code.
   - If a background worker hangs or stalls, inspect its PID via `artifacts/<taskId>/<attemptId>/invocation.json`, check its process status with `Get-Process` (or `tasklist`), and if code/tests are already complete, terminate it explicitly before clearing locks or synthesizing reports.
   - When a worker finished and wrote `report.json` but the runner process terminated before transitioning state out of `in_progress` (leaving `.workflow/runner.lock` behind with an inactive PID):
     1. Verify the lock PID is dead (`tasklist | grep <PID>`), then remove `.workflow/runner.lock`.
     2. Attempting `verify` or `reconcile-report` while state is still `in_progress` will fail (`Attempt is not ready for review` or `Only a file-list mismatch is eligible`).
     3. Check file diff against baseline manifest: ensure no build artifacts (e.g. `.kotlin/errors/*.log` or transient compiler logs) were created outside ignored directories or deleted unexpectedly.
     4. Calculate SHA-256 for all `evidencePaths` declared in `report.json['verification']`. Ensure check command evidence outputs (e.g., test logs) are written to their declared paths beforehand, because verify recalculates their SHA-256 digests against `workerEvidenceHashes`.
     5. Update `.workflow/state.json`: set `workerEvidenceHashes`, `status = report['status']` (typically `"ready_for_review"`), `after = manifest(root)`, `changedFiles = changed`, `workerReport = report`. Clear any `error` key in `state.json`. Persist via `persist(root, state, 'worker_finished')` and update `artifacts/<taskId>/<attemptId>/result.json`.
     6. Now `workflow.py verify` will succeed and execute verification checks cleanly.
   - Review schema validation rule: Review files passed to `workflow.py accept --review <path>` MUST strictly match the full review schema: `taskId`, `attemptId`, `contractHash`, `decision` (must be `"accepted"`), `reviewer` (non-empty string), `rationale` (non-empty string), `findings` (array), and `criteria` (object mapping each acceptance criterion ID from the task contract to `{"passed": boolean, "rationale": string}`). Omitting required keys like `reviewer` or `criteria` will trigger `Workflow blocked: review: expected fields [...]`.
   - For `allowedPaths` path matching in the runner: ensure `workflow.path_matches_scope` supports directory prefix globbing (`/**` and `/`) properly so recursive subdirectory additions/modifications do not raise unexpected `GateError("Out-of-scope change")`.
8. Execute `workflow.py verify --root <project>`. If the runner halts with `Workflow blocked: Project locked`, inspect `.workflow/runner.lock` for the PID; if the previous dispatch/worker process has finished or was terminated, safely remove the stale lock before re-verifying. Inspect source and each acceptance criterion. Record an explicit review file inside `.workflow/reviews/` (e.g., `.workflow/reviews/current.json`) matching the review schema (`taskId`, `attemptId`, `contractHash`, `reviewer`, `decision`, `findings`, `rationale`, and a `criteria` map covering all acceptance criteria IDs with `passed` and `rationale`). Then invoke `workflow.py accept --root <project> --review <relative-review-path>`. Note: Placing review files outside `.workflow/` (like `reviews/*.json`) causes `workflow.py accept` to fail with "Source changed since worker review" because untracked root-level files alter the source manifest.
   - After acceptance, commit the implementation files (`git add native/ ... && git commit -m "feat(...): ..."`) to keep the repository clean before drafting the next task contract. When writing a new task contract (`tasks/T00X.json`), set `baseRevision` to the latest commit hash (the accepted implementation commit), and commit the new task contract file before executing `workflow.py preflight` to satisfy the clean baseline requirement.
9. Use `recover --reason <inspected-resolution>` only after inspecting failed or interrupted work. Never discard partial changes or clear a lock while its processes may be active.
10. Kanban is a projection: configure an explicit board/ticket mapping. Terminal transitions are opt-in. Never start a native Kanban worker for a task already owned by this runner.

## Boundaries

- For projects using this workflow, direct `opencode run` is not a substitute for dispatch through the runner.
- Diagnose repository facts directly; escalate product behavior, public API changes, and scope expansion to the user.
- Model routing comes from the selected OpenCode agent unless the contract records an explicit override. Do not inject stale provider preferences.
- TDD mode requires prewritten behavioral tests and a runner-recorded red checkpoint; do not claim verified TDD for verification-mode tasks.
- Human approval records are evidence, not cryptographic identity enforcement. File scope is checked after execution, not sandboxed.
- Reverse-engineering (REA) is strictly a Discovery tool for specs, protocols, and data formats; it must never bypass Requirements/Design approvals or inject raw decompiled code into worker tasks.
- For tasks building or modifying CLI harnesses, enforce the CLI-Anything 7-phase methodology (`HARNESS.md`), including real backend verification in `TEST.md` and `SKILL.md` generation.