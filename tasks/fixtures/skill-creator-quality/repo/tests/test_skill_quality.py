import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "skills" / "incident-triage" / "SKILL.md"
FORBIDDEN_PHRASES = [
    "handle appropriately",
    "do the needful",
    "etc.",
]


def _skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def _frontmatter_and_body() -> tuple[dict[str, str], str]:
    text = _skill_text()
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    _, frontmatter_text, body = text.split("---", 2)
    frontmatter = {}
    for line in frontmatter_text.strip().splitlines():
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"')
    return frontmatter, body.strip()


def test_frontmatter_uses_discoverable_skill_metadata() -> None:
    frontmatter, _body = _frontmatter_and_body()

    assert frontmatter["name"] == "incident-triage"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", frontmatter["name"])
    assert frontmatter["description"].startswith("Use when")
    assert len(frontmatter["description"]) <= 220
    assert "gathering info" not in frontmatter["description"].lower()
    assert "mitigating" not in frontmatter["description"].lower()
    assert "handoff" not in frontmatter["description"].lower()


def test_body_contains_reusable_incident_triage_workflow() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    for heading in ["## overview", "## when to use", "## triage workflow", "## verification", "## common mistakes"]:
        assert heading in lower
    for required in ["intake", "reproduce", "severity", "evidence", "mitigation", "handoff"]:
        assert required in lower


def test_body_has_concrete_verification_checks() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert "incident id" in lower
    assert "timeline" in lower
    assert "owner" in lower
    assert "rollback" in lower or "feature flag" in lower
    assert "logs" in lower or "metrics" in lower


def test_body_avoids_vague_filler() -> None:
    text = _skill_text().lower()

    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in text
    assert len(text.split()) <= 650
