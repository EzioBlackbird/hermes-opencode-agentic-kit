"""Inspect OpenCode JSON-lines transport without treating text as a task report."""

from __future__ import annotations

import json
from pathlib import Path


def inspect_transport(path: Path) -> dict:
    sessions: set[str] = set()
    errors: list[dict] = []
    events = 0
    invalid_lines = 0
    if not path.exists():
        return {"events": 0, "sessions": [], "errors": [], "invalidLines": 0}
    with path.open(encoding="utf-8-sig", errors="replace") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue
            if not isinstance(item, dict) or not isinstance(item.get("type"), str):
                invalid_lines += 1
                continue
            events += 1
            session = item.get("sessionID")
            if isinstance(session, str):
                sessions.add(session)
            if item["type"] == "error":
                errors.append(item)
    return {
        "events": events,
        "sessions": sorted(sessions),
        "errors": errors,
        "invalidLines": invalid_lines,
    }
