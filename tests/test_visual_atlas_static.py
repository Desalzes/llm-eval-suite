"""Static wiring checks for the single-page scorecard app.

Data correctness lives in the generated *-data.js (see test_generate_atlas_data.py
for atlas data and test_setups.py for setups data). These tests only assert the
page is wired together and renders from the generated globals, not from literals.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_static_files_exist():
    for name in ["index.html", "styles.css", "app.js",
                 "atlas-data.js", "leaderboard-data.js", "setups-data.js",
                 "trials-data.js"]:
        assert (ROOT / name).exists(), f"missing {name}"


def test_index_wires_core_regions_and_data_order():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    # mount points the app needs
    assert 'id="app"' in html
    assert 'id="nav-links"' in html
    assert 'id="modal"' in html
    # the core routes are linked in the nav
    for route in ["#home", "#setups", "#challenges", "#trials", "#leaderboard"]:
        assert route in html
    # the data globals load BEFORE app.js (use the script src= form so the
    # header comment that names these files doesn't confuse the ordering check)
    for datafile in ["atlas-data.js", "leaderboard-data.js", "setups-data.js",
                     "trials-data.js"]:
        assert f'src="{datafile}"' in html
        assert html.index(f'src="{datafile}"') < html.index('src="app.js"')


def test_app_reads_generated_globals_not_hardcoded():
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    for g in ["window.ATLAS_DATA", "window.LEADERBOARD_DATA", "window.SETUPS_DATA",
              "window.TRIALS_DATA"]:
        assert g in app
    assert 'case "trials"' in app
    assert "trial_score" in app
    assert "trial_id" in app
    # the corpus is not hand-maintained inside app.js
    assert "const fixtures = [" not in app


def test_data_files_define_window_globals():
    for name, g in [("atlas-data.js", "window.ATLAS_DATA = "),
                    ("leaderboard-data.js", "window.LEADERBOARD_DATA = "),
                    ("setups-data.js", "window.SETUPS_DATA = "),
                    ("trials-data.js", "window.TRIALS_DATA = ")]:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert text.startswith("// AUTO-GENERATED")
        assert g in text


def test_mobile_nav_has_horizontal_overflow_guard():
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    assert "@media (max-width: 620px)" in css
    assert ".topnav { overflow-x: hidden; }" in css
    assert ".topnav .wrap { height: auto;" in css
    assert ".nav-links { order: 2; width: 100%; max-width: 100%; min-width: 0; margin-left: 0; overflow-x: auto;" in css
    assert ".brand .brand-name { white-space: nowrap;" in css


def test_mobile_trial_commands_scroll_inside_not_page():
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    assert ".trial-detail-grid > div, .trial-detail-grid aside { min-width: 0; }" in css
    assert "background: #0f1722; overflow: hidden;\n  min-width: 0;" in css
    assert "line-height: 1.5;\n  min-width: 0;" in css


def test_trial_ui_is_setup_lift_focused_not_tier_focused():
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    assert "Setup lift" in app
    assert "same Trial" in app
    assert "vanilla-baseline" in app
    assert "difficulty tier" not in app.lower()
    assert "seasonal" not in app.lower()
