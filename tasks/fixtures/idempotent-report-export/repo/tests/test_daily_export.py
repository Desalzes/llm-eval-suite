from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


def _write_orders(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["order_id", "amount", "status"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _run_export(orders_path: Path, out_dir: Path, report_date: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    src_path = str(Path.cwd() / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "reports.daily_export",
            "--orders",
            str(orders_path),
            "--out",
            str(out_dir),
            "--date",
            report_date,
        ],
        cwd=str(Path.cwd()),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_rerunning_same_export_is_idempotent(tmp_path: Path) -> None:
    orders_path = tmp_path / "orders.csv"
    out_dir = tmp_path / "out"
    _write_orders(
        orders_path,
        [
            {"order_id": "o-1", "amount": 12.50, "status": "paid"},
            {"order_id": "o-2", "amount": 7.25, "status": "refunded"},
            {"order_id": "o-3", "amount": 5.25, "status": "paid"},
        ],
    )

    first = _run_export(orders_path, out_dir, "2026-06-04")
    second = _run_export(orders_path, out_dir, "2026-06-04")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    report_path = out_dir / "daily-report-2026-06-04.md"
    assert report_path.read_text(encoding="utf-8") == "\n".join(
        [
            "# Daily Order Report - 2026-06-04",
            "",
            "orders: 3",
            "gross_revenue: $25.00",
            "status_counts:",
            "- paid: 2",
            "- refunded: 1",
            "",
        ]
    )
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest == {
        "reports": [
            {
                "date": "2026-06-04",
                "path": "daily-report-2026-06-04.md",
                "orders": 3,
                "gross_revenue": 25.0,
            }
        ]
    }


def test_rerun_replaces_same_date_without_dropping_other_dates(tmp_path: Path) -> None:
    orders_path = tmp_path / "orders.csv"
    out_dir = tmp_path / "out"
    _write_orders(orders_path, [{"order_id": "o-1", "amount": 10.00, "status": "paid"}])
    assert _run_export(orders_path, out_dir, "2026-06-03").returncode == 0

    _write_orders(orders_path, [{"order_id": "o-2", "amount": 40.00, "status": "paid"}])
    assert _run_export(orders_path, out_dir, "2026-06-04").returncode == 0

    _write_orders(
        orders_path,
        [
            {"order_id": "o-3", "amount": 8.00, "status": "paid"},
            {"order_id": "o-4", "amount": 2.00, "status": "failed"},
        ],
    )
    assert _run_export(orders_path, out_dir, "2026-06-04").returncode == 0

    report_path = out_dir / "daily-report-2026-06-04.md"
    assert "orders: 2" in report_path.read_text(encoding="utf-8")
    assert "gross_revenue: $10.00" in report_path.read_text(encoding="utf-8")
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["reports"] == [
        {
            "date": "2026-06-03",
            "path": "daily-report-2026-06-03.md",
            "orders": 1,
            "gross_revenue": 10.0,
        },
        {
            "date": "2026-06-04",
            "path": "daily-report-2026-06-04.md",
            "orders": 2,
            "gross_revenue": 10.0,
        },
    ]
