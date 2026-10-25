"""JSON transport inspection uses observed OpenCode event shapes."""

import json
from pathlib import Path
import tempfile
import unittest

from transport import inspect_transport


class TransportTests(unittest.TestCase):
    def inspect(self, lines):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.log"
            path.write_text("\n".join(lines), encoding="utf-8")
            return inspect_transport(path)

    def test_observed_text_event_is_not_report(self):
        result = self.inspect(
            [
                json.dumps(
                    {
                        "type": "text",
                        "sessionID": "ses_test",
                        "part": {"text": "WORKFLOW_TRANSPORT_OK"},
                    }
                )
            ]
        )
        self.assertEqual(result["sessions"], ["ses_test"])
        self.assertEqual(result["events"], 1)
        self.assertNotIn("status", result)

    def test_errors_and_non_json_output_are_recorded(self):
        result = self.inspect(
            ["plain output", json.dumps({"type": "error", "error": "provider failed"})]
        )
        self.assertEqual(result["invalidLines"], 1)
        self.assertEqual(len(result["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
