"""Verify adapter argument boundaries without spending model tokens."""

from pathlib import Path
import tempfile
import unittest
import json

from opencode_worker import build_command


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.contract = Path(self.directory.name) / "task with spaces.json"
        self.contract.write_text("{}")
        self.env = {
            "WORKFLOW_REPORT": str(Path(self.directory.name) / "report.json"),
            "WORKFLOW_TASK_ID": "T001",
            "WORKFLOW_ATTEMPT_ID": "1",
            "WORKFLOW_CONTRACT_HASH": "abc",
        }

    def test_explicit_permission_policy_and_file_argument(self):
        argv = build_command(
            "opencode.exe", self.contract, "build", None, False, self.env
        )
        self.assertNotIn("--auto", argv)
        self.assertEqual(argv[argv.index("--file") + 1], str(self.contract.resolve()))
        self.assertEqual(argv[argv.index("--format") + 1], "json")

    def test_model_override_and_auto_are_opt_in(self):
        argv = build_command(
            "opencode.exe", self.contract, "build", "provider/model", True, self.env
        )
        self.assertIn("--auto", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "provider/model")

    def test_rejects_unassigned_execution(self):
        with self.assertRaisesRegex(ValueError, "runner"):
            build_command("opencode.exe", self.contract, "build", None, False, {})

    def test_required_skill_is_attached(self):
        skill = self.contract.parent / "SKILL.md"
        skill.write_text("Follow the task contract")
        self.env["WORKFLOW_SKILL_FILES"] = json.dumps([str(skill)])
        argv = build_command(
            "opencode.exe", self.contract, "build", None, False, self.env
        )
        self.assertEqual(argv.count("--file"), 2)
        self.assertIn(str(skill.resolve()), argv)

    def test_fallback_sequence_on_primary_failure(self):
        from unittest.mock import patch, MagicMock
        from opencode_worker import main
        import sys

        test_args = [
            "opencode_worker.py",
            "--executable", "opencode.exe",
            "--contract", str(self.contract),
            "--agent", "build",
        ]
        # Simulate primary failure (1), then fallback-1 success (0)
        mock_proc_fail = MagicMock(returncode=1)
        mock_proc_ok = MagicMock(returncode=0)

        with patch.dict("os.environ", self.env, clear=True), \
             patch.object(sys, "argv", test_args), \
             patch("subprocess.run", side_effect=[mock_proc_fail, mock_proc_ok]) as mock_run:
            ret = main()
            self.assertEqual(ret, 0)
            self.assertEqual(mock_run.call_count, 2)
            first_call_argv = mock_run.call_args_list[0][0][0]
            second_call_argv = mock_run.call_args_list[1][0][0]
            self.assertEqual(first_call_argv[first_call_argv.index("--agent") + 1], "build")
            self.assertEqual(second_call_argv[second_call_argv.index("--agent") + 1], "build-fallback")


if __name__ == "__main__":
    unittest.main()
