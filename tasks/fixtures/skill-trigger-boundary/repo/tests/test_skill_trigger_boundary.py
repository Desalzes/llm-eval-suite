import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "release-notes"
SKILL_PATH = SKILL_DIR / "SKILL.md"

FORBIDDEN_TRIGGER_TERMS = [
    "pull request",
    "pr review",
    "commit message",
    "marketing copy",
    "documentation",
    "ticket",
    "launch plan",
    "all product",
    "any product",
    "product writing",
]

FORBIDDEN_FILLER = [
    "handle appropriately",
    "as needed",
    "make the release sound good",
    "use judgment for any",
    "etc.",
]


def _frontmatter_and_body() -> tuple[dict[str, str], str]:
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    _leading, frontmatter_text, body = text.split("---", 2)
    frontmatter = {}
    for line in frontmatter_text.strip().splitlines():
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"')
    return frontmatter, body.strip()


def test_skill_metadata_is_narrow_release_notes_trigger() -> None:
    frontmatter, _body = _frontmatter_and_body()
    description = frontmatter["description"]
    lower_description = description.lower()

    assert set(frontmatter) == {"name", "description"}
    assert frontmatter["name"] == "release-notes"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", frontmatter["name"])
    assert description.startswith("Use when")
    assert len(description) <= 220
    assert "release notes" in lower_description
    assert any(term in lower_description for term in ["changelog", "shipped changes", "product changes"])
    for forbidden in FORBIDDEN_TRIGGER_TERMS:
        assert forbidden not in lower_description


def test_skill_body_declares_non_use_cases_and_required_inputs() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert len(body.split()) <= 480
    for heading in ["## overview", "## when to use", "## do not use for", "## workflow", "## verification"]:
        assert heading in lower
    for required in ["audience", "release period", "version", "source list", "tone", "shipped changes"]:
        assert required in lower
    for non_use in ["commit messages", "pull request reviews", "marketing copy", "general documentation"]:
        assert non_use in lower


def test_skill_workflow_is_grounded_in_sources_and_avoids_invention() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert "ask" in lower and "missing" in lower
    assert "do not invent" in lower or "must not invent" in lower
    for item in ["changes", "dates", "audiences", "source links"]:
        assert item in lower
    assert "source" in lower and any(term in lower for term in ["cite", "link", "trace"])
    assert "user-facing" in lower
    assert "internal" in lower
    assert any(term in lower for term in ["chores", "refactors", "maintenance"])
    assert "uncertainty" in lower or "unknown" in lower


def test_skill_body_avoids_broad_trigger_language_and_filler() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    for forbidden in FORBIDDEN_FILLER:
        assert forbidden not in lower
    for broad in ["all product writing", "any product update", "whatever context exists"]:
        assert broad not in lower


def test_skill_does_not_add_extra_documentation_files() -> None:
    forbidden_docs = {"README.md", "QUICK_REFERENCE.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md"}
    present_files = {path.name for path in SKILL_DIR.rglob("*") if path.is_file()}

    assert forbidden_docs.isdisjoint(present_files)
