"""Local gated execution with immutable input binding and independent checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
from contextlib import contextmanager
from typing import Iterator

from kanban_projection import synchronize
from transport import inspect_transport
from tdd import validate_strategy, red_checkpoint, test_hashes
from schema_validation import validate_document


class GateError(ValueError):
    """A required workflow condition is not satisfied."""


class ExecutionInterrupted(GateError):
    """Execution timed out and requires workspace inspection."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GateError(f"Expected object: {path}")
    return value


def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def resolve(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or ":" in name or "\\" in name:
        raise GateError(f"Invalid relative path: {name!r}")
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or name.startswith("./"):
        raise GateError(f"Path escapes project: {name}")
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()):
        raise GateError(f"Path escapes project: {name}")
    return result


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True
    )
    if result.returncode:
        raise GateError(result.stderr.strip())
    return result.stdout.strip()


def manifest(root: Path) -> dict[str, str]:
    result = {}
    for directory, folders, files in os.walk(root):
        relative = Path(directory).relative_to(root)
        for name in folders:
            path = Path(directory) / name
            if path.is_symlink() or (
                hasattr(path, "is_junction") and path.is_junction()
            ):
                raise GateError(f"Directory links are not supported: {path}")
        folders[:] = [
            name
            for name in folders
            if not (
                (relative == Path(".") and name in {".git", "artifacts", ".workflow"})
                or name in {".gradle", "build", "__pycache__", ".pytest_cache", ".ruff_cache"}
            )
        ]
        for name in files:
            path = Path(directory) / name
            key = path.relative_to(root).as_posix()
            resolve(root, key)
            result[key] = digest(path)
    return result


def path_matches_scope(path: str, scope: str) -> bool:
    if scope.endswith("/**"):
        prefix = scope[:-3]
        return path == prefix or path.startswith(prefix + "/")
    if scope.endswith("/"):
        return path.startswith(scope)
    return path == scope


@contextmanager
def lock(root: Path) -> Iterator[None]:
    path = root / ".workflow/runner.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise GateError(
            "Project locked; inspect active process before recovery"
        ) from exc
    try:
        os.write(descriptor, str(os.getpid()).encode())
        os.close(descriptor)
        yield
    finally:
        path.unlink()


def exact(value: dict, fields: set[str], label: str) -> None:
    if set(value) != fields:
        raise GateError(f"{label}: expected fields {sorted(fields)}")


def validate_report(report: dict, state: dict, task: dict, changed: list[str]) -> None:
    validate_document("report", report)
    exact(
        report,
        {
            "schemaVersion",
            "taskId",
            "attemptId",
            "contractHash",
            "status",
            "summary",
            "changedFiles",
            "verification",
            "blockers",
            "changeRequests",
            "remainingConcerns",
        },
        "report",
    )
    if type(report["schemaVersion"]) is not int or report["schemaVersion"] != 1:
        raise GateError("Unsupported report schema")
    for key in ("taskId", "attemptId", "contractHash"):
        if report[key] != state[key]:
            raise GateError(f"Report identity mismatch: {key}")
    if report["status"] not in {"ready_for_review", "blocked", "failed"}:
        raise GateError("Invalid report status")
    if not isinstance(report["summary"], str) or not report["summary"].strip():
        raise GateError("Report summary is required")
    for key in ("changedFiles", "blockers", "changeRequests", "remainingConcerns"):
        if not isinstance(report[key], list) or not all(
            isinstance(item, str) and item.strip() for item in report[key]
        ):
            raise GateError(f"Report {key} must be a list of nonempty strings")
    if sorted(report["changedFiles"]) != sorted(changed):
        raise GateError("Reported files do not match measured changes")
    if report["status"] == "blocked" and not report["blockers"]:
        raise GateError("Blocked report requires a blocker")
    checks = report["verification"]
    if not isinstance(checks, list):
        raise GateError("Report verification must be a list")
    seen = set()
    for check in checks:
        if not isinstance(check, dict):
            raise GateError("Report check must be an object")
        exact(check, {"checkIndex", "exitCode", "evidencePaths"}, "report check")
        index = check["checkIndex"]
        if (
            type(index) is not int
            or not 0 <= index < len(task["verification"])
            or index in seen
        ):
            raise GateError("Invalid or duplicate report check index")
        if type(check["exitCode"]) is not int:
            raise GateError("Report exit code must be an integer")
        seen.add(index)
    if report["status"] == "ready_for_review":
        if (
            report["blockers"]
            or report["changeRequests"]
            or seen != set(range(len(task["verification"])))
        ):
            raise GateError(
                "Review-ready report has unresolved items or missing checks"
            )
        if any(check["exitCode"] != 0 for check in checks):
            raise GateError("Review-ready report contains failed checks")


