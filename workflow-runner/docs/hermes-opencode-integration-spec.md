# Hermes–OpenCode Gated Workflow Specification

Version: 0.1.0
Date: 2026-10-24
Status: Draft for design approval
Input: `hermes-opencode-audit.md`

## 1. Decision record

The user approved the minimum integration direction: aligned Hermes instructions, task contracts, OpenCode execution skills, delegation validation, and a canonical project status source. That approval authorizes preparation of this specification. It is not approval of this specification or authorization to alter live configuration.

## 2. Goal and acceptance criteria

Enable the user to provide a product idea while Hermes clarifies, obtains approval, plans, delegates to OpenCode, verifies evidence, and accepts completed tasks.

The pilot succeeds when:

1. Missing or stale requirements/design approval prevents worker invocation.
2. A valid contract starts exactly one active attempt for the project.
3. OpenCode produces a machine-readable report tied to the contract and source revision.
4. Failed verification, missing evidence, or an out-of-scope change prevents acceptance.
5. Hermes independently reruns required acceptance checks against the reviewed source and records the result.
6. Interrupted attempts can be inspected and resumed without silently duplicating execution.
7. Kanban synchronization failure does not change authoritative task status.
8. One vertical slice runs end-to-end, with reproducible setup and verification instructions.

## 3. Scope

### Included

- Local Windows execution, initially one project and one worker attempt at a time.
- Existing Hermes methodology skills, adapted delegation instructions, and narrowly scoped OpenCode process skills.
- Versioned project contracts, approvals, reports, reviews, and evidence.
- A local runner/validator with preflight, execution capture, postflight, and acceptance operations.
- Git-based source identity in a dedicated pilot repository.
- Kanban projection keyed by project ID and task ID.

### Deferred

- Parallel workers, automatic merging, multi-machine execution, automatic deployment, and dynamic model routing.
- A dashboard, custom OpenCode plugin, or replacement for existing Hermes/OpenCode infrastructure.
- OS-level filesystem isolation. Allowed paths are a worker instruction and postflight acceptance check in this version, not a sandbox guarantee.

## 4. Responsibility and decision boundaries

| Actor | Authority |
| --- | --- |
| User | Approves requirements and design; decides product scope and material changes |
| Hermes | Clarifies, plans, issues contracts, records approval evidence, delegates, reviews, and requests acceptance |
| OpenCode | Implements within the contract, verifies, and submits a report or blocker |
| Runner | Validates artifacts, controls attempt lifecycle, captures evidence, checks transitions, and writes authoritative state |
| Superpowers | Supplies methodology; does not own project status or grant approval |

Hermes asks one high-value question at a time for unresolved product decisions. It investigates technical facts using the repository and documentation. OpenCode may choose internal implementation details consistent with approved architecture and repository conventions.

OpenCode escalates changes to product behavior, dependencies, public interfaces, database migrations, or files outside the contract when not already authorized. A worker report cannot approve its own work.

Hermes may perform inspection and small diagnostic/verification scripts. Production project implementation is delegated to OpenCode. Diagnostic scripts that become shipped product code require a task contract.

## 5. Project artifacts and authority

```text
project/
  docs/
    00-idea.md
    01-requirements.md
    02-prd.md
    03-architecture.md
    04-api-contract.md
    05-plan.md
    adr/
  tasks/
    T-001.json
  .workflow/
    project.json
    state.json
    approvals/
    reviews/
    events/
    locks/
  artifacts/
    T-001/
      attempt-001/
        invocation.json
        events.jsonl
        stdout.log
        stderr.log
        report.json
        source-diff.patch
        checks/
```

`tasks/*.json` defines task contracts. `.workflow/state.json` is the authoritative current state, written atomically by the runner under a project lock. Events explain transitions; they are not a second editable status source. Markdown plans and Kanban reflect state and reference the same task IDs.

Track specifications, contracts, approval records, and review records in Git. Ignore runtime locks and bulky raw logs; retain evidence locally for the project lifetime and export it with handoff. Evidence hashes in review records detect missing or changed evidence. Repository ignore rules do not exempt unexpected ignored source files from scope inspection.

The worker's editable scope excludes `.workflow/`, task contracts, and approved documents unless a separately approved task explicitly authorizes a document change. Report output is restricted by contract to its attempt directory. The runner checks control-artifact hashes before and after execution. This detects mutation but does not create a hostile-worker security boundary.

## 6. Approval gates

### Requirements approval

Requires confirmed users, MVP behavior, non-goals, critical constraints, acceptance criteria, and resolution of critical assumptions.

### Design approval

Requires approved requirements plus PRD, architecture, relevant API contract, testing strategy, and deployment/environment assumptions. An API contract may be explicitly marked not applicable with a reason.

### Approval record

Each record contains `schemaVersion`, `approvalId`, `gate`, `documentHashes`, `decision`, `recordedAt`, and `evidence` with the user message reference and exact approval text. `recordedBy` identifies Hermes as recorder, not as the approving user.

