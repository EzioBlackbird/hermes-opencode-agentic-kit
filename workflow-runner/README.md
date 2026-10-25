# Gated Workflow Runner — Development Checkpoint

This directory contains a tested serial runner and OpenCode adapter. A real contracted coding fixture has reached accepted status after independent verification. It is not the complete approved architecture and must not silently replace the global delegation wrapper. See `OPERATIONS.md` for current usage, live evidence, installation, rollback, and remaining gaps. Latest deterministic suite: 38 passing tests.

## Run checks

```powershell
python -m unittest -v
python workflow.py --help
```

## Implemented

- Requirements/design approval hash validation before dispatch.
- Git baseline and cleanliness checks.
- Exclusive project execution lock.
- Structured subprocess arguments, bounded execution, and separate output logs.
- Worker report identity binding.
- Postflight file-scope checks and workflow JSON mutation detection.
- Independent verification with source-manifest comparison.

The `verified` result is an intermediate status, not task acceptance. The `accept` command requires an explicit review bound to the attempt and contract, unchanged approvals/source, unchanged independent-check evidence, and a passing review for every acceptance criterion.

## Review and recovery

```powershell
python workflow.py verify --root C:/path/to/project
python workflow.py accept --root C:/path/to/project --review .workflow/reviews/current.json
python workflow.py recover --root C:/path/to/project --reason "Inspected failed attempt and resolved its blocker"
```

The review object requires `taskId`, `attemptId`, `contractHash`, `reviewer`, `decision`, `findings`, and `rationale`. Acceptance requires `decision` equal to `accepted`, an empty findings array, and nonempty reviewer/rationale. The runner records transition snapshots under `.workflow/events/`. Attempts are capped at three for the current task; failures require explicit recovery. A stale lock is intentionally not removed automatically.

Twenty deterministic tests cover dispatch, verification, explicit acceptance, evidence tampering, approval changes, recovery, dependency gates, criterion coverage, prerequisite invalidation, and two serial tasks. These use local Python worker fixtures, not a live OpenCode model.

## Criteria and dependencies

Contracts must include `dependsOn` (an array of prerequisite task IDs) and `acceptanceCriteria` (a nonempty array). Each criterion has a unique `id`, a nonempty `description`, and `checkIndexes` referring to the zero-based entries of `verification`. Every criterion must reference at least one existing check.

Reviews must include `criteria`, an object keyed by every criterion ID with exactly `passed` and `rationale` for each. Acceptance requires `passed: true` and a nonempty rationale for all criteria. Accepted task records are retained under `.workflow/accepted/<taskId>.json`.

Prerequisite validation recursively checks acceptance status, contract identity/hash, current approval document hashes, approval-record hashes, and referenced test-evidence hashes. Cycles are rejected. A new approval does not retroactively validate an old acceptance: the changed prerequisite needs a new reviewed acceptance. Historical records are retained rather than rewritten to hide invalidation.

For serial tasks, commit the accepted source and workflow records before dispatching the next task. Pin the next contract to that baseline. The test suite verifies this sequence with two local worker attempts.

## Outstanding specification work

### Optional Kanban terminal-state synchronization

Set `syncStatus: true` in the explicit Kanban mapping to publish accepted as `complete` and failed/blocked/interrupted/changes_requested as `block --kind needs_input`. Commands never use `--force`. Other states remain comment snapshots to avoid activating a second worker through the native dispatcher. A transition failure records pending synchronization without changing canonical task state. Fingerprints now include destination board, ticket, and synchronization mode. Current suite: 47 passing tests; real-board mutations remain untested.

### Worker evidence binding

Each worker verification entry now requires nonempty `evidencePaths` containing project-relative paths to existing `.log` files inside that attempt's artifact directory. Dispatch measures hashes and later review/acceptance revalidates them. Adapter instructions require actual command output, not reconstructed logs. Worker evidence is still untrusted self-report and never replaces independent checks. The deterministic fixture explicitly labels its log as fixture output. Current suite: 45 passing tests, including worker-log tampering rejection.

### Published schema validation

`schemas/contract.schema.json` and `schemas/report.schema.json` now document and validate the current operational format using Draft 2020-12. Runtime validation rejects unknown fields, missing fields, invalid types, and Boolean-as-integer confusion, with field-level errors. Cross-field and filesystem conditions remain in the runner. `requirements.txt` pins the already-installed jsonschema 4.26.0 dependency. Current suite: 42 passing tests. These schemas do not yet include every additional field proposed in the architecture specification.

### Runner-owned TDD checkpoints

Contracts now additionally require `testStrategy`, containing `mode` (`verification` or `tdd`), `testFiles`, `redCheckIndexes`, and `failureMarkers`. Verification mode requires empty arrays. TDD mode requires nonempty arrays and prewritten behavioral tests. The runner executes red checks before worker invocation, requires failure markers, rejects common import/syntax errors, records results and immutable test hashes, and requires the tests to remain unchanged. Normal independent verification supplies the green checkpoint. A regression test exercises red → worker → green. Current suite: 39 passing tests.

