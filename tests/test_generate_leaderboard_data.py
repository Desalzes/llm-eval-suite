import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import generate_leaderboard_data as gen


def _entry(slug, rate, unsafe=0, ti=None, to=None, secs=None):
    return {
        "set_id": "smoke", "agent_label": slug, "model": "m",
        "status_counts": {"passed": 1, "unsafe": unsafe} if unsafe else {"passed": 1},
        "aggregate_stats": {"weighted_pass_rate": rate},
        "tokens_in": ti, "tokens_out": to, "wall_clock_seconds": secs,
        "metrics_self_reported": True,
    }


def _write(root, slug, entry):
    d = root / "leaderboard" / "entries"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.json").write_text(json.dumps(entry), encoding="utf-8")


def test_ranks_by_pass_rate_then_tokens(tmp_path):
    _write(tmp_path, "a", _entry("a", 0.8, ti=900, to=100))   # 0.8, 1000 tok
    _write(tmp_path, "b", _entry("b", 0.8, ti=400, to=100))   # 0.8, 500 tok -> ranks ABOVE a
    _write(tmp_path, "c", _entry("c", 0.5, ti=10, to=10))     # lower pass-rate -> below both
    data = gen.build_leaderboard_data(tmp_path)
    order = [r["agent_label"] for r in data["entries"]]
    assert order == ["b", "a", "c"]
    assert [r["rank"] for r in data["entries"]] == [1, 2, 3]
    assert data["entries"][0]["tokens_total"] == 500


def test_unsafe_entries_sorted_below_clean(tmp_path):
    _write(tmp_path, "clean", _entry("clean", 0.4))           # clean, low pass
    _write(tmp_path, "risky", _entry("risky", 0.95, unsafe=2))  # high pass BUT unsafe
    data = gen.build_leaderboard_data(tmp_path)
    order = [r["agent_label"] for r in data["entries"]]
    assert order == ["clean", "risky"]   # unsafe sorted last despite higher pass-rate
    assert data["entries"][1]["unsafe"] == 2


def test_emits_loadable_js(tmp_path):
    _write(tmp_path, "a", _entry("a", 1.0, ti=1, to=1))
    out = tmp_path / "leaderboard-data.js"
    gen.write_leaderboard_data_js(tmp_path, out)
    text = out.read_text(encoding="utf-8")
    assert text.startswith("// AUTO-GENERATED")
    blob = text.split("window.LEADERBOARD_DATA = ", 1)[1].rsplit(";", 1)[0].strip()
    parsed = json.loads(blob)
    assert parsed["count"] == 1 and parsed["entries"][0]["rank"] == 1
