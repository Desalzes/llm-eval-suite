import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "data-export"
SKILL_PATH = SKILL_DIR / "SKILL.md"
OPENAI_YAML_PATH = SKILL_DIR / "agents" / "openai.yaml"
REFERENCE_PATH = SKILL_DIR / "references" / "export-checklist.md"

FORBIDDEN_SCOPE = [
    "dashboard",
    "bi",
    "warehouse",
    "migration",
    "notebook",
    "modeling",
    "charts",
]
FORBIDDEN_FILLER = [
    "handle data appropriately",
    "do the export correctly",
    "etc.",
    "anything involving data",
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


def test_skill_frontmatter_is_narrow_and_triggerable() -> None:
    frontmatter, _body = _frontmatter_and_body()
    description = frontmatter["description"]
    lower_description = description.lower()

    assert set(frontmatter) == {"name", "description"}
    assert frontmatter["name"] == "data-export"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", frontmatter["name"])
    assert description.startswith("Use when")
    assert len(description) <= 220
    assert "export" in lower_description
    assert "csv" in lower_description or "parquet" in lower_description
    for forbidden in FORBIDDEN_SCOPE:
        assert forbidden not in lower_description


def test_skill_body_is_concise_and_uses_progressive_disclosure() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert len(body.split()) <= 420
    for heading in ["## overview", "## workflow", "## progressive disclosure", "## verification"]:
        assert heading in lower
    for required in ["format", "destination", "schema", "filters", "row count", "privacy"]:
        assert required in lower
    assert "references/export-checklist.md" in body
    assert "read" in lower and "only" in lower and "needed" in lower
    for forbidden in FORBIDDEN_SCOPE:
        assert forbidden not in lower
    for filler in FORBIDDEN_FILLER:
        assert filler not in lower


def test_export_reference_contains_detailed_validation_without_extra_docs() -> None:
    reference = REFERENCE_PATH.read_text(encoding="utf-8")
    lower = reference.lower()

    assert len(reference.split()) >= 140
    for required in [
        "csv",
        "parquet",
        "schema",
        "row count",
        "privacy",
        "pii",
        "delimiter",
        "encoding",
        "checksum",
        "preview",
    ]:
        assert required in lower

    forbidden_docs = {"README.md", "QUICK_REFERENCE.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md"}
    present_files = {path.name for path in SKILL_DIR.rglob("*") if path.is_file()}
    assert forbidden_docs.isdisjoint(present_files)


def test_openai_yaml_matches_narrow_skill_metadata() -> None:
    metadata = _simple_yaml(OPENAI_YAML_PATH)
    joined = " ".join(metadata.values()).lower()

    assert set(metadata) == {"display_name", "short_description", "default_prompt"}
    assert metadata["display_name"] == "Data Export"
    assert len(metadata["short_description"]) <= 90
    assert len(metadata["default_prompt"]) <= 128
    assert "export" in joined
    assert "csv" in joined or "parquet" in joined
    for forbidden in FORBIDDEN_SCOPE:
        assert forbidden not in joined
