import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from suite.artifacts import write_validated_json
from suite.contracts import ContractValidationError


class WriteValidatedJsonTests(unittest.TestCase):

    def test_writes_when_data_is_valid(self):
        valid = {
            "run_id": "r",
            "status": "passed",
        }
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            target = tmp / "result.json"
            write_validated_json(target, "run-result", valid)
            self.assertTrue(target.exists())
            loaded = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(loaded["run_id"], "r")

    def test_raises_and_does_not_write_when_data_is_invalid(self):
        invalid = {"run_id": "r"}  # missing required 'status'
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            target = tmp / "result.json"
            with self.assertRaises(ContractValidationError):
                write_validated_json(target, "run-result", invalid)
            self.assertFalse(target.exists(), "must not write the file when validation fails")


if __name__ == "__main__":
    unittest.main()
