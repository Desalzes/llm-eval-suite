import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import run  # noqa: E402


def _summary(trial_id="trial-1", setup_id="agentic-default", score=64, wpr=0.64,
             unsafe=False, by_category=None):
    """A minimal trial-summary.json shaped like cmd_trial_score writes."""
    return {
        "trial_id": trial_id,
        "setup_id": setup_id,
        "trial_score": score,
        "flagged_unsafe": unsafe,
        "aggregate_stats": {"weighted_pass_rate": wpr, "passed_weight": 0, "total_weight": 0},
        "metrics": {"by_category": {
            cat: {"weighted_pass_rate": r, "passed": 0, "total": 0}
            for cat, r in (by_category or {}).items()}},
    }


def test_compute_trial_ab_delta_and_categories():
    b = _summary(score=64, by_category={"Bugfix": 0.70, "Skill": 0.55})
    t = _summary(setup_id="ponytail", score=61, by_category={"Bugfix": 0.64, "Skill": 0.64})
    ab = run.compute_trial_ab(b, t)
    assert ab["schema"] == "trial-ab/v1"
    assert ab["trial_id"] == "trial-1"
    assert ab["baseline"]["setup_id"] == "agentic-default"
    assert ab["treatment"]["setup_id"] == "ponytail"
    assert ab["delta"]["overall"] == -3
    lifts = {c["category"]: c["lift"] for c in ab["delta"]["by_category"]}
    assert lifts == {"Bugfix": -6, "Skill": 9}
    assert ab["delta"]["restraint"] == "both_clean"
    assert ab["runs_per_arm"] == 1
    assert "generated_at" not in ab  # the caller stamps it, not the pure fn


def test_compute_trial_ab_restraint_branches():
    clean_b = _summary(unsafe=False)
    unsafe_t = _summary(setup_id="ponytail", unsafe=True)
    assert run.compute_trial_ab(clean_b, unsafe_t)["delta"]["restraint"] == "treatment_violated"
    assert run.compute_trial_ab(_summary(unsafe=True), unsafe_t)["delta"]["restraint"] == "both_violated"
    assert run.compute_trial_ab(
        _summary(unsafe=True),
        _summary(setup_id="ponytail", unsafe=False))["delta"]["restraint"] == "baseline_violated"


def test_compute_trial_ab_rejects_trial_mismatch():
    with pytest.raises(ValueError):
        run.compute_trial_ab(_summary(trial_id="trial-1"),
                             _summary(trial_id="trial-2"))
