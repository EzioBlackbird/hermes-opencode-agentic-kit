"""Runner-owned red checkpoint for prewritten immutable behavioral tests."""

import hashlib
from pathlib import Path


def validate_strategy(task: dict) -> None:
    strategy = task["testStrategy"]
    if not isinstance(strategy, dict) or set(strategy) != {
        "mode",
        "testFiles",
        "redCheckIndexes",
        "failureMarkers",
    }:
        raise ValueError("Invalid testStrategy fields")
    if strategy["mode"] not in {"verification", "tdd"}:
        raise ValueError("Unsupported test strategy")
    for key in ("testFiles", "failureMarkers"):
        if not isinstance(strategy[key], list) or not all(
            isinstance(item, str) and item.strip() for item in strategy[key]
        ):
            raise ValueError(f"Invalid testStrategy.{key}")
    indexes = strategy["redCheckIndexes"]
    if not isinstance(indexes, list) or any(
        type(i) is not int or not 0 <= i < len(task["verification"]) for i in indexes
    ):
        raise ValueError("Invalid red check indexes")
    if strategy["mode"] == "tdd" and not all(
        strategy[key] for key in ("testFiles", "redCheckIndexes", "failureMarkers")
    ):
        raise ValueError(
            "TDD requires tests, red checks, and behavioral failure markers"
        )
    if strategy["mode"] == "verification" and any(
        strategy[key] for key in ("testFiles", "redCheckIndexes", "failureMarkers")
    ):
        raise ValueError("Verification mode cannot claim red evidence")


def test_hashes(root: Path, task: dict, resolve) -> dict[str, str]:
    return {
        name: hashlib.sha256(resolve(root, name).read_bytes()).hexdigest()
        for name in task["testStrategy"]["testFiles"]
    }


def red_checkpoint(root: Path, folder: Path, task: dict, run, resolve) -> dict:
    hashes = test_hashes(root, task, resolve)
    checks = []
    for index in task["testStrategy"]["redCheckIndexes"]:
        output = folder / f"red-{index}"
        code = run(task["verification"][index], root, output, task["timeoutSeconds"])
        text = "\n".join(
            output.with_suffix(f".{stream}.log").read_text(
                encoding="utf-8", errors="replace"
            )
            for stream in ("stdout", "stderr")
        )
        if code == 0:
            raise ValueError("TDD red checkpoint unexpectedly passed")
        if any(
            marker in text
            for marker in ("ModuleNotFoundError", "ImportError", "SyntaxError")
        ):
            raise ValueError(
                "TDD red checkpoint is an environment/import/syntax failure"
            )
        if not any(marker in text for marker in task["testStrategy"]["failureMarkers"]):
            raise ValueError("TDD failure lacks expected behavioral marker")
        checks.append({"checkIndex": index, "exitCode": code})
    if hashes != test_hashes(root, task, resolve):
        raise ValueError("Red checkpoint modified test files")
    return {"testHashes": hashes, "checks": checks}
