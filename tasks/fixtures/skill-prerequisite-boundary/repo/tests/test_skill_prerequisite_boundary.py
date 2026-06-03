import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "crm-sync"
SKILL_PATH = SKILL_DIR / "SKILL.md"

FORBIDDEN_CLAIMS = [
    "logs into",
    "sync everything",
    "fix conflicts however seems best",
    "handle errors appropriately",
    "do the needful",
    "etc.",
]

FORBIDDEN_SECRET_HANDLING = [
    "put the api token",
    "store the api",
    "hard-code",
    "hardcode",
    "create a token",
    "use a password",
    "bypass access",
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
    assert frontmatter["name"] == "crm-sync"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", frontmatter["name"])
    assert description.startswith("Use when")
    assert len(description) <= 220
    assert "crm" in lower_description
    for workflow_term in ["logs into", "deduplicates", "writes updates", "automatically", "sync problems"]:
        assert workflow_term not in lower_description


def test_skill_body_states_prerequisites_before_sync_work() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert len(body.split()) <= 520
    for heading in ["## overview", "## prerequisites", "## workflow", "## missing access", "## verification"]:
        assert heading in lower
    for required in [
        "source system",
        "destination system",
        "connected app",
        "credentials",
        "workspace",
        "record types",
        "field scope",
    ]:
        assert required in lower


def test_skill_uses_read_only_discovery_and_confirmation_before_writes() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert "read-only" in lower
    assert "map fields" in lower or "field mapping" in lower
    assert "dry-run" in lower or "preview" in lower
    assert "confirm" in lower or "confirmation" in lower
    assert "before updating" in lower or "before write" in lower or "before writing" in lower
    assert "backup" in lower or "rollback" in lower


def test_skill_has_missing_access_fallback_without_inventing_data_or_secrets() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert "ask" in lower or "request" in lower
    assert "export" in lower or "sample rows" in lower or "sample file" in lower
    assert "manual checklist" in lower or "manual plan" in lower
    assert "do not invent" in lower or "must not invent" in lower
    assert "credentials" in lower and "records" in lower
    for phrase in FORBIDDEN_CLAIMS + FORBIDDEN_SECRET_HANDLING:
        assert phrase not in lower


def test_skill_does_not_add_extra_documentation_files() -> None:
    forbidden_docs = {"README.md", "QUICK_REFERENCE.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md"}
    present_files = {path.name for path in SKILL_DIR.rglob("*") if path.is_file()}

    assert forbidden_docs.isdisjoint(present_files)
