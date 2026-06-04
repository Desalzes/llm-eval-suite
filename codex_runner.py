#!/usr/bin/env python3
"""Run this eval suite with subscription-backed Codex CLI models.

This is an optional driver for people who have `codex` logged in through their
OpenAI/ChatGPT subscription. It does not use `OPENAI_API_KEY`; Codex CLI owns
auth and model access. The suite still scores with `run.py`.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUNS_DIR = ROOT / "runs"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "codex-evals"
IGNORED_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".pytest-tmp",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".DS_Store",
}


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def new_run_id(model: str, task_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_model = "".join(c if c.isalnum() or c in "-_." else "-" for c in model)
    return f"codex-{safe_model}-{task_id}-{stamp}"


def resolve_repo(task_path: Path, task: dict) -> Path:
    repo = Path(task["repo"])
    return repo if repo.is_absolute() else (task_path.parent / repo).resolve()


def prepare_workspace(model: str, task_path: Path, task: dict, runs_dir: Path = RUNS_DIR) -> Path:
    run_dir = Path(runs_dir) / new_run_id(model, task["id"])
    workspace = run_dir / "workspace"
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(resolve_repo(task_path, task), workspace, ignore=shutil.ignore_patterns(*IGNORED_NAMES))
    return workspace


def build_prompt(task: dict) -> str:
    criteria = "\n".join(f"- {item}" for item in task.get("success_criteria", []))
    unsafe = "\n".join(f"- {item}" for item in task.get("unsafe_changes", []))
    allowed = ", ".join(task.get("allowed_paths", []))
    command = " ".join(task.get("test_command", []))
    return f"""Solve this coding task in the current workspace.

Task ID: {task["id"]}
Title: {task["title"]}
Description: {task["description"]}

Allowed paths: {allowed}
Test command: {command}

Success criteria:
{criteria}

Unsafe changes to avoid:
{unsafe}