Hash document bytes with SHA-256. Any change to a covered file makes that approval stale. Editorial changes may use a short renewed approval; the runner does not infer that changes are immaterial. Missing records, missing files, or mismatched hashes block dispatch.

A task contract binds both approval IDs and its own content hash. A material requirement/design change invalidates dependent tasks' readiness. Previously accepted history remains preserved, but changed requirements require explicit impact analysis and follow-up tasks.

## 7. Task contract v1

The implementation must provide strict schemas with unknown fields rejected and helpful field-level errors.

| Field | Requirement |
| --- | --- |
| `schemaVersion` | Supported contract version |
| `projectId`, `taskId`, `title` | Stable identity and concise intent |
| `objective` | Observable result |
| `approvalIds` | Current requirements and design approvals |
| `contextFiles` | Existing project-relative source documents |
| `dependsOn` | Task IDs already accepted |
| `baseRevision` | Exact Git commit expected at dispatch |
| `allowedPaths` | Explicit project-relative files or directory prefixes; no ambiguous glob rules in v1 |
| `acceptanceCriteria` | Unique criterion IDs and measurable expectations |
| `requiredSkills` | Exact skill IDs whose availability/loading must be confirmed |
| `testStrategy` | `tdd`, `regression`, `integration`, `visual`, `documentation`, or `configuration`, with rationale |
| `verification` | Check IDs, executable, argument array, relative working directory, timeout, and criterion IDs |
| `execution` | Explicit agent, optional model override, overall timeout, and maximum attempts |
| `reportPath` | Attempt-local output location assigned at dispatch |
| `nonGoals` | Explicit excluded behavior |

Use structured argument arrays instead of shell-concatenated commands. Resolve paths against the canonical project root; reject absolute paths in relative fields, traversal, alternate data streams, and paths escaping through junctions or symbolic links. Compare Windows paths with platform-appropriate case handling.

Acceptance criteria must be covered by a command or a declared review procedure. An arbitrary successful command is not sufficient proof of a criterion.

## 8. Lifecycle

```text
draft -> ready -> running -> ready_for_review -> accepted
                   |              |
                   |              +-> changes_requested -> ready
                   +-> blocked -> ready
                   +-> failed -> ready
                   +-> interrupted -> ready
```

- `draft -> ready`: valid contract, current approvals, accepted dependencies, usable environment.
- `ready -> running`: project lock acquired, baseline verified, attempt ID allocated, invocation recorded.
- `running -> ready_for_review`: valid worker report, complete evidence, postflight passed.
- `running -> blocked`: worker identifies a missing decision/prerequisite; partial changes are recorded.
- `running -> failed`: execution/check/report validation failure.
- `running -> interrupted`: timeout, cancellation, or lost process without confirmed completion.
- `ready_for_review -> accepted`: independent verification and review pass on the exact final source identity.
- `ready_for_review -> changes_requested`: review findings require correction.
- Returning to `ready` requires a recorded resolution, inspected workspace, valid approvals, and a new attempt ID.

No automatic retry after interruption. Check process status and partial artifacts first. Never silently reset, clean, or discard work. Default maximum attempts: three total per task; increasing this requires a recorded Hermes decision and explanation. Product decisions still go to the user.

## 9. Execution protocol

### Preflight

1. Load and validate project configuration, contract, state, and approval evidence.
2. Verify all document hashes, dependencies, skills, and executable availability.
3. Require a dedicated Git workspace with clean source baseline and matching `baseRevision`; approved runtime artifacts are excluded from cleanliness checks.
4. Resolve effective agent/model settings and record requested configuration. Do not claim an upstream model identity unless runtime evidence supplies it.
5. Acquire an exclusive project lock and create the attempt directory before invoking OpenCode.

### Invocation

Use a native Windows-compatible invocation of the installed OpenCode executable with a bounded prompt and attached contract/context. The installed CLI supports `--format json`, `--file`, `--session`, `--agent`, and `--model`; verify precise behavior during implementation.

Capture CLI events as transport evidence. CLI JSON output is not the task report schema. Record session identity when emitted, command exit code, timestamps, executable version, and hashes of inputs. Avoid shell quoting by using a subprocess argument list.

The existing `--auto` behavior must be an explicit runner policy rather than an accidental wrapper default. It does not validate approval or enforce file scope. This version's gate guarantees apply to invocations through the runner; direct CLI use can bypass them.

### Postflight

1. Confirm process termination and collect exit status/output.
2. Validate worker report identity, schema, contract hash, evidence paths, and evidence existence.
3. Inspect tracked, deleted, renamed, untracked, and unexpected ignored files; compare control-artifact hashes and source changes against allowed scope.
4. Save the patch and a source manifest with SHA-256 hashes, including relevant untracked files. Baseline commit plus final manifest identifies uncommitted results; a commit hash alone does not.
5. Record status. Out-of-scope changes block review readiness and remain available for inspection.

### Independent acceptance

Hermes requests runner-owned acceptance checks against the final source manifest. Check stdout/stderr, exit codes, semantic assertions, and required manual/visual review. Compare source identity again after checks; any source change invalidates the review and requires re-verification.

