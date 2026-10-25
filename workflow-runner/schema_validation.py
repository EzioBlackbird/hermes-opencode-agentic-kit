"""Strict versioned document validation with field-level errors."""

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator


@lru_cache(maxsize=2)
def validator(kind: str) -> Draft202012Validator:
    if kind not in {"contract", "report"}:
        raise ValueError(f"Unknown schema: {kind}")
    schema = json.loads(
        (Path(__file__).parent / "schemas" / f"{kind}.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_document(kind: str, document: dict) -> None:
    errors = sorted(
        validator(kind).iter_errors(document),
        key=lambda error: str(list(error.absolute_path)),
    )
    if errors:
        details = "; ".join(
            f"{kind}.{'.'.join(map(str, error.absolute_path)) or '$'}: {error.message}"
            for error in errors[:5]
        )
        raise ValueError(details)
