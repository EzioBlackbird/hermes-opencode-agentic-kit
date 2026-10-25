"""Publish canonical workflow snapshots as comments on explicitly mapped tickets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


def synchronize(root: Path, state: dict) -> dict:
    config_path = root / ".workflow/kanban.json"
    if not config_path.exists():
        return {"status": "disabled"}
    destination = root / ".workflow/kanban-sync.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if not {"command", "board", "tickets"} <= set(config) or set(config) - {
            "command",
            "board",
            "tickets",
            "syncStatus",
        }:
            raise ValueError(
                "Kanban configuration requires command, board, and tickets"
            )
        command = config["command"]
        if type(config.get("syncStatus", False)) is not bool:
            raise ValueError("syncStatus must be a boolean")
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(arg, str) and arg for arg in command)
        ):
            raise ValueError("Kanban command must be an argument array")
        if not isinstance(config["board"], str) or not config["board"].strip():
            raise ValueError("An explicit Kanban board is required")
        ticket = config["tickets"].get(state["taskId"])
        if not isinstance(ticket, str) or not ticket.strip() or ticket.startswith("-"):
            raise ValueError("Task has no valid explicit Kanban ticket mapping")
        snapshot = {key: state[key] for key in ("taskId", "attemptId", "status")}
        message = json.dumps(snapshot, sort_keys=True)
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "snapshot": snapshot,
                    "board": config["board"],
                    "ticket": ticket,
                    "syncStatus": config.get("syncStatus", False),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        if destination.exists():
            previous = json.loads(destination.read_text(encoding="utf-8"))
            if (
                previous.get("fingerprint") == fingerprint
                and previous.get("status") == "synced"
            ):
                return previous
        result = subprocess.run(
            [
                *command,
                "kanban",
                "--board",
                config["board"],
                "comment",
                ticket,
                f"[workflow:{fingerprint}] Canonical workflow state: {message}",
                "--author",
                "workflow-runner",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode:
            raise ValueError(
                f"Kanban command exited {result.returncode}: {result.stderr[-1000:]}"
            )
        transition = None
        if config.get("syncStatus", False):
            if state["status"] == "accepted":
                transition = ["complete", ticket, "--result", message]
            elif state["status"] in {
                "failed",
                "blocked",
                "interrupted",
                "changes_requested",
            }:
                transition = [
                    "block",
                    ticket,
                    state.get("error", message),
                    "--kind",
                    "needs_input",
                ]
            if transition:
                result = subprocess.run(
                    [*command, "kanban", "--board", config["board"], *transition],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode:
                    raise ValueError(
                        f"Kanban transition exited {result.returncode}: {result.stderr[-1000:]}"
                    )
        status = {
            "status": "synced",
            "fingerprint": fingerprint,
            "ticket": ticket,
            "transition": transition[0] if transition else None,
        }
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as exc:
        status = {"status": "pending", "error": str(exc)}
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return status
