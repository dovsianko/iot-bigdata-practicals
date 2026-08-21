#!/usr/bin/env python3
"""Базова перевірка результатів практичної роботи №5."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Callable

import polars as pl

ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
RESULTS_DIR = ROOT / "results" / "practical_05"

REQUIRED_OUTPUTS = (
    "incident_mart.csv",
    "device_risk_summary.csv",
    "scenario_risk_summary.csv",
    "location_risk_summary.csv",
    "top_incidents.csv",
    "practical_05_summary.json",
    "findings_by_scenario.png",
    "severity_distribution.png",
    "top_risky_devices.png",
    "risk_by_location.png",
)

INCIDENT_MART_COLUMNS = {
    "finding_id",
    "scenario_type",
    "device_id",
    "device_type",
    "location",
    "start_ts",
    "end_ts",
    "metric",
    "score",
    "severity",
    "severity_weight",
    "risk_score",
    "priority",
    "evidence",
}

failures: list[str] = []


def check(message: str, action: Callable[[], None]) -> None:
    try:
        action()
    except Exception as exc:  # noqa: BLE001 - діагностичний скрипт
        failures.append(f"{message}: {exc}")
        print(f"[FAIL] {message}: {exc}")
    else:
        print(f"[ OK ] {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def check_output_files() -> None:
    require(RESULTS_DIR.is_dir(), f"каталог не знайдено: {RESULTS_DIR}")
    missing = [name for name in REQUIRED_OUTPUTS if not (RESULTS_DIR / name).is_file()]
    require(not missing, f"відсутні файли: {', '.join(missing)}")
    empty = [name for name in REQUIRED_OUTPUTS if (RESULTS_DIR / name).stat().st_size == 0]
    require(not empty, f"порожні файли: {', '.join(empty)}")


def check_incident_mart() -> None:
    mart = pl.read_csv(RESULTS_DIR / "incident_mart.csv")
    require(mart.height > 0, "incident_mart.csv не містить рядків")
    missing_columns = sorted(INCIDENT_MART_COLUMNS - set(mart.columns))
    require(not missing_columns, f"немає колонок: {', '.join(missing_columns)}")
    require(
        mart.select(pl.col("risk_score").is_not_null().all()).item(),
        "risk_score містить порожні значення",
    )
    require(
        mart.select((pl.col("risk_score") >= 0).all()).item(),
        "risk_score містить від'ємні значення",
    )


def check_summary() -> None:
    summary = json.loads((RESULTS_DIR / "practical_05_summary.json").read_text(encoding="utf-8"))
    required_keys = {
        "variant_id",
        "student_id",
        "student_name",
        "incident_mart_rows",
        "device_risk_rows",
        "scenario_risk_rows",
        "location_risk_rows",
        "top_incidents_rows",
        "total_risk_score",
    }
    missing_keys = sorted(required_keys - summary.keys())
    require(not missing_keys, f"у summary немає полів: {', '.join(missing_keys)}")
    require(int(summary["incident_mart_rows"]) > 0, "incident_mart_rows має бути більше 0")


def main() -> int:
    print("=== Перевірка результатів практичної роботи №5 ===")
    check("наявність очікуваних файлів", check_output_files)
    check("структура incident_mart.csv", check_incident_mart)
    check("структура practical_05_summary.json", check_summary)

    if failures:
        print(f"\nПеревірка ПР5 не пройдена. Невдалих перевірок: {len(failures)}")
        return 1

    print("\nПеревірка ПР5 пройдена.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
