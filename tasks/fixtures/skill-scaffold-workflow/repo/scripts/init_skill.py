import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a local Codex skill scaffold.")
    parser.add_argument("skill_name")
    parser.add_argument("--path", required=True, help="Directory where the skill folder should be created.")
    args = parser.parse_args()

    skill_name = args.skill_name
    skill_dir = Path(args.path) / skill_name
    agents_dir = skill_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    skill_path = skill_dir / "SKILL.md"
    if not skill_path.exists():
        skill_path.write_text(
            "---\n"
            f"name: {skill_name}\n"
            "description: Use when TODO trigger conditions.\n"
            "---\n\n"
            f"# {skill_name}\n\n"
            "TODO: Replace this scaffold with concise skill instructions.\n",
            encoding="utf-8",
        )

    (skill_dir / ".init_skill.json").write_text(
        json.dumps(
            {
                "script": "scripts/init_skill.py",
                "skill_name": skill_name,
                "output_path": f"skills/{skill_name}",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
