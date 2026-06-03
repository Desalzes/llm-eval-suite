import argparse
import json
from pathlib import Path


DEFAULTS = {
    "display_name": "Meeting Summary",
    "short_description": "Turn meeting notes into structured decisions and follow-ups.",
    "default_prompt": "Summarize these meeting notes into decisions, action items, and open questions.",
}


def _yaml_line(key: str, value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'{key}: "{escaped}"'


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate UI metadata for a scaffolded skill.")
    parser.add_argument("skill_path")
    parser.add_argument("--display-name", default=DEFAULTS["display_name"])
    parser.add_argument("--short-description", default=DEFAULTS["short_description"])
    parser.add_argument("--default-prompt", default=DEFAULTS["default_prompt"])
    args = parser.parse_args()

    skill_dir = Path(args.skill_path)
    agents_dir = skill_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    values = {
        "display_name": args.display_name,
        "short_description": args.short_description,
        "default_prompt": args.default_prompt,
    }
    (agents_dir / "openai.yaml").write_text(
        "\n".join(_yaml_line(key, value) for key, value in values.items()) + "\n",
        encoding="utf-8",
    )
    marker_skill_path = skill_dir
    try:
        marker_skill_path = skill_dir.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        pass

    (agents_dir / ".openai_yaml_generated.json").write_text(
        json.dumps(
            {
                "script": "scripts/generate_openai_yaml.py",
                "skill_path": str(marker_skill_path).replace("\\", "/"),
                "fields": list(values),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
