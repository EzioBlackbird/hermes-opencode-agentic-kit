"""Prepare or run an isolated real-OpenCode runner integration pilot."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

import workflow as w


def prepare(root: Path, executable: Path) -> None:
    if root.exists():
        raise w.GateError("Pilot directory already exists; refusing to overwrite")
    root.mkdir(parents=True)

    def git(*args: str) -> str:
        return w.git(root, *args)

    git("init")
    git("config", "user.name", "Workflow Pilot")
    git("config", "user.email", "workflow-pilot@example.invalid")
    (root / ".gitignore").write_text(
        "artifacts/\n.workflow/state.json\n.workflow/runner.lock\n.workflow/events/\n__pycache__/\n",
        encoding="utf-8",
    )
    (root / "docs").mkdir()
    (root / "docs/requirements.md").write_text(
        "# Runner integration fixture\nImplement sum_even(values) in calculator.py. "
        "Return the sum of even integers, including negative values. Empty input returns zero. "
        "This is an integration fixture for the approved workflow implementation, not a product pilot.\n",
        encoding="utf-8",
    )
    (root / "docs/design.md").write_text(
        "# Design\nUse Python standard library only. Implement one pure function. "
        "Do not change the verifier or workflow artifacts. Read required skill attachments as instructions.\n",
        encoding="utf-8",
    )
    (root / "check.py").write_text(
        "from calculator import sum_even\n"
        "assert sum_even([]) == 0\nassert sum_even([1, 2, 3, 4]) == 6\n"
        "assert sum_even([-4, -3, 0, 6]) == 2\nprint('PILOT_CHECKS_OK')\n",
        encoding="utf-8",
    )
    for gate, document in [
        ("requirements", "docs/requirements.md"),
        ("design", "docs/design.md"),
    ]:
        w.save(
            root / f".workflow/{gate}.json",
            {
                "gate": gate,
                "decision": "approved",
                "evidence": "User approved integration implementation and requested continuation to completion; this bounded fixture tests that integration only.",
                "documentHashes": {document: w.digest(root / document)},
            },
        )
    skills = {}
    for identifier in ("task-contract-execution", "structured-handoff"):
        relative = f".opencode/skills/{identifier}/SKILL.md"
        destination = root / relative
        destination.parent.mkdir(parents=True)
        shutil.copyfile(
            Path(__file__).parent / "skills" / identifier / "SKILL.md", destination
        )
        skills[identifier] = relative
    git("add", ".")
    git("commit", "-m", "test: establish runner integration fixture")
    task = {
        "schemaVersion": 1,
        "projectId": "runner-integration-pilot",
        "title": "Implement even integer sum",
        "objective": "Implement and verify sum_even using the approved fixture",
        "contextFiles": ["docs/requirements.md", "docs/design.md"],
        "nonGoals": ["No external dependencies or verifier changes"],
        "taskId": "T001",
        "baseRevision": git("rev-parse", "HEAD"),
        "approvalFiles": [".workflow/requirements.json", ".workflow/design.json"],
        "allowedPaths": ["calculator.py"],
        "verification": [[sys.executable, "-B", "check.py"]],
        "workerCommand": [
            sys.executable,
            str(Path(__file__).with_name("opencode_worker.py").resolve()),
            "--executable",
            str(executable),
            "--contract",
            "tasks/T001.json",
            "--auto",
        ],
        "timeoutSeconds": 240,
        "dependsOn": [],
        "requiredSkills": skills,
        "testStrategy": {
            "mode": "verification",
            "testFiles": [],
            "redCheckIndexes": [],
            "failureMarkers": [],
        },
        "acceptanceCriteria": [
            {
                "id": "AC1",
                "description": "Even integer sums match all fixed acceptance cases",
                "checkIndexes": [0],
            }
        ],
    }
    w.save(root / "tasks/T001.json", task)
    git("add", ".")
    git("commit", "-m", "test: bind pilot task contract")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument(
        "--executable",
        type=Path,
        default=Path(os.environ.get("APPDATA", ""))
        / "npm/node_modules/@opencode/cli/bin/opencode.exe",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == "prepare":
        prepare(root, args.executable)
        print(f"Prepared {root}")
        return 0
    state = w.dispatch(root, "tasks/T001.json")
    print(state["status"], state.get("error", ""))
    if state["status"] != "ready_for_review":
        return 1
    state = w.verify(root)
    print(state["status"], state.get("error", ""))
    return 0 if state["status"] == "verified" else 1


if __name__ == "__main__":
    sys.exit(main())