Previously generated contracts need the new explicit `testStrategy` field before a new dispatch. Historical accepted pilot artifacts remain unchanged.

### Required skill delivery

Contracts now require `requiredSkills`, an object mapping exact lowercase kebab-case IDs to project-relative instruction files. An empty object explicitly declares that no task-specific attachments are required. Missing or empty skill files block preflight. The runner hashes these files and revalidates them before review; the adapter attaches them through repeated `--file` arguments using the runner-provided environment list.

This implements explicit instruction delivery rather than native skill registration or proof of model compliance. The three additional tests cover missing files, changed instructions, and adapter attachments. Current suite: 37 passing tests. Live skill installation and a model-backed contracted coding run remain outstanding.

### Verification failure recovery

Timeouts during independent verification now persist `interrupted`; missing executables and other execution failures persist `changes_requested`. Records retain completed checks, the failing check index, and the error. Timeout classification uses a dedicated exception instead of matching message text. Two regression tests exercise these paths; the current suite has 34 passing tests.

### Structured report checkpoint

Reports now require `schemaVersion: 1`, task/attempt/contract identity, status, summary, `changedFiles`, `verification`, `blockers`, `changeRequests`, and `remainingConcerns`. The four list fields other than verification contain strings. Each verification entry has exactly `checkIndex` and `exitCode`.

The runner compares reported paths to measured changes. A review-ready report must cover all checks with zero exit codes and contain no blockers or change requests. Valid blocked reports retain the `blocked` lifecycle state. Independent reruns remain mandatory: worker check claims are not trusted as acceptance evidence. The complete design's evidence references and TDD checkpoints are still outstanding. Adapter prompts and worker fixtures use this expanded report format.

### OpenCode adapter checkpoint

`opencode_worker.py` can be selected as a contract's `workerCommand` using a Python executable, the adapter's absolute path, `--executable` with the native OpenCode executable, and `--contract` with the contract path. Optional flags are `--agent`, `--model`, and explicit `--auto`. It inherits runner identity/report environment variables and rejects execution without them.

The adapter attaches the contract using `--file`, requests JSON CLI transport, and asks the worker to create the separately validated report. It inherits stdout/stderr so the runner captures transport output. The adapter uses the preliminary report format; it does not implement the full approved report schema or guarantee that requested skills were loaded.

On 2026-10-25 a real CLI smoke request returned `WORKFLOW_TRANSPORT_OK` as a `text` event, preceded by `step_start`, with session ID `ses_e8fc971b3ffeZQnDWZ5YAsWU84`. The request instructed the worker not to use tools or edit files. This proves basic CLI/model transport, not contracted coding or gate enforcement.

The runner now records transport event counts, session IDs, malformed-line counts, and explicit error events in `transport.json`. Error events block review readiness even after a zero subprocess exit. CLI text remains distinct from the required report file. The current suite contains 28 passing tests.

### Kanban projection checkpoint

`kanban_projection.py` optionally publishes status snapshots as comments through the installed `hermes kanban --board ... comment` CLI. Enable it with `.workflow/kanban.json` containing `command` (executable argument array), `board` (explicit board slug), and `tickets` (workflow task ID to existing Hermes ticket ID mapping). Without this file it is disabled.

Successful identical snapshots are deduplicated. Failures are recorded as `pending` in `.workflow/kanban-sync.json` without changing canonical status. A process interruption between posting and receipt persistence can still duplicate a comment; the fingerprint makes duplicates identifiable. This is a comment projection, not column synchronization: ticket creation, claims, completion, and worker dispatch are intentionally not invoked. Real-board integration has not been exercised. The installed CLI help was inspected to confirm the command arguments.

The current suite contains 23 passing tests, including mocked projection success, failure, and deduplication checks.

- Replace the preliminary contract/report format with the complete approved v1 schemas, including skill resolution and full execution reports. Dependencies, criterion-level reviews, and a fixed retry limit are implemented in the preliminary format.
- Add a tracked-contract regression fixture. Preflight permits a metadata-only descendant of the pinned source baseline so a tracked contract need not contain its own commit hash.
- Complete approval/control revalidation during independent acceptance, directory-junction handling, ignored-runtime policy, and structured recovery.
- Implement crash-consistent lifecycle recovery, source patches, TDD checkpoints, and Kanban synchronization. Transition snapshots and independent-check evidence hashes are now implemented.
- Verify actual OpenCode JSON transport and task report behavior.
- Deploy reviewed skills and align live instructions only after backup and rollout checks.
- Run the approved pilot through its own requirements/design gates.

No live Hermes/OpenCode configuration has been modified by this checkpoint. The repository-level `docs/hermes-opencode-integration-spec.md` remains the target specification.
