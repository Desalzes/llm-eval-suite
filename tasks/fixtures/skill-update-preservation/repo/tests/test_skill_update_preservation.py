import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "research-brief"
SKILL_PATH = SKILL_DIR / "SKILL.md"
OPENAI_YAML_PATH = SKILL_DIR / "agents" / "openai.yaml"
STYLE_REFERENCE_PATH = SKILL_DIR / "references" / "team-style.md"

EXPECTED_STYLE_REFERENCE = """# Team Research Style

CUSTOM-REFERENCE-MARKER: preserve this user-authored file exactly.

Research briefs should:

- lead with the decision or answer,
- separate evidence from interpretation,
- name source gaps plainly,
- keep citations close to the claim they support,
- avoid pretending weak evidence is stronger than it is.
"""

FORBIDDEN_FILLER = [
    "refresh everything",
    "handle appropriately",
    "delete and recreate",
    "rewrite ui metadata from scratch",
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


def _simple_yaml(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def test_skill_metadata_is_trigger_only_and_hyphenated() -> None:
    frontmatter, _body = _frontmatter_and_body()
    description = frontmatter["description"]
    lower_description = description.lower()

    assert set(frontmatter) == {"name", "description"}
    assert frontmatter["name"] == "research-brief"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", frontmatter["name"])
    assert description.startswith("Use when")
    assert len(description) <= 220
    assert "research" in lower_description
    assert "brief" in lower_description
    for workflow_term in ["gather sources", "outline", "write citations", "polish", "refresh every"]:
        assert workflow_term not in lower_description


def test_skill_body_updates_in_place_and_preserves_custom_resources() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert len(body.split()) <= 520
    for heading in ["## overview", "## when to use", "## update workflow", "## brief workflow", "## verification"]:
        assert heading in lower
    for required in [
        "inventory",
        "existing skill folder",
        "preserve",
        "references",
        "assets",
        "scripts",
        "user-authored",
        "only files needed",
    ]:
        assert required in lower
    assert "references/team-style.md" in body
    assert "read" in lower and "team" in lower and "style" in lower
    for phrase in FORBIDDEN_FILLER:
        assert phrase not in lower


def test_openai_yaml_updates_ui_copy_without_dropping_custom_fields() -> None:
    metadata = _simple_yaml(OPENAI_YAML_PATH)
    joined = " ".join(metadata.values()).lower()

    assert set(metadata) == {"display_name", "short_description", "default_prompt", "icon", "brand_color"}
    assert metadata["display_name"] == "Research Brief"
    assert len(metadata["short_description"]) <= 90
    assert len(metadata["default_prompt"]) <= 128
    assert "research" in joined
    assert "brief" in joined
    assert metadata["icon"] == "icons/research-brief.svg"
    assert metadata["brand_color"] == "#335c67"


def test_existing_team_style_reference_is_preserved_exactly() -> None:
    assert STYLE_REFERENCE_PATH.read_text(encoding="utf-8") == EXPECTED_STYLE_REFERENCE


def test_skill_does_not_add_extra_documentation_files() -> None:
    forbidden_names = {"README.md", "QUICK_REFERENCE.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md"}
    present_files = {path.name for path in SKILL_DIR.rglob("*") if path.is_file()}

    assert forbidden_names.isdisjoint(present_files)
