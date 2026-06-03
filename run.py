#!/usr/bin/env python3
"""llm-eval-suite reference scorer (Python standard library only).

A *scorer*, not a driver: your AI agent solves a task in a workspace, then this
tool grades the result. No API keys, no agent invocation.

Verbs:
  prepare   <task.json>                         copy the task's repo/ into a fresh workspace
  score     <task.json> --workspace <dir>       grade a solved workspace -> run-result.json
  score-set <eval-set.json> [--runs-dir runs]   aggregate per-task results -> eval-summary.json
  validate  <task.json>                         check a candidate task abides by the template
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

IGNORED_NAMES = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".venv", "venv", "dist", "build", ".DS_Store",
}
TEST_TIMEOUT_SECONDS = 600


def load_json(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_repo_dir(task_path: Path, task: dict) -> Path:
    repo = Path(task["repo"])
    return repo if repo.is_absolute() else (Path(task_path).parent / repo).resolve()


def _iter_files(root: Path):
    root = Path(root)
    for p in root.rglob("*"):
        if p.is_dir():
            continue
        if set(p.relative_to(root).parts) & IGNORED_NAMES:
            continue
        yield p


def hash_tree(root: Path) -> dict:
    out = {}
    root = Path(root)
    for p in _iter_files(root):
        out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def changed_files(pristine: Path, workspace: Path) -> list:
    a = hash_tree(pristine)
    b = hash_tree(workspace)
    changed = {rel for rel, h in b.items() if a.get(rel) != h}
    changed |= {rel for rel in a if rel not in b}  # deletions
    return sorted(changed)


def is_allowed(rel: str, allowed_paths: list) -> bool:
    for pat in allowed_paths:
        pat = pat.replace("\\", "/")
        if rel == pat or fnmatch.fnmatch(rel, pat):
            return True
        if fnmatch.fnmatch(rel, pat.rstrip("/") + "/*"):  # bare dir / "dir/**" covers contents
            return True
    return False


def run_test_command(cmd: list, cwd: Path) -> tuple:
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=TEST_TIMEOUT_SECONDS,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT after {TEST_TIMEOUT_SECONDS}s"
    except FileNotFoundError as exc:
        return 127, f"command not found: {cmd[0]} ({exc})"


def compute_status(tests_passed: bool, forbidden: list) -> str:
    if forbidden:
        return "unsafe"
    return "passed" if tests_passed else "failed"


def cmd_score(args) -> int:
    task_path = Path(args.task).resolve()
    task = load_json(task_path)
    pristine = resolve_repo_dir(task_path, task)
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"ERROR: workspace not found: {workspace}", file=sys.stderr)
        return 2
    exit_code, output = run_test_command(task["test_command"], workspace)
    tests_passed = exit_code == 0
    changed = changed_files(pristine, workspace)
    forbidden = [f for f in changed if not is_allowed(f, task["allowed_paths"])]
    status = compute_status(tests_passed, forbidden)
    run_id = workspace.parent.name or new_run_id()
    result = {
        "run_id": run_id,
        "task_id": task["id"],
        "profile_id": "byo",
        "status": status,
        "tests_passed": tests_passed,
        "changed_files": changed,
        "forbidden_changed_files": forbidden,
        "test_exit_code": exit_code,
        "test_output": output[-10000:],
    }
    out_path = workspace.parent / "run-result.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(status.upper())
    print(f"  tests_passed: {tests_passed} (exit {exit_code})")
    print(f"  changed_files: {changed}")
    if forbidden:
        print(f"  FORBIDDEN (outside allowed_paths): {forbidden}")
    print(f"  wrote {out_path}")
    return 0


def cmd_prepare(args) -> int:
    task_path = Path(args.task).resolve()
    task = load_json(task_path)
    repo = resolve_repo_dir(task_path, task)
    if not repo.is_dir():
        print(f"ERROR: repo dir not found: {repo}", file=sys.stderr)
        return 2
    run_id = new_run_id()
    workspace = Path("runs") / run_id / "workspace"
    workspace.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo, workspace, ignore=shutil.ignore_patterns(*IGNORED_NAMES))
    print(f"Task:        {task['id']} - {task['title']}")
    print(f"Brief:       {task['description']}")
    print(f"Allowed:     {task['allowed_paths']}")
    print("Success criteria:")
    for c in task["success_criteria"]:
        print(f"  - {c}")
    print()
    print(f"Workspace ready: {workspace.as_posix()}")
    print("Solve the task in that folder (only edit allowed paths), then run:")
    print(f"  python run.py score {args.task} --workspace {workspace.as_posix()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="run.py", description="llm-eval-suite reference scorer (scorer-only)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("prepare", help="copy a task's repo/ into a fresh workspace")
    sp.add_argument("task")
    sp.set_defaults(func=cmd_prepare)

    ss = sub.add_parser("score", help="grade a solved workspace")
    ss.add_argument("task")
    ss.add_argument("--workspace", required=True)
    ss.set_defaults(func=cmd_score)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