def validate_criteria(task: dict) -> None:
    criteria = task["acceptanceCriteria"]
    if not isinstance(criteria, list) or not criteria:
        raise GateError("Acceptance criteria must be a nonempty list")
    identifiers = set()
    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise GateError("Each criterion must be an object")
        exact(criterion, {"id", "description", "checkIndexes"}, "criterion")
        identifier = criterion["id"]
        if (
            not isinstance(identifier, str)
            or not identifier.strip()
            or identifier in identifiers
        ):
            raise GateError("Criterion IDs must be unique nonempty strings")
        identifiers.add(identifier)
        if (
            not isinstance(criterion["description"], str)
            or not criterion["description"].strip()
        ):
            raise GateError("Criterion description is required")
        indexes = criterion["checkIndexes"]
        if (
            not isinstance(indexes, list)
            or not indexes
            or any(
                type(index) is not int or not 0 <= index < len(task["verification"])
                for index in indexes
            )
        ):
            raise GateError(
                "Each criterion must reference existing verification checks"
            )


def validate_skills(root: Path, task: dict) -> dict[str, str]:
    skills = task["requiredSkills"]
    if not isinstance(skills, dict):
        raise GateError(
            "requiredSkills must map exact skill IDs to project-relative files"
        )
    hashes = {}
    for identifier, name in skills.items():
        if (
            not isinstance(identifier, str)
            or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier) is None
        ):
            raise GateError("Invalid required skill ID")
        path = resolve(root, name)
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            raise GateError(f"Required skill unavailable: {identifier}")
        hashes[name] = digest(path)
    return hashes


def validate_dependencies(
    root: Path, task: dict, ancestors: frozenset[str] = frozenset()
) -> None:
    if task["taskId"] in ancestors:
        raise GateError(f"Dependency cycle detected: {task['taskId']}")
    ancestors = ancestors | {task["taskId"]}
    dependencies = task["dependsOn"]
    if not isinstance(dependencies, list) or any(
        not isinstance(item, str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}", item) is None
        for item in dependencies
    ):
        raise GateError("Dependencies must be valid task IDs")
    if len(set(dependencies)) != len(dependencies) or task["taskId"] in dependencies:
        raise GateError("Duplicate or self-referencing dependency")
    for identifier in dependencies:
        path = root / ".workflow/accepted" / f"{identifier}.json"
        if not path.exists():
            raise GateError(f"Dependency not accepted: {identifier}")
        accepted = load(path)
        if accepted.get("status") != "accepted" or accepted.get("taskId") != identifier:
            raise GateError(f"Invalid dependency acceptance: {identifier}")
        contract_path = resolve(root, accepted["contractPath"])
        if digest(contract_path) != accepted["contractHash"]:
            raise GateError(f"Dependency contract changed: {identifier}")
        dependency = load(contract_path)
        if dependency.get("projectId") != task["projectId"]:
            raise GateError(f"Dependency belongs to another project: {identifier}")
        if dependency["taskId"] != identifier:
            raise GateError(f"Dependency contract identity mismatch: {identifier}")
        if validate_approvals(root, dependency) != accepted["approvalHashes"]:
            raise GateError(f"Dependency approvals changed: {identifier}")
        revalidate_acceptance_evidence(root, accepted)
        validate_dependencies(root, dependency, ancestors)


def revalidate_acceptance_evidence(root: Path, state: dict) -> None:
    for check in state["checks"]:
        if check["exitCode"] != 0:
            raise GateError("Verification did not pass")
        for path, expected in check["evidenceHashes"].items():
            if digest(resolve(root, path)) != expected:
                raise GateError(f"Verification evidence changed: {path}")


