from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _read_orders(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _build_report(orders: list[dict[str, str]], report_date: str) -> str:
    total = sum(float(order["amount"]) for order in orders)
    status_counts: dict[str, int] = {}
    for order in orders:
        status = order["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    lines = [
        f"# Daily Order Report - {report_date}",
        "",
        f"orders: {len(orders)}",
        f"gross_revenue: ${total:.2f}",
        "status_counts:",
    ]
    for status in sorted(status_counts):
        lines.append(f"- {status}: {status_counts[status]}")
    return "\n".join(lines) + "\n"


def export_report(orders_path: Path, out_dir: Path, report_date: str) -> Path:
    orders = _read_orders(orders_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"daily-report-{report_date}.md"
    report_body = _build_report(orders, report_date)

    mode = "a" if report_path.exists() else "w"
    with report_path.open(mode, encoding="utf-8") as fh:
        fh.write(report_body)

    manifest_path = out_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"reports": []}
    manifest["reports"].append(
        {
            "date": report_date,
            "path": report_path.name,
            "orders": len(orders),
            "gross_revenue": round(sum(float(order["amount"]) for order in orders), 2),
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--orders", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args(argv)
    export_report(Path(args.orders), Path(args.out), args.date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
