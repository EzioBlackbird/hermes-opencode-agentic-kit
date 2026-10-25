"""Project installation preserves preexisting instructions."""

from pathlib import Path
import json
import tempfile
import unittest

from install_project import install


class InstallTests(unittest.TestCase):
    def test_backups_and_idempotency(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / ".opencode/skills/task-contract-execution/SKILL.md"
            target.parent.mkdir(parents=True)
            target.write_text("Existing user instructions")
            manifest = install(root)
            self.assertEqual(
                (manifest.parent / target.relative_to(root)).read_text(),
                "Existing user instructions",
            )
            self.assertEqual(len(json.loads(manifest.read_text())["files"]), 3)
            repeated = install(root)
            self.assertEqual(json.loads(repeated.read_text())["files"], [])


if __name__ == "__main__":
    unittest.main()