def validate_approvals(root: Path, task: dict) -> dict[str, str]:
    gates = set()
    hashes = {}
    for name in task["approvalFiles"]:
        path = resolve(root, name)
        approval = load(path)
        exact(approval, {"gate", "decision", "evidence", "documentHashes"}, "approval")
        if (
            approval["decision"] != "approved"
            or not isinstance(approval["evidence"], str)
            or not approval["evidence"].strip()
        ):
            raise GateError("Approval requires explicit user evidence")
        if (
            not isinstance(approval["documentHashes"], dict)
            or not approval["documentHashes"]
        ):
            raise GateError("Approval must bind documents")
        for document, expected in approval["documentHashes"].items():
            if digest(resolve(root, document)) != expected:
                raise GateError(f"Stale approval: {document}")
        if approval["gate"] in gates:
            raise GateError("Duplicate approval gate")
        gates.add(approval["gate"])
        hashes[name] = digest(path)
    if gates != {"requirements", "design"}:
        raise GateError("Both requirements and design approval are required")
    return hashes


def persist(root: Path, state: dict, action: str) -> None:
    event = {"action": action, "timestampNs": time.time_ns(), "state": state}
    save(root / ".workflow/state.json", state)
    save(root / ".workflow/events" / f"{event['timestampNs']}.json", event)
    try:
        synchronize(root, state)
    except OSError as exc:
        print(f"Kanban projection unavailable: {exc}", file=sys.stderr)


def revalidate(root: Path, state: dict) -> dict:
    for name, expected in state.get("workerEvidenceHashes", {}).items():
        if digest(resolve(root, name)) != expected:
            raise GateError(f"Worker evidence changed: {name}")
    contract = resolve(root, state["contractPath"])
    if digest(contract) != state["contractHash"]:
        raise GateError("Contract changed")
    task = load(contract)
    if {name: digest(resolve(root, name)) for name in task["contextFiles"]} != state[
        "contextHashes"
    ]:
        raise GateError("Task context changed since dispatch")
    if validate_skills(root, task) != state["skillHashes"]:
        raise GateError("Required skill instructions changed since dispatch")
    if validate_approvals(root, task) != state["approvalHashes"]:
        raise GateError("Approval records changed since dispatch")
    if manifest(root) != state["after"]:
        raise GateError("Source changed since worker review")
    return task


def preflight(root: Path, task_path: str) -> dict:
    task = load(resolve(root, task_path))
    try:
        validate_document("contract", task)
    except ValueError as exc:
        raise GateError(str(exc)) from exc
    exact(
        task,
        {
            "schemaVersion",
            "taskId",
            "baseRevision",
            "approvalFiles",
            "allowedPaths",
            "verification",
            "workerCommand",
            "timeoutSeconds",
            "acceptanceCriteria",
            "dependsOn",
            "requiredSkills",
            "testStrategy",
            "projectId",
            "title",
            "objective",
            "contextFiles",
            "nonGoals",
        },
        "contract",
    )
    if (
        task["schemaVersion"] != 1
        or not isinstance(task["taskId"], str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}", task["taskId"]) is None
    ):
        raise GateError("Unsupported schema or task ID")
    head = git(root, "rev-parse", "HEAD")
    if head != task["baseRevision"]:
        # A tracked contract cannot contain its own commit hash. Permit only a
        # metadata-only descendant of the pinned source revision.
        git(root, "merge-base", "--is-ancestor", task["baseRevision"], head)
        changed = git(
            root, "diff", "--name-only", task["baseRevision"], head
        ).splitlines()
        if any(
            not name.startswith(("tasks/", ".workflow/", "docs/")) for name in changed
        ):
            raise GateError("Baseline revision mismatch: source changed")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise GateError("Commit the project baseline before dispatch")
    validate_approvals(root, task)
    for name in task["contextFiles"]:
        if not resolve(root, name).is_file():
            raise GateError(f"Context file missing: {name}")
    validate_criteria(task)
    validate_strategy(task)
    test_hashes(root, task, resolve)
    validate_skills(root, task)
    validate_dependencies(root, task)
    if not task["allowedPaths"] or not task["verification"]:
        raise GateError("Scope and verification cannot be empty")
    for name in task["allowedPaths"]:
        resolve(root, name)
        if name in {".", "./"} or name.split("/")[0].casefold() in {
            ".git",
            ".workflow",
            "tasks",
            "artifacts",
            "docs",
        }:
            raise GateError("Worker scope cannot include control documents")
    for command in [task["workerCommand"], *task["verification"]]:
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(x, str) and x for x in command)
        ):
            raise GateError("Commands must be nonempty string argument arrays")
    if (
        not isinstance(task["timeoutSeconds"], int)
        or not 1 <= task["timeoutSeconds"] <= 3600
    ):
        raise GateError("Timeout must be between 1 and 3600 seconds")
    return task


