"""OpenCode subprocess adapter for a runner-assigned contract and report path."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def build_command(
    executable: str,
    contract: Path,
    agent: str,
    model: str | None,
    auto: bool,
    environment: dict[str, str],
) -> list[str]:
    keys = (
        "WORKFLOW_REPORT",
        "WORKFLOW_TASK_ID",
        "WORKFLOW_ATTEMPT_ID",
        "WORKFLOW_CONTRACT_HASH",
    )
    if any(not environment.get(key) for key in keys):
        raise ValueError("Adapter must be invoked by the workflow runner")
    if not contract.is_file():
        raise ValueError("Contract file does not exist")
    report = {
        "taskId": environment["WORKFLOW_TASK_ID"],
        "attemptId": environment["WORKFLOW_ATTEMPT_ID"],
        "contractHash": environment["WORKFLOW_CONTRACT_HASH"],
        "status": "ready_for_review",
        "summary": "Describe actual implementation and checks",
        "schemaVersion": 1,
        "changedFiles": [],
        "verification": [],
        "blockers": [],
        "changeRequests": [],
        "remainingConcerns": [],
    }
    prompt = (
        "Execute the attached approved task contract. Read its referenced approval documents. "
        "Only change allowedPaths and the assigned report file. Do not alter contracts, approvals, "
        "workflow state, or acceptance criteria. Run all verification commands. "
        "Load task-contract-execution and structured-handoff if available; report unavailable skills. "
        "If blocked, do not expand scope: set report status to blocked and explain why in summary. "
        "On a check failure set status to failed. Never claim final acceptance. "
        f"Write the report as UTF-8 JSON to {environment['WORKFLOW_REPORT']}. "
        "Use exactly these keys and preserve identity values: "
        + json.dumps(report)
        + ". "
        "Replace summary with real results. List all actually changed paths in changedFiles. "
        "For each verification command include checkIndex (zero-based), exitCode, and evidencePaths. "
        "Save actual check output in .log files beside the report and put their project-relative paths in evidencePaths. "
        "List blockers, change requests, and remaining concerns as strings. "
        "CLI text is not a substitute for the report file."
    )
    argv = [
        executable,
        "run",
        "--standalone",
        "--format",
        "json",
        "--agent",
        agent,
        "--file",
        str(contract.resolve()),
    ]
    skill_files = json.loads(environment.get("WORKFLOW_SKILL_FILES", "[]"))
    if not isinstance(skill_files, list) or not all(
        isinstance(name, str) for name in skill_files
    ):
        raise ValueError("Invalid runner skill attachment list")
    for name in skill_files:
        path = Path(name)
        if not path.is_file():
            raise ValueError(f"Required skill attachment missing: {name}")
        argv.extend(["--file", str(path.resolve())])
    if model:
        argv.extend(["--model", model])
    if auto:
        argv.append("--auto")
    argv.append(prompt)
    return argv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--executable", required=True, help="Native OpenCode executable path"
    )
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--agent", default="build")
    parser.add_argument("--model")
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()
    try:
        run_env = dict(os.environ)
        if os.name == "nt" and run_env.get("PWD", "").startswith("/"):
            del run_env["PWD"]
        argv = build_command(
            args.executable,
            args.contract,
            args.agent,
            args.model,
            args.auto,
            run_env,
        )
        ret = subprocess.run(argv, env=run_env, check=False).returncode
        if ret == 0:
            return 0

        # Resilient multi-tier fallback sequence if community model fails
        fallback_agents = {
            "build": ["build-fallback", "build-safe"],
            "plan": ["plan-fallback", "plan-safe"],
            "explore": ["explore-fallback", "explore-safe"],
            "general": ["general-fallback", "general-safe"],
            "summary": ["summary-fallback", "summary-safe"],
        }
        fallbacks = fallback_agents.get(args.agent, [])
        if not args.model and fallbacks:
            for fb_agent in fallbacks:
                print(
                    f"Primary agent '{args.agent}' failed (exit code {ret}). "
                    f"Retrying with fallback agent '{fb_agent}'...",
                    file=sys.stderr,
                )
                fb_argv = build_command(
                    args.executable,
                    args.contract,
                    fb_agent,
                    None,
                    args.auto,
                    run_env,
                )
                ret = subprocess.run(fb_argv, env=run_env, check=False).returncode
                if ret == 0:
                    print(
                        f"Fallback agent '{fb_agent}' succeeded.",
                        file=sys.stderr,
                    )
                    return 0
        return ret
    except (OSError, ValueError) as exc:
        print(f"OpenCode adapter failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
