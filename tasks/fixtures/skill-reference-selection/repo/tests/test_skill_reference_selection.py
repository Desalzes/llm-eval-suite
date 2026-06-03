import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "cloud-deploy"
SKILL_PATH = SKILL_DIR / "SKILL.md"
REFERENCE_DIR = SKILL_DIR / "references"

FORBIDDEN_FILLER = [
    "deploy it somehow",
    "handle cloud appropriately",
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
    assert frontmatter["name"] == "cloud-deploy"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", frontmatter["name"])
    assert description.startswith("Use when")
    assert len(description) <= 220
    for workflow_term in ["aws ecs", "gcloud", "az webapp", "cloudwatch", "application insights"]:
        assert workflow_term not in lower_description


def test_skill_body_selects_one_provider_reference_without_embedding_commands() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert len(body.split()) <= 450
    for heading in ["## overview", "## when to use", "## workflow", "## provider references", "## verification"]:
        assert heading in lower
    for required in ["provider", "runtime", "region", "secrets", "rollback", "health"]:
        assert required in lower
    for reference in ["references/aws.md", "references/gcp.md", "references/azure.md"]:
        assert reference in body
    assert "read" in lower and "only" in lower and "relevant" in lower
    for provider_command in ["aws ecs", "gcloud run", "az webapp", "cloudwatch", "application insights"]:
        assert provider_command not in lower
    for phrase in FORBIDDEN_FILLER:
        assert phrase not in lower


def test_provider_references_contain_concrete_provider_guidance() -> None:
    expectations = {
        "aws.md": ["aws ecs", "iam", "cloudwatch", "health check", "rollback"],
        "gcp.md": ["gcloud run", "service account", "cloud logging", "health check", "rollback"],
        "azure.md": ["az webapp", "managed identity", "application insights", "health check", "rollback"],
    }

    for filename, required_terms in expectations.items():
        text = (REFERENCE_DIR / filename).read_text(encoding="utf-8")
        lower = text.lower()
        assert len(text.split()) >= 90
        for term in required_terms:
            assert term in lower


def test_skill_does_not_add_extra_documentation_files() -> None:
    forbidden_docs = {"README.md", "QUICK_REFERENCE.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md"}
    present_files = {path.name for path in SKILL_DIR.rglob("*") if path.is_file()}

    assert forbidden_docs.isdisjoint(present_files)
