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


def test_render_ab_strip_markdown():
    ab = run.compute_trial_ab(_summary(score=64),
                              _summary(setup_id="ponytail", score=61))
    md = run.render_ab_strip_markdown(ab)
    assert "trial-1" in md
    assert "64 → 61" in md
    assert "−3" in md          # U+2212 minus, not hyphen
    assert "both clean" in md
    assert "n=1" in md


def test_render_ab_strip_markdown_positive_sign():
    ab = run.compute_trial_ab(_summary(score=60),
                              _summary(setup_id="ponytail", score=68))
    assert "+8" in run.render_ab_strip_markdown(ab)


def test_render_ab_strip_svg_is_selfcontained():
    ab = run.compute_trial_ab(_summary(score=64),
                              _summary(setup_id="ponytail", score=61))
    svg = run.render_ab_strip_svg(ab)
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert 'role="img"' in svg
    assert "xlink" not in svg          # no external image refs
    assert "<image" not in svg
    assert "https://" not in svg       # only the SVG namespace (http://www.w3.org/2000/svg)
    assert "61" in svg and "64" in svg


def test_xml_escape():
    assert run._xml_escape('a & b <c> "d"') == "a &amp; b &lt;c&gt; &quot;d&quot;"


def test_render_ab_strip_svg_escapes_user_text():
    import xml.dom.minidom
    ab = run.compute_trial_ab(
        _summary(trial_id="t&<x", setup_id="agentic-default", score=64),
        _summary(trial_id="t&<x", setup_id='p"<script>', score=61))
    svg = run.render_ab_strip_svg(ab)
    # well-formed XML (parses) and no raw injected markup leaked through
    xml.dom.minidom.parseString(svg)
    assert "<script>" not in svg
    assert "&amp;" in svg          # the & in trial id was escaped
    assert "&amp;amp;" not in svg  # but not double-escaped


def test_trial_ab_schema_validates_output():
    schema = json.loads((ROOT / "schemas" / "trial-ab.schema.json").read_text(encoding="utf-8"))
    ab = run.compute_trial_ab(_summary(score=64),
                              _summary(setup_id="ponytail", score=61))
    ab["generated_at"] = "20260615T000000Z"
    assert run.lightweight_validate(ab, schema) == []
    assert run.lightweight_validate({"schema": "trial-ab/v1"}, schema) != []