def command(
    argv: list[str], root: Path, output: Path, timeout: int, env: dict | None = None
) -> int:
    with (
        output.with_suffix(".stdout.log").open("wb") as stdout,
        output.with_suffix(".stderr.log").open("wb") as stderr,
    ):
        process = subprocess.Popen(
            argv, cwd=root, stdout=stdout, stderr=stderr, env=env
        )
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True,
                )
            else:
                process.kill()
            process.wait()
            raise ExecutionInterrupted(
                "Execution interrupted by timeout; inspect partial work"
            )


def dispatch(root: Path, task_path: str) -> dict:
    with lock(root):
        task = preflight(root, task_path)
        state_path = root / ".workflow/state.json"
        previous = load(state_path) if state_path.exists() else {}
        if previous and previous.get("status") not in {"ready", "accepted"}:
            raise GateError("Resolve the previous attempt before dispatch")
        prior_attempts = (
            previous.get("attemptCount", 0)
            if previous.get("taskId") == task["taskId"]
            else 0
        )
        if prior_attempts >= 3:
            raise GateError(
                "Attempt limit reached; review the task before further execution"
            )
        attempt = str(time.time_ns())
        folder = root / "artifacts" / task["taskId"] / attempt
        folder.mkdir(parents=True)
        before = manifest(root)
        state = {
            "taskId": task["taskId"],
            "projectId": task["projectId"],
            "contextHashes": {
                name: digest(resolve(root, name)) for name in task["contextFiles"]
            },
            "attemptId": attempt,
            "status": "running",
            "contractPath": task_path,
            "contractHash": digest(resolve(root, task_path)),
            "folder": folder.relative_to(root).as_posix(),
            "before": before,
            "approvalHashes": validate_approvals(root, task),
            "attemptCount": prior_attempts + 1,
            "skillHashes": validate_skills(root, task),
        }
        persist(root, state, "dispatch")
        controls = {
            p.as_posix(): digest(p) for p in (root / ".workflow").rglob("*.json")
        }
        environment = dict(
            os.environ,
            WORKFLOW_REPORT=str(folder / "report.json"),
            WORKFLOW_TASK_ID=task["taskId"],
            WORKFLOW_ATTEMPT_ID=attempt,
            WORKFLOW_CONTRACT_HASH=state["contractHash"],
            WORKFLOW_SKILL_FILES=json.dumps(
                [str(resolve(root, name)) for name in state["skillHashes"]]
            ),
        )
        if os.name == "nt" and environment.get("PWD", "").startswith("/"):
            del environment["PWD"]
        save(
            folder / "invocation.json",
            {"command": task["workerCommand"], "contractHash": state["contractHash"]},
        )
        try:
            if task["testStrategy"]["mode"] == "tdd":
                state["redCheckpoint"] = red_checkpoint(
                    root, folder, task, command, resolve
                )
                save(folder / "red-checkpoint.json", state["redCheckpoint"])
                if manifest(root) != before:
                    raise GateError("Red checkpoint modified the source baseline")
            code = command(
                task["workerCommand"],
                root,
                folder / "worker",
                task["timeoutSeconds"],
                environment,
            )
            if code:
                raise GateError(f"Worker exited with {code}")
            transport = inspect_transport(folder / "worker.stdout.log")
            save(folder / "transport.json", transport)
            state["transport"] = transport
            if transport["errors"]:
                raise GateError("Worker transport emitted an error event")
            report = load(folder / "report.json")
            if any(
                not Path(p).exists() or digest(Path(p)) != h
                for p, h in controls.items()
            ):
                raise GateError("Worker changed workflow control state")
            after = manifest(root)
            if (
                "redCheckpoint" in state
                and test_hashes(root, task, resolve)
                != state["redCheckpoint"]["testHashes"]
            ):
                raise GateError("Worker modified immutable TDD tests")
            changed = [
                p for p in before.keys() | after.keys() if before.get(p) != after.get(p)
            ]
            for path in changed:
                if not any(
                    path_matches_scope(path, scope)
                    for scope in task["allowedPaths"]
                ):
                    raise GateError(f"Out-of-scope change: {path}")
            validate_report(report, state, task, changed)
            evidence_hashes = {}
            for check in report["verification"]:
                for name in check["evidencePaths"]:
                    path = resolve(root, name)
                    if (
                        not path.is_relative_to(folder.resolve())
                        or path.suffix != ".log"
                        or not path.is_file()
                    ):
                        raise GateError(
                            f"Worker evidence must be an existing attempt-local log: {name}"
                        )
                    evidence_hashes[name] = digest(path)
            state["workerEvidenceHashes"] = evidence_hashes
            state.update(
                status=report["status"],
                after=after,
                changedFiles=changed,
                workerReport=report,
            )
        except (GateError, OSError, ValueError) as exc:
            state.update(
                status="interrupted"
                if isinstance(exc, ExecutionInterrupted)
                else "failed",
                error=str(exc),
            )
        persist(root, state, "worker_finished")
        save(folder / "result.json", state)
        return state


