"""Regression checks for gate validation and review integrity."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import workflow as w


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.git("init")
        self.git("config", "user.name", "Workflow Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.root / ".gitignore").write_text(
            "artifacts/\n.workflow/state.json\n.workflow/runner.lock\ntasks/\n"
        )
        (self.root / "requirements.md").write_text("Create a result file.")
        (self.root / "design.md").write_text("Use result.txt.")
        for gate, document in [
            ("requirements", "requirements.md"),
            ("design", "design.md"),
        ]:
            w.save(
                self.root / f".workflow/{gate}.json",
                {
                    "gate": gate,
                    "decision": "approved",
                    "evidence": "Test fixture approval",
                    "documentHashes": {document: w.digest(self.root / document)},
                },
            )
        self.git("add", ".")
        self.git("commit", "-m", "test: establish approved baseline")
        worker = (
            "import os,json,pathlib; p=pathlib.Path('result.txt'); changed=not p.exists() or p.read_text()!='ok'; p.write_text('ok'); "
            "r={k:os.environ[v] for k,v in [('taskId','WORKFLOW_TASK_ID'),"
            "('attemptId','WORKFLOW_ATTEMPT_ID'),('contractHash','WORKFLOW_CONTRACT_HASH')]};"
            "r.update(status='ready_for_review',summary='Result created');"
            "log=pathlib.Path(os.environ['WORKFLOW_REPORT']).with_name('fixture.log'); log.write_text('Fixture worker completed; independent checks remain required');"
            "r.update(schemaVersion=1,changedFiles=['result.txt'] if changed else [],verification=[{'checkIndex':0,'exitCode':0,'evidencePaths':[log.relative_to(pathlib.Path.cwd()).as_posix()]}],blockers=[],changeRequests=[],remainingConcerns=[]);"
            "pathlib.Path(os.environ['WORKFLOW_REPORT']).write_text(json.dumps(r))"
        )
        self.task = {
            "schemaVersion": 1,
            "projectId": "test-project",
            "title": "Create result file",
            "objective": "Write the required result for independent verification",
            "contextFiles": ["requirements.md", "design.md"],
            "nonGoals": ["Do not change approval documents"],
            "taskId": "T001",
            "baseRevision": self.git("rev-parse", "HEAD"),
            "approvalFiles": [".workflow/requirements.json", ".workflow/design.json"],
            "allowedPaths": ["result.txt"],
            "verification": [
                [
                    sys.executable,
                    "-c",
                    "from pathlib import Path; assert Path('result.txt').read_text() == 'ok'",
                ]
            ],
            "workerCommand": [sys.executable, "-c", worker],
            "timeoutSeconds": 10,
            "dependsOn": [],
            "requiredSkills": {},
            "testStrategy": {
                "mode": "verification",
                "testFiles": [],
                "redCheckIndexes": [],
                "failureMarkers": [],
            },
            "acceptanceCriteria": [
                {"id": "AC1", "description": "Result contains ok", "checkIndexes": [0]}
            ],
        }
        self.write_task()

    def git(self, *args):
        result = subprocess.run(
            ["git", "-C", str(self.root), *args], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def write_task(self):
        w.save(self.root / "tasks/T001.json", self.task)

    def test_success_requires_independent_verification(self):
        self.assertEqual(
            w.dispatch(self.root, "tasks/T001.json")["status"], "ready_for_review"
        )
        self.assertEqual(w.verify(self.root)["status"], "verified")

    def test_missing_gate_blocks_worker(self):
        self.task["approvalFiles"] = [".workflow/design.json"]
        self.write_task()
        with self.assertRaisesRegex(w.GateError, "approvalFiles"):
            w.dispatch(self.root, "tasks/T001.json")
        self.assertFalse((self.root / "result.txt").exists())

    def test_stale_approval(self):
        (self.root / "design.md").write_text("Changed design")
        self.git("add", ".")
        self.git("commit", "-m", "test: change approved document")
        self.task["baseRevision"] = self.git("rev-parse", "HEAD")
        self.write_task()
        with self.assertRaisesRegex(w.GateError, "Stale"):
            w.preflight(self.root, "tasks/T001.json")

    def test_out_of_scope_change(self):
        self.task["allowedPaths"] = ["other.txt"]
        self.write_task()
        self.assertEqual(w.dispatch(self.root, "tasks/T001.json")["status"], "failed")

    def test_source_change_invalidates_review(self):
        w.dispatch(self.root, "tasks/T001.json")
        (self.root / "result.txt").write_text("different")
        with self.assertRaisesRegex(w.GateError, "Source changed"):
            w.verify(self.root)

    def test_failed_acceptance_check(self):
        self.task["verification"] = [[sys.executable, "-c", "raise SystemExit(1)"]]
        self.write_task()
        w.dispatch(self.root, "tasks/T001.json")
        self.assertEqual(w.verify(self.root)["status"], "changes_requested")

    def test_lock_prevents_concurrent_dispatch(self):
        with w.lock(self.root):
            with self.assertRaisesRegex(w.GateError, "locked"):
                w.dispatch(self.root, "tasks/T001.json")

    def test_path_traversal_rejected(self):
        for name in ["../outside", "C:/Windows", "/absolute", "file:stream"]:
            with self.subTest(name=name), self.assertRaises(w.GateError):
                w.resolve(self.root, name)

    def review(self, state):
        path = ".workflow/reviews/current.json"
        w.save(
            self.root / path,
            {
                "taskId": state["taskId"],
                "attemptId": state["attemptId"],
                "contractHash": state["contractHash"],
                "reviewer": "test-reviewer",
                "decision": "accepted",
                "findings": [],
                "rationale": "The result matches the required content and independent check.",
                "criteria": {
                    "AC1": {
                        "passed": True,
                        "rationale": "Content assertion passed and matches the requirement.",
                    }
                },
            },
        )
        return path

    def test_acceptance_requires_review_and_preserves_evidence(self):
        w.dispatch(self.root, "tasks/T001.json")
        state = w.verify(self.root)
        path = self.review(state)
        self.assertEqual(w.accept(self.root, path)["status"], "accepted")

    def test_tampered_evidence_blocks_acceptance(self):
        w.dispatch(self.root, "tasks/T001.json")
        state = w.verify(self.root)
        path = self.review(state)
        evidence = next(iter(state["checks"][0]["evidenceHashes"]))
        (self.root / evidence).write_text("fabricated")
        with self.assertRaisesRegex(w.GateError, "evidence changed"):
            w.accept(self.root, path)

    def test_changed_approval_blocks_verification(self):
        w.dispatch(self.root, "tasks/T001.json")
        path = self.root / ".workflow/design.json"
        approval = w.load(path)
        approval["evidence"] = "Different approval"
        w.save(path, approval)
        with self.assertRaisesRegex(w.GateError, "Approval records changed"):
            w.verify(self.root)

    def test_failed_attempt_requires_explicit_recovery(self):
        self.task["workerCommand"] = [sys.executable, "-c", "raise SystemExit(2)"]
        self.write_task()
        self.assertEqual(w.dispatch(self.root, "tasks/T001.json")["status"], "failed")
        with self.assertRaises(w.GateError):
            w.recover(self.root, "")
        self.assertEqual(
            w.recover(self.root, "Inspected logs; worker exited before edits")[
                "status"
            ],
            "ready",
        )

    def test_unaccepted_dependency_blocks_dispatch(self):
        self.task["dependsOn"] = ["T000"]
        self.write_task()
        with self.assertRaisesRegex(w.GateError, "Dependency not accepted"):
            w.dispatch(self.root, "tasks/T001.json")

    def test_criterion_requires_real_check(self):
        self.task["acceptanceCriteria"][0]["checkIndexes"] = [99]
        self.write_task()
        with self.assertRaisesRegex(w.GateError, "existing verification"):
            w.preflight(self.root, "tasks/T001.json")

    def test_review_cannot_omit_criterion(self):
        w.dispatch(self.root, "tasks/T001.json")
        state = w.verify(self.root)
        path = self.review(state)
        review = w.load(self.root / path)
        review["criteria"] = {}
        w.save(self.root / path, review)
        with self.assertRaisesRegex(w.GateError, "every acceptance criterion"):
            w.accept(self.root, path)

    def accept_first_task(self):
        w.dispatch(self.root, "tasks/T001.json")
        state = w.verify(self.root)
        w.accept(self.root, self.review(state))
        return {**self.task, "taskId": "T002", "dependsOn": ["T001"]}

    def test_valid_accepted_dependency(self):
        second = self.accept_first_task()
        w.validate_dependencies(self.root, second)

    def test_dependency_invalidated_by_changed_requirements(self):
        second = self.accept_first_task()
        (self.root / "requirements.md").write_text("A different product requirement")
        with self.assertRaisesRegex(w.GateError, "Stale approval"):
            w.validate_dependencies(self.root, second)

    def test_dependency_invalidated_even_after_new_approval(self):
        second = self.accept_first_task()
        document = self.root / "requirements.md"
        document.write_text("A newly approved requirement")
        path = self.root / ".workflow/requirements.json"
        approval = w.load(path)
        approval["documentHashes"]["requirements.md"] = w.digest(document)
        w.save(path, approval)
        with self.assertRaisesRegex(w.GateError, "Dependency approvals changed"):
            w.validate_dependencies(self.root, second)

    def test_dependency_contract_mutation(self):
        second = self.accept_first_task()
        self.task["timeoutSeconds"] = 20
        self.write_task()
        with self.assertRaisesRegex(w.GateError, "Dependency contract changed"):
            w.validate_dependencies(self.root, second)

    def test_two_serial_tasks(self):
        second = self.accept_first_task()
        self.git("add", ".")
        self.git("commit", "-m", "test: preserve first accepted result")
        second["baseRevision"] = self.git("rev-parse", "HEAD")
        w.save(self.root / "tasks/T002.json", second)
        state = w.dispatch(self.root, "tasks/T002.json")
        self.assertEqual(state["status"], "ready_for_review", state.get("error"))
        self.assertEqual(state["attemptCount"], 1)

    def test_verification_missing_executable_is_recorded(self):
        self.task["verification"] = [[str(self.root / "missing-tool.exe")]]
        self.write_task()
        w.dispatch(self.root, "tasks/T001.json")
        state = w.verify(self.root)
        self.assertEqual(state["status"], "changes_requested")
        self.assertEqual(state["failedCheckIndex"], 0)
        self.assertEqual(
            w.load(self.root / ".workflow/state.json")["status"], "changes_requested"
        )

    def test_verification_timeout_requires_recovery(self):
        self.task["timeoutSeconds"] = 1
        self.task["verification"] = [
            [sys.executable, "-c", "import time; time.sleep(10)"]
        ]
        self.write_task()
        w.dispatch(self.root, "tasks/T001.json")
        state = w.verify(self.root)
        self.assertEqual(state["status"], "interrupted")
        self.assertEqual(state["failedCheckIndex"], 0)

    def test_missing_required_skill_blocks_preflight(self):
        self.task["requiredSkills"] = {"task-contract-execution": "skills/missing.md"}
        self.write_task()
        with self.assertRaisesRegex(w.GateError, "Required skill unavailable"):
            w.preflight(self.root, "tasks/T001.json")

    def test_skill_change_invalidates_review(self):
        skill = self.root / ".workflow/skills/execution.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("Follow the approved task contract.")
        self.git("add", ".")
        self.git("commit", "-m", "test: bind executor instructions")
        self.task["baseRevision"] = self.git("rev-parse", "HEAD")
        self.task["requiredSkills"] = {
            "task-contract-execution": ".workflow/skills/execution.md"
        }
        self.write_task()
        w.dispatch(self.root, "tasks/T001.json")
        skill.write_text("Different execution rules")
        with self.assertRaisesRegex(w.GateError, "skill instructions changed"):
            w.verify(self.root)

    def test_runner_records_red_before_worker_then_green(self):
        check = self.root / "behavior_check.py"
        check.write_text(
            "from pathlib import Path\np=Path('result.txt')\nassert p.exists() and p.read_text() == 'ok', 'EXPECTED_RESULT_MISSING'\n"
        )
        self.git("add", ".")
        self.git("commit", "-m", "test: add behavioral red checkpoint")
        self.task["baseRevision"] = self.git("rev-parse", "HEAD")
        self.task["verification"] = [[sys.executable, "-B", "behavior_check.py"]]
        self.task["testStrategy"] = {
            "mode": "tdd",
            "testFiles": ["behavior_check.py"],
            "redCheckIndexes": [0],
            "failureMarkers": ["EXPECTED_RESULT_MISSING"],
        }
        self.write_task()
        state = w.dispatch(self.root, "tasks/T001.json")
        self.assertEqual(state["status"], "ready_for_review", state.get("error"))
        self.assertNotEqual(state["redCheckpoint"]["checks"][0]["exitCode"], 0)
        self.assertEqual(w.verify(self.root)["status"], "verified")

    def test_missing_context_blocks_dispatch(self):
        self.task["contextFiles"] = ["missing-context.md"]
        self.write_task()
        with self.assertRaisesRegex(w.GateError, "Context file missing"):
            w.preflight(self.root, "tasks/T001.json")

    def test_cross_project_dependency_is_rejected(self):
        second = self.accept_first_task()
        second["projectId"] = "different-project"
        with self.assertRaisesRegex(w.GateError, "another project"):
            w.validate_dependencies(self.root, second)

    def test_worker_evidence_tampering_blocks_review(self):
        state = w.dispatch(self.root, "tasks/T001.json")
        evidence = next(iter(state["workerEvidenceHashes"]))
        (self.root / evidence).write_text("Changed worker log")
        with self.assertRaisesRegex(w.GateError, "Worker evidence changed"):
            w.verify(self.root)

    def test_reconcile_preserves_original_and_requires_verification(self):
        self.task["workerCommand"][2] = self.task["workerCommand"][2].replace(
            "changedFiles=['result.txt'] if changed else []", "changedFiles=[]"
        )
        self.write_task()
        state = w.dispatch(self.root, "tasks/T001.json")
        self.assertEqual(state["status"], "failed")
        original = self.root / state["folder"] / "report.json"
        original_hash = w.digest(original)
        state = w.reconcile_report(
            self.root,
            "Inspected actual diff; worker omitted the authorized result file",
        )
        self.assertEqual(state["status"], "ready_for_review")
        self.assertEqual(w.digest(original), original_hash)
        self.assertEqual(state["attemptCount"], 1)
        self.assertEqual(w.verify(self.root)["status"], "verified")


if __name__ == "__main__":
    unittest.main()
