"""Static wiring checks for the single-page scorecard app.

Data correctness lives in the generated *-data.js (see test_generate_atlas_data.py
for atlas data and test_setups.py for setups data). These tests only assert the
page is wired together and renders from the generated globals, not from literals.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_static_files_exist():
    for name in ["index.html", "styles.css", "app.js",
                 "atlas-data.js", "leaderboard-data.js", "setups-data.js"]:
        assert (ROOT / name).exists(), f"missing {name}"


def test_index_wires_core_regions_and_data_order():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    # mount points the app needs
    assert 'id="app"' in html
    assert 'id="nav-links"' in html
    assert 'id="modal"' in html
    # the four routes are linked in the nav
    for route in ["#home", "#setups", "#challenges", "#leaderboard"]:
        assert route in html
    # the three data globals load BEFORE app.js (use the script src= form so the
    # header comment that names these files doesn't confuse the ordering check)
    for datafile in ["atlas-data.js", "leaderboard-data.js", "setups-data.js"]:
        assert f'src="{datafile}"' in html
        assert html.index(f'src="{datafile}"') < html.index('src="app.js"')


def test_app_reads_generated_globals_not_hardcoded():
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    for g in ["window.ATLAS_DATA", "window.LEADERBOARD_DATA", "window.SETUPS_DATA"]:
        assert g in app
    # the corpus is not hand-maintained inside app.js
    assert "const fixtures = [" not in app


def test_data_files_define_window_globals():
    for name, g in [("atlas-data.js", "window.ATLAS_DATA = "),
                    ("leaderboard-data.js", "window.LEADERBOARD_DATA = "),
                    ("setups-data.js", "window.SETUPS_DATA = ")]:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert text.startswith("// AUTO-GENERATED")
        assert g in text