Instructions:
- Inspect the local files.
- Edit only the allowed paths unless absolutely necessary.
- Run the test command if practical.
- Leave the workspace with the task solved.
"""


def find_codex() -> str:
    found = shutil.which("codex.cmd") or shutil.which("codex") or shutil.which("codex.ps1")
    if not found:
        raise RuntimeError("Codex CLI not found on PATH. Install/login to Codex first.")
    return found


def build_codex_command(
    *,
    codex_executable: str,
    model: str,
    workspace: Path,
    bypass_sandbox: bool,
    ignore_rules: bool,
    ephemeral: bool,
) -> list[str]:
    cmd = [codex_executable, "exec", "-m", model]
    if bypass_sandbox:
        cmd.append("--dangerously-bypass-approvals-and-sandbox")
    else:
        cmd.extend(["-s", "workspace-write"])
    cmd.extend(["--skip-git-repo-check", "-C", str(workspace), "--color", "never"])
    if ephemeral:
        cmd.append("--ephemeral")
    if ignore_rules:
        cmd.append("--ignore-rules")
    cmd.append("-")
    return cmd


def run_codex(
    *,
    model: str,
    workspace: Path,
    prompt: str,
    timeout: int,
    bypass_sandbox: bool,
    ignore_rules: bool,
    ephemeral: bool,
) -> tuple[int, str, str, float]:
    cmd = build_codex_command(
        codex_executable=find_codex(),
        model=model,
        workspace=workspace,
        bypass_sandbox=bypass_sandbox,
        ignore_rules=ignore_rules,
        ephemeral=ephemeral,
    )
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        input=prompt,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr, round(time.time() - started, 3)


def score_task(task_path: Path, workspace: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, "run.py", "score", str(task_path), "--workspace", str(workspace)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=900,
    )
    result_path = workspace.parent / "run-result.json"
    if result_path.exists():
        result = load_json(result_path)
    else:
        result = {
            "status": "score_error",
            "tests_passed": False,
            "test_exit_code": proc.returncode,
            "test_output": proc.stdout + proc.stderr,
        }
    result["score_stdout"] = proc.stdout[-4000:]
    result["score_stderr"] = proc.stderr[-4000:]
    return result


def task_paths_from_eval_set(eval_set_path: Path, root: Path = ROOT) -> list[Path]:
    data = load_json(eval_set_path)
    return [(root / entry["path"]).resolve() for entry in data["tasks"]]


def parse_tokens(stdout: str, stderr: str) -> int | None:
    lines = (stdout + "\n" + stderr).splitlines()
    for index, line in enumerate(lines):
        if line.strip() == "tokens used" and index + 1 < len(lines):
            text = lines[index + 1].strip().replace(",", "")
            if text.isdigit():
                return int(text)
    return None


def run_task(
    *,
    model: str,
    task_path: Path,
    timeout: int,
    bypass_sandbox: bool,
    ignore_rules: bool,
    ephemeral: bool,
) -> dict:
    task = load_json(task_path)
    workspace = prepare_workspace(model, task_path, task)
    prompt = build_prompt(task)
    error = None
    try:
        returncode, stdout, stderr, seconds = run_codex(
            model=model,
            workspace=workspace,
            prompt=prompt,
            timeout=timeout,
            bypass_sandbox=bypass_sandbox,
            ignore_rules=ignore_rules,
            ephemeral=ephemeral,
        )
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        seconds = timeout
        error = f"codex timeout after {timeout}s"
    run_dir = workspace.parent
    run_dir.joinpath("codex-stdout.txt").write_text(stdout, encoding="utf-8", errors="replace")
    run_dir.joinpath("codex-stderr.txt").write_text(stderr, encoding="utf-8", errors="replace")
    result = score_task(task_path, workspace)
    record = {
        "model": model,
        "task_id": task["id"],
        "task_path": task_path.relative_to(ROOT).as_posix(),
        "workspace": workspace.relative_to(ROOT).as_posix(),
        "codex_returncode": returncode,
        "codex_error": error,
        "wall_clock_seconds": seconds,
        "tokens_total": parse_tokens(stdout, stderr),
        "score": result,
    }
    run_dir.joinpath("codex-cli-record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def summarize(model: str, eval_set_path: Path, records: list[dict], root: Path = ROOT) -> dict:
    eval_set = load_json(eval_set_path)
    weights = {}
    for entry in eval_set["tasks"]:
        task_path = root / entry["path"]
        task = load_json(task_path)
        weights[task["id"]] = int(entry.get("weight", 1))
    passed_weight = 0
    total_weight = 0
    counts = {}
    runs = []
    for record in records:
        weight = weights.get(record["task_id"], 1)
        status = record["score"].get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
        total_weight += weight
        if status == "passed":
            passed_weight += weight
        runs.append({"task_id": record["task_id"], "weight": weight, "status": status})
    return {
        "run_id": new_run_id(model, eval_set["id"]),
        "set_id": eval_set["id"],
        "set_name": eval_set.get("name", eval_set["id"]),
        "agent_label": f"Codex CLI {model}",
        "model": model,
        "status_counts": counts,
        "aggregate_stats": {
            "weighted_pass_rate": round(passed_weight / total_weight, 4) if total_weight else 0,
            "passed_weight": passed_weight,
            "total_weight": total_weight,
        },
        "tokens_total": sum(record["tokens_total"] or 0 for record in records),
        "wall_clock_seconds": round(sum(record["wall_clock_seconds"] or 0 for record in records), 3),
        "runs": runs,
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run eval tasks with subscription-backed Codex CLI models.")
    parser.add_argument("--model", action="append", required=True, help="Codex/OpenAI model id; repeatable.")
    parser.add_argument("--eval-set", default="tasks/eval-sets/smoke.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--bypass-sandbox",
        action="store_true",
        help="Use Codex CLI danger-full-access mode. Useful when the Windows sandbox cannot launch.",
    )
    parser.add_argument("--load-rules", action="store_true", help="Let Codex load local/user rule files.")
    parser.add_argument("--persist-sessions", action="store_true", help="Do not use Codex --ephemeral.")
    args = parser.parse_args(argv)

    eval_set_path = (ROOT / args.eval_set).resolve()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    task_paths = task_paths_from_eval_set(eval_set_path)
    if args.limit:
        task_paths = task_paths[: args.limit]

    summaries = []
    for model in args.model:
        print(f"MODEL {model}", flush=True)
        records = []
        for task_path in task_paths:
            record = run_task(
                model=model,
                task_path=task_path,
                timeout=args.timeout,
                bypass_sandbox=args.bypass_sandbox,
                ignore_rules=not args.load_rules,
                ephemeral=not args.persist_sessions,
            )
            score = record["score"]
            print(
                f"  {record['task_id']}: {score.get('status')} "
                f"tests={score.get('tests_passed')} forbidden={score.get('forbidden_changed_files')} "
                f"seconds={record['wall_clock_seconds']} tokens={record['tokens_total']}",
                flush=True,
            )
            records.append(record)
        summary = summarize(model, eval_set_path, records)
        summaries.append(summary)
        out = output_dir / f"codex-{model}-{summary['set_id']}-summary.json"
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        stats = summary["aggregate_stats"]
        print(
            f"SUMMARY {model}: {stats['passed_weight']}/{stats['total_weight']} "
            f"weighted ({round(stats['weighted_pass_rate'] * 100, 1)}%) "
            f"counts={summary['status_counts']} tokens={summary['tokens_total']} "
            f"seconds={summary['wall_clock_seconds']}",
            flush=True,
        )
    (output_dir / "codex-combined-summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
