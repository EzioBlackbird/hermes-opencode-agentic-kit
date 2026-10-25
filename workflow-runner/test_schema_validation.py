"""Schemas reject type confusion and unknown fields before execution."""

import unittest

from schema_validation import validate_document, validator


class SchemaTests(unittest.TestCase):
    def test_both_schemas_are_valid(self):
        for kind in ("contract", "report"):
            self.assertIsNotNone(validator(kind))

    def test_boolean_is_not_integer_version(self):
        with self.assertRaisesRegex(ValueError, "schemaVersion"):
            validate_document("report", {"schemaVersion": True})

    def test_unknown_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, "unexpected"):
            validate_document("contract", {"skipApproval": True})


if __name__ == "__main__":
    unittest.main()
