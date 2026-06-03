import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "browser-testing"
SKILL_PATH = SKILL_DIR / "SKILL.md"
REFERENCE_PATH = SKILL_DIR / "references" / "playwright.md"


def _skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def _frontmatter_and_body() -> tuple[dict[str, str], str]:
    text = _skill_text()
    assert text.startswith("---\n"), "SKILL.md must start with frontmatter"
    _leading, frontmatter_text, body = text.split("---", 2)
    frontmatter = {}
    for line in frontmatter_text.strip().splitlines():
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"')
    return frontmatter, body.strip()


def test_skill_metadata_is_discoverable_without_workflow_summary() -> None:
    frontmatter, _body = _frontmatter_and_body()
    description = frontmatter["description"]

    assert frontmatter["name"] == "browser-testing"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", frontmatter["name"])
    assert description.startswith("Use when")
    assert len(description) <= 180
    for shortcut in ["opening pages", "clicking controls", "recording traces", "writing playwright tests"]:
        assert shortcut not in description.lower()


def test_skill_body_is_concise_and_links_to_reference() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert len(body.split()) <= 350
    assert "## when to use" in lower
    assert "## workflow" in lower
    assert "references/playwright.md" in body
    assert "page.goto" not in body
    assert "context.tracing.start" not in body
    assert "etc." not in lower
    assert "handle appropriately" not in lower


def test_playwright_reference_contains_detailed_examples() -> None:
    reference = REFERENCE_PATH.read_text(encoding="utf-8")
    lower = reference.lower()

    assert len(reference.split()) >= 120
    for required in ["page.goto", "locator", "expect", "screenshot", "trace"]:
        assert required in lower
    assert "role" in lower or "get_by_role" in lower or "getbyrole" in lower


def test_skill_does_not_add_extra_documentation_files() -> None:
    forbidden = {
        "README.md",
        "QUICK_REFERENCE.md",
        "CHANGELOG.md",
    }
    present = {path.name for path in SKILL_DIR.rglob("*") if path.is_file()}

    assert forbidden.isdisjoint(present)
