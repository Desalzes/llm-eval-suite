from __future__ import annotations

import json
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_flag(
    flag: str,
    user_id: str | None = None,
    cohort: str | None = None,
    config_dir: Path | None = None,
) -> dict:
    root = config_dir or CONFIG_DIR
    defaults = _load_json(root / "defaults.json")
    if flag in defaults:
        return {
            "flag": flag,
            "enabled": bool(defaults[flag]),
            "source": "default",
        }
    return {
        "flag": flag,
        "enabled": False,
        "source": "implicit_default",
    }
