from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_leaderboard_page_wires_data_then_app():
    html = (ROOT / "leaderboard.html").read_text(encoding="utf-8")
    assert (ROOT / "leaderboard.js").exists()
    assert (ROOT / "leaderboard-data.js").exists()
    assert 'id="leaderboard-table"' in html
    assert 'src="leaderboard-data.js"' in html
    assert 'src="leaderboard.js"' in html
    assert html.index("leaderboard-data.js") < html.index("leaderboard.js")
    assert "self-reported" in html  # caveat present


def test_leaderboard_js_is_data_driven():
    js = (ROOT / "leaderboard.js").read_text(encoding="utf-8")
    assert "window.LEADERBOARD_DATA" in js
    assert "const entries = [" not in js  # not hand-maintained
