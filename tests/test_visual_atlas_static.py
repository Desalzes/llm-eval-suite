"""Static wiring checks for the visual atlas.

Counts/fixtures live in the generated atlas-data.js (see generate_atlas_data.py
and test_generate_atlas_data.py for the data-correctness checks). These tests
only assert the page is wired together correctly and renders from the generated
data rather than hand-maintained literals.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_visual_atlas_static_files_exist_and_wire_core_regions():
    index = ROOT / "index.html"
    assert index.exists()
    assert (ROOT / "styles.css").exists()
    assert (ROOT / "app.js").exists()
    assert (ROOT / "codex_runner.py").exists()
    assert (ROOT / "atlas-data.js").exists()
    assert (ROOT / "leaderboard-data.js").exists()

    html = index.read_text(encoding="utf-8")
    assert '<main class="atlas-shell">' in html
    assert 'id="fixture-grid"' in html
    assert 'id="detail-panel"' in html
    assert 'id="reference-list"' in html
    assert 'id="leaderboard-preview"' in html
    assert "codex_runner.py" in html

    # The generated data must load before the app script that consumes it.
    assert 'src="atlas-data.js"' in html
    assert 'src="leaderboard-data.js"' in html
    assert 'src="app.js"' in html
    assert html.index('atlas-data.js') < html.index('app.js')
    assert html.index('leaderboard-data.js') < html.index('app.js')


def test_app_renders_from_generated_data_not_hardcoded():
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    assert "window.ATLAS_DATA" in app
    assert "window.LEADERBOARD_DATA" in app
    # The fixture corpus is no longer hand-maintained inside app.js.
    assert "const fixtures = [" not in app


def test_atlas_data_defines_window_global_with_core_keys():
    data = (ROOT / "atlas-data.js").read_text(encoding="utf-8")
    assert data.startswith("// AUTO-GENERATED")
    assert "window.ATLAS_DATA = " in data
    for key in ['"summary"', '"categories"', '"palette"', '"evalSets"', '"fixtures"']:
        assert key in data


def test_atlas_data_includes_expected_categories():
    data = (ROOT / "atlas-data.js").read_text(encoding="utf-8")
    for category in ["Bugfix", "Policy", "Safety", "Skill", "Frontend", "Innovation"]:
        assert f'"{category}"' in data
