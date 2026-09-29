"""Shared experiment-report persistence helpers."""

import csv
import json
from pathlib import Path
from typing import Any


def write_json_with_tables(
    report: dict[str, Any], output: Path, tables: dict[str, list[dict[str, Any]]],
) -> None:
    """Write one JSON report and any number of named CSV tables."""
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    for filename, rows in tables.items():
        if not rows:
            continue
        with (output / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


def write_domain_report(report: dict[str, Any], output: Path) -> None:
    """Write experiment 0's domain metrics using the shared persistence layer."""
    metrics = report.get("metrics", [])
    if not metrics:
        raise ValueError("report must contain at least one metrics row")
    write_json_with_tables(report, output, {"domain_metrics.csv": metrics})
