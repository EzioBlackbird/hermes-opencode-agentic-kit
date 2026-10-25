"""Kanban projection must never dispatch workers or mutate canonical state."""

from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from kanban_projection import synchronize


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / ".workflow").mkdir()
        self.state = {"taskId": "T001", "attemptId": "1", "status": "accepted"}

    def configure(self):
        (self.root / ".workflow/kanban.json").write_text(
            json.dumps(
                {
                    "command": ["hermes"],
                    "board": "pilot",
                    "tickets": {"T001": "ticket-1"},
                }
            )
        )

    def test_disabled_without_mapping(self):
        self.assertEqual(synchronize(self.root, self.state)["status"], "disabled")

    @patch("kanban_projection.subprocess.run")
    def test_success_is_deduplicated_and_comment_only(self, run):
        self.configure()
        run.return_value = subprocess.CompletedProcess([], 0, "ok", "")
        self.assertEqual(synchronize(self.root, self.state)["status"], "synced")
        synchronize(self.root, self.state)
        run.assert_called_once()
        argv = run.call_args.args[0]
        self.assertIn("comment", argv)
        self.assertNotIn("dispatch", argv)
        self.assertNotIn("complete", argv)

    @patch("kanban_projection.subprocess.run")
    def test_failure_preserves_canonical_state(self, run):
        self.configure()
        run.side_effect = OSError("Hermes unavailable")
        before = dict(self.state)
        self.assertEqual(synchronize(self.root, self.state)["status"], "pending")
        self.assertEqual(self.state, before)

    @patch("kanban_projection.subprocess.run")
    def test_opt_in_acceptance_completes_ticket_without_force(self, run):
        self.configure()
        path = self.root / ".workflow/kanban.json"
        config = json.loads(path.read_text())
        config["syncStatus"] = True
        path.write_text(json.dumps(config))
        run.return_value = subprocess.CompletedProcess([], 0, "ok", "")
        self.assertEqual(synchronize(self.root, self.state)["transition"], "complete")
        self.assertEqual(run.call_count, 2)
        self.assertNotIn("--force", run.call_args.args[0])

    @patch("kanban_projection.subprocess.run")
    def test_transition_failure_remains_pending(self, run):
        self.configure()
        path = self.root / ".workflow/kanban.json"
        config = json.loads(path.read_text())
        config["syncStatus"] = True
        path.write_text(json.dumps(config))
        run.side_effect = [
            subprocess.CompletedProcess([], 0, "ok", ""),
            subprocess.CompletedProcess([], 1, "", "live claim"),
        ]
        self.assertEqual(synchronize(self.root, self.state)["status"], "pending")
        self.assertEqual(self.state["status"], "accepted")


if __name__ == "__main__":
    unittest.main()
