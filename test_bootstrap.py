"""Offline regression tests for preservation and routing upgrades."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bootstrap as b


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_routing_migrates_and_preserves_personal_sections(self):
        soul = self.root / "SOUL.md"
        old = "# Personal\n\n## Gated software project routing\n\nOLD\n\n## Identity\nKeep me\n"
        soul.write_text(old, encoding="utf-8")
        b.update_routing(soul, "## Gated software project routing\n\nNEW\n")
        content = soul.read_text(encoding="utf-8")
        self.assertIn("# Personal", content)
        self.assertIn("## Identity\nKeep me", content)
        self.assertNotIn("OLD", content)
        backups = list(self.root.glob("SOUL.md.agentic-kit-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), old)
        b.update_routing(soul, "## Gated software project routing\n\nNEW\n")
        self.assertEqual(len(list(self.root.glob("SOUL.md.agentic-kit-backup-*"))), 1)

    def test_routing_created_and_versioned_update(self):
        soul = self.root / "new" / "SOUL.md"
        b.update_routing(soul, "## Gated software project routing\nold")
        b.update_routing(soul, "## Gated software project routing\nnew")
        self.assertNotIn("\nold", soul.read_text(encoding="utf-8"))
        self.assertEqual(soul.read_text(encoding="utf-8").count(b.ROUTING_START), 1)

    def test_malformed_markers_fail_without_modification(self):
        soul = self.root / "SOUL.md"
        soul.write_text(b.ROUTING_START, encoding="utf-8")
        with self.assertRaises(RuntimeError):
            b.update_routing(soul, "new")
        self.assertEqual(soul.read_text(encoding="utf-8"), b.ROUTING_START)

    def test_overlay_preserves_custom_files_and_backs_up_conflicts(self):
        source, target = self.root / "src", self.root / "dst"
        source.mkdir()
        target.mkdir()
        (source / "owned.txt").write_text("new")
        (target / "owned.txt").write_text("user edit")
        (target / "custom.txt").write_text("custom")
        b.copy_preserving(source, target)
        self.assertEqual((target / "custom.txt").read_text(), "custom")
        self.assertEqual(
            next(target.glob("owned.txt.agentic-kit-backup-*")).read_text(), "user edit"
        )
        b.copy_preserving(source, target)
        self.assertEqual(len(list(target.glob("owned.txt.agentic-kit-backup-*"))), 1)

    def test_legacy_command_directory_is_not_deleted(self):
        repo = Path(__file__).parent
        config = self.root / "config"
        legacy = config / "command"
        legacy.mkdir(parents=True)
        (legacy / "custom.md").write_text("personal command")
        b.install_cli_anything_plugin(repo, self.root / "plugin", config)
        self.assertEqual((legacy / "custom.md").read_text(), "personal command")

    def test_client_setup_creates_missing_soul_without_external_commands(self):
        hermes = self.root / "hermes"
        with patch.object(b.subprocess, "run"):
            b.configure_clients(self.root / "rea", {}, self.root / "oc", hermes)
        self.assertIn(
            "multi-model coding benchmarks",
            (hermes / "SOUL.md").read_text(encoding="utf-8"),
        )

    def test_skill_has_no_manual_state_recovery(self):
        skill = (
            Path(__file__).parent / "skills/gated-project-orchestration/SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("in_progress", skill)
        self.assertNotIn("You can synthesize", skill)
        self.assertNotIn("Persist via", skill)
        self.assertIn("Never synthesize a missing worker report", skill)
        self.assertIn("workflow.py recover", skill)

    def test_skill_defines_fullstack_ownership_and_visual_acceptance(self):
        skill = (
            Path(__file__).parent / "skills/gated-project-orchestration/SKILL.md"
        ).read_text(encoding="utf-8")
        for requirement in (
            "OpenCode owns engineering proposals and implementation for both frontend and backend",
            "do not fabricate design approval",
            "Do not assume a skill loaded in Hermes is inherited by OpenCode",
            "build success alone is not visual acceptance",
            "visual verification as incomplete, not passed",
        ):
            self.assertIn(requirement, skill)


if __name__ == "__main__":
    unittest.main()
