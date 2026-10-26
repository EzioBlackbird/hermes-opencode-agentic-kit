# Hermes + OpenCode Agentic Engineering Kit

One-command Turnkey Integration uniting **Gated Project Orchestration**, **REA (Reverse Engineer Anything)**, and **CLI-Anything / CLI-Hub** for autonomous AI software engineering on Windows 11.

---

## Architecture Overview

```text
[1. Concept / Product Intake]
       │
       ▼
[2. Gate 1: Requirements Approval] (SHA-256 bound JSON)
       │
       ▼
[3. Proactive Reference Scouting & REA Discovery]
       ├─ Web / Electron / JS Bundles (Built-in static & browser analyzer)
       ├─ Android APKs (JADX 0.7.1 + Apktool 3.0.3)
       ├─ Native PE / ELF / C / Rust Binaries (Ghidra 12.1.4 Headless)
       └─ CLI-Hub Marketplace Inspection (103+ Agent-Native CLIs)
       │  (All raw evidence isolated in artifacts/discovery/<target>/)
       ▼
[4. Gate 2: Clean-Room Design Approval] (SHA-256 bound JSON)
       │
       ▼
[5. Bounded Task Contract (tasks/T00X.json)]
       │
       ▼
[6. Gated OpenCode Workflow Runner]
       ├─ preflight -> dispatch -> verify -> review -> accept
       └─ 7-Phase CLI-Anything Harness Generator (HARNESS.md + TEST.md + SKILL.md)
```

---

## What's Included in This Repository

- **`workflow-runner/`**: Complete Gated Project Orchestration engine (`workflow.py`, `opencode_worker.py`, `install_project.py`, `kanban_projection.py`, `tdd.py`, Draft 2020-12 JSON schemas, and **48 unit/integration tests**).
- **`skills/`**:
  - `gated-project-orchestration`: Enforces 1-question-per-turn intake, Proactive REA Reference Scouting, SHA-256 approval gates, clean-room engineering, and runner verification.
  - `reverse-engineer-anything`: Official REA v49 skill + reference guides.
  - `cli-hub-meta-skill`: Autonomous discovery and installation of 103+ agent-native CLIs.
- **`opencode/commands/`**: 5 slash commands (`/cli-anything`, `/cli-anything-refine`, `/cli-anything-test`, `/cli-anything-validate`, `/cli-anything-list`) hardened with Gated Project Boundaries.
- **`cli-anything-plugin/`**: Complete 7-phase `HARNESS.md` specification, `repl_skin.py`, `guides/`, `scripts/`, and `templates/`.
- **`bootstrap.py`**: Cross-machine automated installer and verifier.

---

## Quick Start (One-Command Setup)

### Prerequisites
- Windows 10/11 x64
- Python 3.10+ (`python` on PATH)
- Node.js 22.23.4+ & npm
- Git

### 1. Clone & Run Bootstrapper

```powershell
git clone https://github.com/EzioBlackbird/hermes-opencode-agentic-kit.git
cd hermes-opencode-agentic-kit

# Full Installation (includes OpenJDK 21, Ghidra 12.1.4, JADX 0.7.1, Apktool 3.0.3)
python bootstrap.py --mode full

# Or Lite Installation (Static JS/Web/Electron/SQLite REA + CLI-Anything + Gated Runner)
python bootstrap.py --mode lite
```

### 2. What `bootstrap.py` Does Automatically
1. Installs Python packages (`jsonschema`, `cli-anything-hub`, `click`, `prompt-toolkit`, `pytest`).
2. Installs the Gated Workflow Runner to `~/Jarvis/hermes-opencode-workflow`.
3. Installs `cli-anything-plugin` and configures the 5 `/cli-anything*` slash commands in `~/.config/opencode/commands/` with dynamically resolved user paths.
4. Installs `gated-project-orchestration`, `cli-hub-meta-skill`, and `reverse-engineer-anything` into Hermes and OpenCode skill directories.
5. Installs a durable `rea-agents@6.8.0` runtime (avoiding ephemeral `npx` cache corruption) and downloads/verifies **OpenJDK 21, Ghidra 12.1.4, JADX 0.7.1, and Apktool 3.0.3** (in `--mode full`).
6. Registers the `rea` MCP server in both OpenCode (`opencode.json`) and Hermes (`config.yaml`) while preserving all existing user settings and API keys.
7. Runs all **48 runner regression tests** and `rea doctor` to prove readiness.
# Update safety and recovery boundaries

The installer overlays packaged files without deleting unrelated destination files.
Before replacing a differing file it saves a sibling backup named
`<filename>.agentic-kit-backup-<UTC timestamp>`. Existing legacy `command/`
directories are preserved; inspect duplicate commands manually. Obsolete files
are not automatically removed. Backups of client configuration may contain secrets:
keep them private and never commit or upload them.

Hermes routing is maintained inside `agentic-kit:routing` markers. Existing legacy
routing sections are migrated, missing `SOUL.md` files are created, and instructions
outside the managed section are preserved. Ambiguous markers stop the update.
Restart/reload Hermes before testing updated routing in a new session.

Workers must produce their own reports. Never synthesize reports or manually edit
canonical runner state to turn a failed attempt into success. Use `recover` only
for supported terminal states and `reconcile-report` only for the exact supported
file-list mismatch. An abandoned `running` attempt remains a blocker until a
validated recovery path exists; do not manually promote it.

Offline regression checks: `python -m unittest test_bootstrap -v`, followed by
`python -m unittest discover -v` from `workflow-runner/`. These do not prove live
Hermes routing, fresh-machine installation, provider execution, or enforcement
against tools invoked outside the runner. Routing remains instruction-based.