The review record contains reviewer identity, criterion-level decisions, findings, check evidence hashes, reviewed source identity, and final decision. Only runner-mediated acceptance updates the canonical state. Kanban is updated afterwards and synchronization errors are recorded separately.

## 10. Worker report v1

Required fields:

- `schemaVersion`, `projectId`, `taskId`, `attemptId`, and `contractHash`.
- `status`: `ready_for_review`, `blocked`, or `failed`.
- `summary` and `changedFiles`.
- `verification`: check ID, exact command/arguments, exit code, evidence path, and outcome.
- `criteria`: criterion ID, claimed outcome, and evidence references.
- `blockers`, `changeRequests`, and `remainingConcerns`, including empty arrays when absent.
- `tddEvidence` when the strategy is TDD: failing test evidence before production changes, passing evidence afterwards, and relevant source snapshots.

Runner-measured source changes and exit codes take precedence over worker claims. Missing checks are `not_run`, not passed. A nonzero process exit cannot yield automatic acceptance even if a partial report claims success.

For TDD, an initial failure must exercise the intended missing behavior, not merely a broken import or test environment. Test validity is reviewed. Timestamped worker logs alone do not establish order reliably; the runner should capture separate red and green checkpoints with source snapshots. Where ordering cannot be established, report it as unverified.

## 11. Skills and instruction alignment

### Hermes

- Preserve existing `brainstorming`, `writing-plans`, `systematic-debugging`, verification, and review methodology.
- Adapt the existing OpenCode delegation skill to call the runner and interpret reports.
- Add a focused `gated-project-orchestration` skill covering gates, artifacts, status authority, and escalation.
- Reconcile `SOUL.md` decision boundaries, tracking paths, CLI examples, and model-routing instructions.
- Use exact runtime skill IDs rather than assuming `superpowers:` namespace syntax works on every host.

### OpenCode

- Add `task-contract-execution`: preflight reading, bounded implementation, blockers, and change requests.
- Add `structured-handoff`: report schema and evidence requirements.
- Adapt relevant existing Superpowers TDD/debugging/verification instructions for the executor role after reviewing portability and license requirements.
- Load technical stack skills only when relevant to the task.

Do not import orchestrator brainstorming requirements into a worker already executing an approved contract. Missing skills are a preflight blocker; installation or substitution is recorded explicitly.

## 12. Model and configuration policy

Use existing OpenCode agent configuration as the default authority. Hermes must not inject a conflicting model preference from stale instructions. Record any task-specific override in the contract. Route health and actual provider behavior remain implementation-time checks.

Make changes narrowly scoped and backed up. Preserve unrelated user instructions, providers, keys, and project preferences. Resolve the actual Hermes home and effective profile before modification. Credentials remain in existing credential storage and are never copied into task artifacts or logs.

## 13. Pilot and verification matrix

Recommended pilot: a local task-list vertical slice supporting create and list through a UI, API, and persistent storage. Stack selection occurs during pilot requirements approval; it is not implicit approval of a framework.

| Scenario | Expected result |
| --- | --- |
| Requirements approval absent | No OpenCode invocation |
| Approved document edited | Stale approval blocks dispatch |
| Dependency not accepted | Task remains unstarted |
| Required skill unavailable | Actionable preflight failure |
| Two dispatch requests | Only one active attempt |
| Invalid or missing report | Task fails validation |
| Worker says passed but command fails | Acceptance rejected |
| Worker edits out-of-scope/control file | Acceptance rejected; diff retained |
| Worker edits untracked/ignored source | Changes included in scope assessment |
| Source changes after review | Previous review cannot accept new source |
| Timeout with partial work | Interrupted state; inspection before retry |
| Kanban unavailable | Canonical state retained; sync pending |
| User asks for scope change | Contract/design impact assessed before continuation |
| Valid end-to-end slice | Independent checks and review permit acceptance |

Use deterministic runner tests for gates and lifecycle behavior, then one real model-backed pilot. Avoid paying for model runs to test pure validation logic.

## 14. Implementation sequence after approval

1. Verify effective Hermes profile, terminal backend, executable resolution, skill resolution, and CLI event/report behavior.
2. Select a dedicated integration repository and create schemas, runner, and deterministic verification tests.
3. Implement approval binding, state transitions, locks, process capture, source manifests, report validation, and acceptance checks.
4. Add/adapt skills and reconcile live instructions with backups and explicit rollback paths.
5. Connect Kanban projection using verified local interfaces.
6. Run failure scenarios and the isolated vertical-slice pilot.
7. Publish setup, usage, evidence, known limitations, and rollback instructions.

Recommended runner technology: Python standard library for process/filesystem operations, with a maintained JSON Schema validator dependency selected during implementation. The locally verified Python installation makes this practical; a dedicated virtual environment prevents changes to Hermes dependencies.

## 15. Design approval requested

Approval of this document accepts the proposed authority model, serial execution, project artifacts, gate semantics, testing policy, and phased implementation. It does not approve any future product's requirements or design. Pilot requirements and design remain separate gates.
