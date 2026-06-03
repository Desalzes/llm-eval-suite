import csv
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "csv-normalization"
SKILL_PATH = SKILL_DIR / "SKILL.md"
SCRIPT_PATH = SKILL_DIR / "scripts" / "normalize_csv.py"

FORBIDDEN_FILLER = [
    "handle appropriately",
    "just clean it up",
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

    assert set(frontmatter) == {"name", "description"}
    assert frontmatter["name"] == "csv-normalization"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", frontmatter["name"])
    assert description.startswith("Use when")
    assert len(description) <= 220
    for workflow_term in ["trim", "blank rows", "script", "verification"]:
        assert workflow_term not in description.lower()


def test_skill_body_preserves_script_boundary() -> None:
    _frontmatter, body = _frontmatter_and_body()
    lower = body.lower()

    assert len(body.split()) <= 420
    for heading in ["## overview", "## when to use", "## workflow", "## verification"]:
        assert heading in lower
    assert "scripts/normalize_csv.py" in body
    assert "read" in lower and "only" in lower and "needed" in lower
    assert "python skills/csv-normalization/scripts/normalize_csv.py" in body
    for forbidden in ["rewrite a quick script", "one-off script", "manually edit"]:
        assert forbidden not in lower
    for filler in FORBIDDEN_FILLER:
        assert filler not in lower
    assert body.count("def ") == 0
    assert "import csv" not in body


def test_normalize_csv_script_cli_is_deterministic() -> None:
    scratch_dir = ROOT / ".pytest-tmp" / "script-preservation-cli"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    source = scratch_dir / "messy.csv"
    output = scratch_dir / "clean.csv"
    source.write_text(
        " Customer ID , Signup-Date , Email Address \n"
        " 42 , 2026/05/13 , ADA@EXAMPLE.COM \n"
        "   ,   ,   \n"
        " 43 , 2026/05/14 , alan@example.com \n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--input",
            str(source),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr + completed.stdout
    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {
            "customer_id": "42",
            "signup_date": "2026/05/13",
            "email_address": "ADA@EXAMPLE.COM",
        },
        {
            "customer_id": "43",
            "signup_date": "2026/05/14",
            "email_address": "alan@example.com",
        },
    ]
    source.unlink(missing_ok=True)
    output.unlink(missing_ok=True)


def test_skill_does_not_add_extra_documentation_files() -> None:
    forbidden_docs = {"README.md", "QUICK_REFERENCE.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md"}
    present_files = {path.name for path in SKILL_DIR.rglob("*") if path.is_file()}

    assert forbidden_docs.isdisjoint(present_files)
