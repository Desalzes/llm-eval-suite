import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "meeting-summary"
SKILL_PATH = SKILL_DIR / "SKILL.md"
OPENAI_YAML_PATH = SKILL_DIR / "agents" / "openai.yaml"
INIT_MARKER_PATH = SKILL_DIR / ".init_skill.json"
YAML_MARKER_PATH = SKILL_DIR / "agents" / ".openai_yaml_generated.json"

FORBIDDEN_SCOPE = [
    "calendar scheduling",
    "crm",
    "project management automation",
    "transcription service",
]
FORBIDDEN_FILLER = [
    "summarize appropriately",
    "handle the meeting",
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


def test_skill_was_created_with_local_init_helper() -> None:
    marker = json.loads(INIT_MARKER_PATH.read_text(encoding="utf-8"))

    assert marker == {
        "script": "scripts/init_skill.py",
        "skill_name": "meeting-summary",
        "output_path": "skills/meeting-summary",
    }
    assert SKILL_PATH.exists()
    assert OPENAI_YAML_PATH.exists()


def test_openai_yaml_was_generated_with_metadata_helper() -> None:
    marker = json.loads(YAML_MARKER_PATH.read_text(encoding="utf-8"))
    metadata = _simple_yaml(OPENAI_YAML_PATH)
    joined = " ".join(metadata.values()).lower()

    assert marker == {
        "script": "scripts/generate_openai_yaml.py",
        "skill_path": "skills/meeting-summary",
        "fields": ["display_name", "short_description", "default_prompt"],
    }
    assert set(metadata) == {"display_name", "short_description", "default_prompt"}
    assert metadata["display_name"] == "Meeting Summary"
    assert len(metadata["short_description"]) <= 90
    assert len(metadata["default_prompt"]) <= 128
    assert "meeting" in joined
    assert "summary" in joined or "summarize" in joined
    for forbidden in FORBIDDEN_SCOPE:
        assert forbidden not in joined


def test_skill_metadata_is_trigger_only_and_hyphenated() -> None:
    frontmatter, _body = _frontmatter_and_body()
    description = frontmatter["description"]
    lower_description = description.lower()

    assert set(frontmatter) == {"name", "description"}
    assert frontmatter["name"] == "meeting-summary"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", frontmatter["name"])
    assert description.startswith("Use when")
    assert len(description) <= 220
    assert "meeting" in lower_description
    assert any(term in lower_description for term in ["transcript", "call notes", "recording", "rough notes"])
    for workflow_term in ["action items", "owners", "due dates", "verification"]:
        assert workflow_term not in lower_description


def test_skill_body_is_concise_and_covers_summary_workflow() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert len(body.split()) <= 420
    for heading in ["## overview", "## workflow", "## output", "## verification"]:
        assert heading in lower
    for required in [
        "attendees",
        "decisions",
        "action items",
        "owners",
        "due dates",
        "open questions",
        "source gaps",
    ]:
        assert required in lower
    for forbidden in FORBIDDEN_SCOPE:
        assert forbidden not in lower
    for filler in FORBIDDEN_FILLER:
        assert filler not in lower


def test_skill_does_not_add_extra_resource_or_documentation_files() -> None:
    forbidden_names = {"README.md", "QUICK_REFERENCE.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md"}
    forbidden_dirs = {"references", "assets", "scripts"}
    present_files = {path.name for path in SKILL_DIR.rglob("*") if path.is_file()}
    present_dirs = {path.name for path in SKILL_DIR.rglob("*") if path.is_dir()}

    assert forbidden_names.isdisjoint(present_files)
    assert forbidden_dirs.isdisjoint(present_dirs)
