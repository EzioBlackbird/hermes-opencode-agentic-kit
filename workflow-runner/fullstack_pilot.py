"""Prepare the approved full-stack pilot for real contracted execution."""

from pathlib import Path
import argparse
import os
import shutil
import sys

import workflow as w
from install_project import install


def prepare(root: Path) -> None:
    if root.exists():
        raise ValueError("Refusing to overwrite an existing pilot")
    root.mkdir(parents=True)
    runner = Path(__file__).resolve().parent
    w.git(root, "init")
    w.git(root, "config", "user.name", "Workflow Pilot")
    w.git(root, "config", "user.email", "workflow-pilot@example.invalid")
    (root / "docs").mkdir()
    for name in ("requirements", "design"):
        target = root / "docs" / f"{name}.md"
        shutil.copyfile(runner.parent / "docs" / f"fullstack-pilot-{name}.md", target)
        w.save(
            root / f".workflow/{name}.json",
            {
                "gate": name,
                "decision": "approved",
                "evidence": "User replied 'Lanjut' immediately after explicit request to approve both full-stack pilot requirements and Python-SQLite-JavaScript design.",
                "documentHashes": {f"docs/{name}.md": w.digest(target)},
            },
        )
    install(root)
    (root / ".gitignore").write_text(
        "artifacts/\n.workflow/state.json\n.workflow/runner.lock\n.workflow/events/\n__pycache__/\n*.db\n.ruff_cache/\n",
        encoding="utf-8",
    )
    w.git(root, "add", ".")
    w.git(root, "commit", "-m", "docs: record approved full-stack pilot")
    task = {
        "schemaVersion": 1,
        "projectId": "fullstack-pilot",
        "taskId": "T001",
        "title": "Implement approved local task-list vertical slice",
        "objective": "Implement all behavior in docs/requirements.md and docs/design.md. Provide app.py, static/index.html, static/app.js, static/style.css, test_app.py, README.md, and .env.example. Tests must start the server on a free port with a temporary database and verify validation, real HTTP create/list, inert title persistence, and persistence across restart. Bind only localhost. Do not claim browser checks have run unless actually performed.",
        "contextFiles": ["docs/requirements.md", "docs/design.md"],
        "nonGoals": [
            "Authentication",
            "Deployment",
            "External packages",
            "Changing approved docs",
        ],
        "baseRevision": w.git(root, "rev-parse", "HEAD"),
        "approvalFiles": [".workflow/requirements.json", ".workflow/design.json"],
        "allowedPaths": [
            "app.py",
            "static/",
            "test_app.py",
            "README.md",
            ".env.example",
            ".ruff_cache/",
        ],
        "verification": [[sys.executable, "-B", "-m", "unittest", "-v", "test_app"]],
        "workerCommand": [
            sys.executable,
            str(runner / "opencode_worker.py"),
            "--executable",
            str(
                Path(os.environ["APPDATA"])
                / "npm/node_modules/@opencode/cli/bin/opencode.exe"
            ),
            "--contract",
            "tasks/T001.json",
            "--auto",
        ],
        "timeoutSeconds": 900,
        "dependsOn": [],
        "requiredSkills": {
            name: f".opencode/skills/{name}/SKILL.md"
            for name in ("task-contract-execution", "structured-handoff")
        },
        "testStrategy": {
            "mode": "verification",
            "testFiles": [],
            "redCheckIndexes": [],
            "failureMarkers": [],
        },
        "acceptanceCriteria": [
            {
                "id": "API",
                "description": "Real API validation and SQLite restart persistence pass; final product acceptance additionally requires separate browser review",
                "checkIndexes": [0],
            }
        ],
    }
    w.save(root / "tasks/T001.json", task)
    w.git(root, "add", ".")
    w.git(root, "commit", "-m", "feat: define bounded implementation contract")
    w.preflight(root, "tasks/T001.json")
    print(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    prepare(parser.parse_args().root.resolve())
