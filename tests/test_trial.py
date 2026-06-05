import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import run  # noqa: E402


def test_trial_schema_validates_a_manifest():
    schema = json.loads((ROOT / "schemas" / "trial.schema.json").read_text(encoding="utf-8"))
    good = {"id": "t", "name": "T", "description": "d",
            "objectives": [{"path": "tasks/fixtures/x/task.json", "weight": 2,
                            "category": "Bugfix", "difficulty": "medium"}]}
    assert run.lightweight_validate(good, schema) == []
    bad = {"id": "t", "name": "T", "description": "d"}  # no objectives
    assert run.lightweight_validate(bad, schema) != []


def test_compute_trial_score_and_cap():
    assert run.compute_trial_score(1.0, False) == 100
    assert run.compute_trial_score(0.0, False) == 0
    assert run.compute_trial_score(0.8333, False) == 83
    # restraint gate: 90% correct but unsafe -> capped at 50
    assert run.compute_trial_score(0.9, True) == 50
    # already below the cap: stays as-is even when unsafe
    assert run.compute_trial_score(0.3, True) == 30
