import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "proposal-pack"
SKILL_PATH = SKILL_DIR / "SKILL.md"
ASSET_PATH = SKILL_DIR / "assets" / "proposal-template.md"

FORBIDDEN_FILLER = [
    "customize as needed",
    "handle appropriately",
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


def test_skill_metadata_is_trigger_only_and_hyphenated() -> None:
    frontmatter, _body = _frontmatter_and_body()
    description = frontmatter["description"]
    lower_description = description.lower()

    assert set(frontmatter) == {"name", "description"}
    assert frontmatter["name"] == "proposal-pack"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", frontmatter["name"])
    assert description.startswith("Use when")
    assert len(description) <= 220
    for workflow_term in ["scope", "timeline", "pricing", "approval", "anything else"]:
        assert workflow_term not in lower_description


def test_skill_body_points_to_asset_without_embedding_template() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert len(body.split()) <= 420
    for heading in ["## overview", "## when to use", "## workflow", "## verification"]:
        assert heading in lower
    for required in ["audience", "offer", "decision stage", "deadline", "format"]:
        assert required in lower
    assert "assets/proposal-template.md" in body
    assert "read" in lower and "only" in lower and "needed" in lower
    assert "# proposal for {{client_name}}" not in lower
    assert "## project summary" not in lower
    for phrase in FORBIDDEN_FILLER:
        assert phrase not in lower


def test_asset_contains_reusable_template_with_required_sections() -> None:
    asset = ASSET_PATH.read_text(encoding="utf-8")
    lower = asset.lower()

    assert len(asset.split()) >= 120
    for placeholder in [
        "{{client_name}}",
        "{{project_summary}}",
        "{{objectives}}",
        "{{scope}}",
        "{{out_of_scope}}",
        "{{timeline}}",
        "{{assumptions}}",
        "{{pricing}}",
        "{{approval}}",
    ]:
        assert placeholder in asset
    for section in [
        "project summary",
        "objectives",
        "scope",
        "out of scope",
        "timeline",
        "assumptions",
        "pricing",
        "approval",
    ]:
        assert section in lower


def test_skill_does_not_add_extra_documentation_files() -> None:
    forbidden_docs = {"README.md", "QUICK_REFERENCE.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md"}
    present_files = {path.name for path in SKILL_DIR.rglob("*") if path.is_file()}

    assert forbidden_docs.isdisjoint(present_files)
