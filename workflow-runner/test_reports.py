"""Worker claims must match measured scope and complete required checks."""

import unittest

from workflow import GateError, validate_report


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.state = {"taskId": "T001", "attemptId": "1", "contractHash": "abc"}
        self.task = {"verification": [["python", "check.py"]]}
        self.report = {
            **self.state,
            "schemaVersion": 1,
            "status": "ready_for_review",
            "summary": "Implemented and checked",
            "changedFiles": ["result.txt"],
            "verification": [
                {
                    "checkIndex": 0,
                    "exitCode": 0,
                    "evidencePaths": ["artifacts/T001/1/check.log"],
                }
            ],
            "blockers": [],
            "changeRequests": [],
            "remainingConcerns": [],
        }

    def test_hidden_change_is_rejected(self):
        with self.assertRaisesRegex(GateError, "measured changes"):
            validate_report(
                self.report, self.state, self.task, ["result.txt", "hidden.txt"]
            )

    def test_missing_check_is_rejected(self):
        self.report["verification"] = []
        with self.assertRaisesRegex(GateError, "missing checks"):
            validate_report(self.report, self.state, self.task, ["result.txt"])

    def test_blocked_report_preserves_reason(self):
        self.report.update(
            status="blocked", verification=[], blockers=["API decision required"]
        )
        validate_report(self.report, self.state, self.task, ["result.txt"])

    def test_failed_check_cannot_claim_ready(self):
        self.report["verification"][0]["exitCode"] = 1
        with self.assertRaisesRegex(GateError, "failed checks"):
            validate_report(self.report, self.state, self.task, ["result.txt"])


if __name__ == "__main__":
    unittest.main()
