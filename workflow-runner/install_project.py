"""Install project-local executor skills and Hermes orchestration instructions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time


def install(root: Path) -> Path:
    if not root.is_dir():
        raise ValueError("Project directory must already exist")
    source = Path(__file__).resolve().parent
    destinations = {
        root / ".opencode/skills/task-contract-execution/SKILL.md": source
        / "skills/task-contract-execution/SKILL.md",
        root / ".opencode/skills/structured-handoff/SKILL.md": source
        / "skills/structured-handoff/SKILL.md",
        root / ".workflow/instructions/gated-project-orchestration.md": source
        / "skills/gated-project-orchestration/SKILL.md",
    }
    stamp = str(time.time_ns())
    backup = root / ".workflow/install-backups" / stamp
    entries = []
    for target, origin in destinations.items():
        if target.exists() and target.read_bytes() == origin.read_bytes():
            continue
        if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Installation target escapes project: {target}")
        relative = target.relative_to(root)
        entry = {"path": relative.as_posix(), "existed": target.exists()}
        if target.exists():
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
        entry["installedHash"] = hashlib.sha256(target.read_bytes()).hexdigest()
        entries.append(entry)
    backup.mkdir(parents=True, exist_ok=True)
    manifest = backup / "manifest.json"
    manifest.write_text(
        json.dumps({"files": entries}, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    print(install(args.root.resolve()))


if __name__ == "__main__":
    main()