def verify(root: Path) -> dict:
    with lock(root):
        state_path = root / ".workflow/state.json"
        state = load(state_path)
        if state["status"] != "ready_for_review":
            raise GateError("Attempt is not ready for review")
        task = revalidate(root, state)
        folder = resolve(root, state["folder"])
        results = []
        for index, argv in enumerate(task["verification"]):
            try:
                code = command(
                    argv, root, folder / f"check-{index}", task["timeoutSeconds"]
                )
            except (GateError, OSError) as exc:
                state.update(
                    status="interrupted"
                    if isinstance(exc, ExecutionInterrupted)
                    else "changes_requested",
                    checks=results,
                    failedCheckIndex=index,
                    error=str(exc),
                )
                persist(root, state, "verification_failed")
                save(folder / "verification.json", state)
                return state
            evidence = {
                (folder / f"check-{index}.{stream}.log")
                .relative_to(root)
                .as_posix(): digest(folder / f"check-{index}.{stream}.log")
                for stream in ("stdout", "stderr")
            }
            results.append(
                {"command": argv, "exitCode": code, "evidenceHashes": evidence}
            )
        passed = (
            all(item["exitCode"] == 0 for item in results)
            and manifest(root) == state["after"]
        )
        state.update(
            status="verified" if passed else "changes_requested", checks=results
        )
        if validate_approvals(root, task) != state["approvalHashes"]:
            state.update(
                status="changes_requested",
                error="Approval records changed during verification",
            )
        persist(root, state, "verification_finished")
        save(folder / "verification.json", state)
        return state


def accept(root: Path, review_path: str) -> dict:
    with lock(root):
        state = load(root / ".workflow/state.json")
        if state["status"] != "verified":
            raise GateError("Independent verification must pass before acceptance")
        task = revalidate(root, state)
        review = load(resolve(root, review_path))
        exact(
            review,
            {
                "taskId",
                "attemptId",
                "contractHash",
                "reviewer",
                "decision",
                "findings",
                "rationale",
                "criteria",
            },
            "review",
        )
        for key in ("taskId", "attemptId", "contractHash"):
            if review[key] != state[key]:
                raise GateError(f"Review identity mismatch: {key}")
        if review["decision"] != "accepted" or review["findings"] != []:
            raise GateError(
                "Review contains unresolved findings or does not accept the task"
            )
        if not all(
            isinstance(review[key], str) and review[key].strip()
            for key in ("reviewer", "rationale")
        ):
            raise GateError(
                "Review requires reviewer identity and substantive rationale"
            )
        if len(state["checks"]) != len(task["verification"]):
            raise GateError("Incomplete independent verification")
        validate_criteria(task)
        validate_dependencies(root, task)
        decisions = review["criteria"]
        expected_ids = {item["id"] for item in task["acceptanceCriteria"]}
        if not isinstance(decisions, dict) or set(decisions) != expected_ids:
            raise GateError("Review must cover every acceptance criterion exactly once")
        for identifier, decision in decisions.items():
            if not isinstance(decision, dict):
                raise GateError(f"Invalid criterion review: {identifier}")
            exact(decision, {"passed", "rationale"}, "criterion review")
            if (
                decision["passed"] is not True
                or not isinstance(decision["rationale"], str)
                or not decision["rationale"].strip()
            ):
                raise GateError(f"Criterion not accepted: {identifier}")
        for check in state["checks"]:
            if check["exitCode"] != 0:
                raise GateError("Verification did not pass")
            for path, expected in check["evidenceHashes"].items():
                if digest(resolve(root, path)) != expected:
                    raise GateError(f"Verification evidence changed: {path}")
        state.update(
            status="accepted",
            review=review,
            reviewHash=digest(resolve(root, review_path)),
        )
        persist(root, state, "accepted")
        save(resolve(root, state["folder"]) / "acceptance.json", state)
        save(root / ".workflow/accepted" / f"{state['taskId']}.json", state)
        return state


