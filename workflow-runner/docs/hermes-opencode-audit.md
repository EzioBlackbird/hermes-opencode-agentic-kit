# Hermes–OpenCode Local Integration Audit

Date: 2026-10-24
Scope: Read-only inspection of local installation, instructions, skill inventory, and delegation wrapper. No configuration changes or model-backed delegation runs were performed.

## Verified environment

- Hermes CLI: v0.22.5 (2026.9.24), local revision `bf0203a794a0`, Python 3.14.9.
- Hermes install: `~/AppData/Local/hermes/hermes-agent`.
- Current process `HERMES_HOME`: `~/AppData/Local/hermes`.
- OpenCode CLI: v2.1.4.
- `opencode run --help` confirms `--auto`, `--format json`, `--file`, `--session`, `--model`, and `--agent`.
- OpenCode global configuration: `~/.config/opencode/opencode.json`.
- Current workspace contains existing files and is not a Git repository; it was not repurposed as an implementation repository.

## Existing capabilities

Hermes already has local skills named `brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `verification-loop`, `requesting-code-review`, `receiving-code-review`, and `using-superpowers`. Presence does not establish runtime invocation or upstream version parity.

Its active-home `SOUL.md` already describes design approval, planning, TDD, Kanban, delegation to OpenCode, and independent verification of worker claims.

OpenCode has six global engineering skills and thirteen shared design/output skills in the two configured skill directories. These inspected directories do not contain the Hermes Superpowers process skills or a dedicated task-contract/reporting skill.

The delegation skill is located at `skills/autonomous-ai-agents/opencode/SKILL.md` under Hermes home. The existing wrapper is `~/Jarvis/opencode_delegate.sh`.

## Findings

1. **Instruction conflicts:** `SOUL.md` requires design approval but also directs the agent to decide assumptions rather than ask (line 143). Product decisions and implementation discretion need explicit boundaries.
2. **Routing drift:** `SOUL.md` recommends direct DeepSeek for implementation, while inspected OpenCode build/general configuration selects a local-router Gemini model. The actual route for a future run remains untested.
3. **CLI documentation drift:** The Hermes delegation skill advertises `--attach`; the installed `opencode run --help` instead exposes `--server`. Its preferred wrapper guidance also differs from the direct CLI example in `SOUL.md`.
4. **No gate validation in the inspected wrapper:** It checks executable/work-directory presence and forwards a prompt with `--auto`. It does not validate approval versions, task contracts, allowed changes, or acceptance evidence.
5. **Multiple tracking conventions:** `verification-loop` uses Markdown tickets; `SOUL.md` requires Kanban; planning uses `docs/superpowers/plans`. These need a canonical task identity and authority model to prevent divergent status.
6. **Plugin scope:** The inspected `fullstack-guardian/index.mjs` defines audit/schema-validation prompt commands. Its source does not implement approval or task-scope enforcement. Runtime plugin activation was not tested.
7. **Home-path ambiguity:** A separate `~/.hermes` directory exists. The inspected process sets Hermes home to the AppData location; all-client consistency has not been established.

## Recommended minimum design for approval

- Reuse the existing Hermes methodology skills after resolving conflicting instructions.
- Add narrowly scoped OpenCode skills for contract execution and structured evidence handoff; adapt relevant testing/debugging methodology rather than copying every orchestration rule.
- Define a versioned task contract and execution report with task ID, attempt ID, revision identity, acceptance criteria, allowed paths, verification commands, and evidence locations.
- Keep task definitions, approvals, and evidence in project artifacts. Treat Kanban as a synchronized view, with one documented authority for status transitions.
- Have OpenCode return `ready_for_review`, `blocked`, or `failed`; only the orchestrator may accept a task after verification.
- Add a delegation validator that checks contract completeness and approval validity before invocation, then checks report completeness and changed-file scope afterwards. Post-run scope detection is not prevention; strict prevention requires a separate execution-boundary design.
- Pilot serial execution on one isolated end-to-end feature before parallelism.

## Remaining verification

- Inspect Hermes effective terminal backend and all relevant profile overrides using secret-safe extraction.
- Confirm runtime skill resolution, wrapper executable availability, and actual delegation behavior.
- Validate machine-readable CLI event behavior; JSON output is not automatically a task-result schema.
- Exercise missing approval, out-of-scope change, failing verification, interrupted execution, and successful acceptance.
- Review and approve the minimum design before changing live instructions or installing integration components.

## Documentation consulted

- https://opencode.ai/v2/docs/skills
- https://opencode.ai/v2/docs/cli
- Installed CLI help and local source files take precedence for claims about the inspected installation.
