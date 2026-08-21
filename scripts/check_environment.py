#!/usr/bin/env python3
"""Перевірка готовності середовища для практичних робіт."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Callable

import duckdb
import polars as pl
import pyarrow as pa

ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
INPUT_DIR = ROOT / "data" / "input"
WORKING_DIR = ROOT / "data" / "working"
RESULTS_DIR = ROOT / "results"

REQUIRED_FILES = (
    "raw_iot_events.jsonl",
    "device_registry.csv",
    "metric_catalog.csv",
    "device_type_metrics.csv",
    "metadata.json",
)

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


def check_versions() -> None:
    print(f"Python:  {sys.version.split()[0]}")
    print(f"Polars:  {pl.__version__}")
    print(f"DuckDB:  {duckdb.__version__}")
    print(f"PyArrow: {pa.__version__}")


def check_directories() -> None:
    for directory in (INPUT_DIR, WORKING_DIR, RESULTS_DIR):
        require(directory.is_dir(), f"каталог не знайдено: {directory}")


def check_required_files() -> None:
    missing = [name for name in REQUIRED_FILES if not (INPUT_DIR / name).is_file()]
    require(not missing, f"відсутні файли: {', '.join(missing)}")
    empty = [name for name in REQUIRED_FILES if (INPUT_DIR / name).stat().st_size == 0]
    require(not empty, f"порожні файли: {', '.join(empty)}")


def check_metadata() -> None:
    metadata = json.loads((INPUT_DIR / "metadata.json").read_text(encoding="utf-8"))
    required_keys = {
        "course",
        "dataset_version",
        "variant_id",
        "group",
        "student_id",
        "student_name",
        "period_start",
        "period_end",
        "timezone",
    }
    missing = sorted(required_keys - metadata.keys())
    require(not missing, f"у metadata.json немає полів: {', '.join(missing)}")
    print(
        "       Варіант:",
        metadata["variant_id"],
        "| Студент:",
        metadata["student_name"],
    )


def check_first_event() -> None:
    with (INPUT_DIR / "raw_iot_events.jsonl").open("r", encoding="utf-8") as file:
        first_line = file.readline()
    require(bool(first_line.strip()), "перший рядок JSONL порожній")
    event = json.loads(first_line)
    required_keys = {"event_id", "event_ts", "device_id", "event_type", "metric", "value"}
    missing = sorted(required_keys - event.keys())
    require(not missing, f"у першій події немає полів: {', '.join(missing)}")


def check_csv_files() -> None:
    registry = pl.read_csv(INPUT_DIR / "device_registry.csv")
    catalog = pl.read_csv(INPUT_DIR / "metric_catalog.csv")
    mapping = pl.read_csv(INPUT_DIR / "device_type_metrics.csv")
    require(registry.height > 0, "device_registry.csv не містить записів")
    require(catalog.height > 0, "metric_catalog.csv не містить записів")
    require(mapping.height > 0, "device_type_metrics.csv не містить записів")
    print(
        f"       Пристроїв: {registry.height} | "
        f"Метрик: {catalog.height} | "
        f"Пар тип-метрика: {mapping.height}"
    )


def check_write_access(directory: Path, filename: str) -> None:
    test_file = directory / filename
    test_file.write_text("environment test\n", encoding="utf-8")
    require(test_file.read_text(encoding="utf-8") == "environment test\n", "помилка читання")
    test_file.unlink()


def check_input_is_read_only() -> None:
    test_file = INPUT_DIR / ".write_test"
    try:
        test_file.write_text("must fail", encoding="utf-8")
    except OSError:
        return
    else:
        test_file.unlink(missing_ok=True)
        raise RuntimeError("каталог data/input доступний для запису")


def main() -> int:
    print("=== Перевірка робочого середовища ===")
    check("версії Python-бібліотек", check_versions)
    check("структура каталогів", check_directories)
    check("наявність п'яти вхідних файлів", check_required_files)
    check("структура metadata.json", check_metadata)
    check("читання першої JSONL-події", check_first_event)
    check("читання CSV-довідників через Polars", check_csv_files)
    check("data/input змонтовано лише для читання", check_input_is_read_only)
    check(
        "data/working доступний для запису",
        lambda: check_write_access(WORKING_DIR, ".environment_test"),
    )
    check(
        "results доступний для запису",
        lambda: check_write_access(RESULTS_DIR, ".environment_test"),
    )

    if failures:
        print(f"\nСередовище не готове. Невдалих перевірок: {len(failures)}")
        return 1

    print("\nСередовище готове до роботи.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