def reconcile_report(root: Path, reason: str) -> dict:
    """Repair only a measured file-list omission; retain the original worker report."""
    if not reason.strip():
        raise GateError("Reconciliation requires an explicit review reason")
    with lock(root):
        state = load(root / ".workflow/state.json")
        if (
            state.get("status") != "failed"
            or state.get("error") != "Reported files do not match measured changes"
        ):
            raise GateError("Only a file-list mismatch is eligible for reconciliation")
        task = load(resolve(root, state["contractPath"]))
        if digest(resolve(root, state["contractPath"])) != state["contractHash"]:
            raise GateError("Contract changed")
        if (
            validate_approvals(root, task) != state["approvalHashes"]
            or validate_skills(root, task) != state["skillHashes"]
        ):
            raise GateError("Approval or skill binding changed")
        after = manifest(root)
        changed = sorted(
            name
            for name in after.keys() | state["before"].keys()
            if after.get(name) != state["before"].get(name)
        )
        for name in changed:
            if not any(
                path_matches_scope(name, scope)
                for scope in task["allowedPaths"]
            ):
                raise GateError(f"Out-of-scope change: {name}")
        folder = resolve(root, state["folder"])
        report = load(folder / "report.json")
        original_hash = digest(folder / "report.json")
        report["changedFiles"] = changed
        validate_report(report, state, task, changed)
        if report["status"] != "ready_for_review":
            raise GateError("Report is not review-ready")
        evidence = {}
        for check in report["verification"]:
            for name in check["evidencePaths"]:
                path = resolve(root, name)
                if (
                    not path.is_relative_to(folder)
                    or path.suffix != ".log"
                    or not path.is_file()
                ):
                    raise GateError("Invalid worker evidence path")
                evidence[name] = digest(path)
        save(folder / "report-reconciled.json", report)
        state.update(
            status="ready_for_review",
            after=after,
            changedFiles=changed,
            workerReport=report,
            workerEvidenceHashes=evidence,
            reportReconciliation={
                "reason": reason,
                "originalReportHash": original_hash,
            },
        )
        revalidate(root, state)
        state.pop("error", None)
        persist(root, state, "report_reconciled")
        return state


def recover(root: Path, reason: str) -> dict:
    if not reason.strip():
        raise GateError("Recovery requires an inspection/resolution reason")
    with lock(root):
        state = load(root / ".workflow/state.json")
        if state["status"] not in {
            "failed",
            "blocked",
            "changes_requested",
            "interrupted",
        }:
            raise GateError(
                "Only failed, blocked, interrupted, or changes-requested attempts can recover"
            )
        state.update(
            status="ready", recoveryReason=reason, recoveryManifest=manifest(root)
        )
        persist(root, state, "recovered")
        return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "preflight",
            "dispatch",
            "verify",
            "accept",
            "recover",
            "reconcile-report",
            "status",
        ],
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--task", default="tasks/T001.json")
    parser.add_argument("--review", default=".workflow/reviews/current.json")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        result = {
            "preflight": lambda: preflight(root, args.task),
            "dispatch": lambda: dispatch(root, args.task),
            "verify": lambda: verify(root),
            "accept": lambda: accept(root, args.review),
            "recover": lambda: recover(root, args.reason),
            "reconcile-report": lambda: reconcile_report(root, args.reason),
            "status": lambda: load(root / ".workflow/state.json"),
        }[args.action]()
        print(json.dumps(result, indent=2))
        return (
            1
            if result.get("status") in {"failed", "interrupted", "changes_requested"}
            else 0
        )
    except (GateError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Workflow blocked: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
