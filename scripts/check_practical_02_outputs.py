#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import json
import sys

import polars as pl


ROOT = Path("/workspace") if Path("/workspace").exists() else Path.cwd()
if not (ROOT / "data" / "input").exists() and (ROOT.parent / "data" / "input").exists():
    ROOT = ROOT.parent

INPUT_DIR = ROOT / "data" / "input"
RESULTS_DIR = ROOT / "results" / "practical_02"

RAW_EVENTS_PATH = INPUT_DIR / "raw_iot_events.jsonl"
METADATA_PATH = INPUT_DIR / "metadata.json"

required = {
    "clean": RESULTS_DIR / "clean_iot_events.parquet",
    "issues": RESULTS_DIR / "data_quality_issues.csv",
    "rejected": RESULTS_DIR / "rejected_iot_events.jsonl",
    "summary": RESULTS_DIR / "cleaning_summary.json",
}

CLEAN_COLUMNS = [
    "event_id",
    "event_ts",
    "device_id",
    "event_type",
    "metric",
    "value",
]

ISSUES_COLUMNS = [
    "event_id",
    "issue_type",
    "issue_detail",
    "action",
]

REJECTED_REQUIRED_FIELDS = {
    "event_id",
    "issue_type",
    "issue_detail",
    "action",
    "raw_record",
}

SUMMARY_REQUIRED_KEYS = {
    "variant_id",
    "student_id",
    "student_name",
    "input_records",
    "clean_records",
    "unchanged_records",
    "repaired_records",
    "rejected_records",
    "removed_duplicate_records",
    "issues_by_type",
    "issues_by_detail",
    "actions_by_type",
}

ALLOWED_ISSUE_TYPES = {
    "duplicate_event_id",
    "missing_required_field",
    "invalid_timestamp",
    "unknown_device_id",
    "invalid_event_type",
    "unknown_metric",
    "invalid_metric_for_device_type",
    "out_of_range_value",
}

ALLOWED_ISSUE_ACTIONS = {
    "rejected",
    "repaired",
    "removed_duplicate",
}

errors = []

for name, path in required.items():
    if not path.is_file():
        errors.append(f"missing {name}: {path}")

for path in (RAW_EVENTS_PATH, METADATA_PATH):
    if not path.is_file():
        errors.append(f"missing input file: {path}")

clean = None
issues = None
summary = None
metadata = None
rejected_rows = []

if not errors:
    try:
        clean = pl.read_parquet(required["clean"])
    except Exception as exc:  # noqa: BLE001
        errors.append(f"cannot read clean parquet: {exc}")

    try:
        issues = pl.read_csv(required["issues"])
    except Exception as exc:  # noqa: BLE001
        errors.append(f"cannot read issues csv: {exc}")

    try:
        with required["summary"].open("r", encoding="utf-8") as f:
            summary = json.load(f)
        if not isinstance(summary, dict):
            errors.append("cleaning_summary.json must contain one JSON object")
            summary = None
    except Exception as exc:  # noqa: BLE001
        errors.append(f"cannot read cleaning summary: {exc}")

    try:
        with METADATA_PATH.open("r", encoding="utf-8") as f:
            metadata = json.load(f)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"cannot read metadata.json: {exc}")

    try:
        with required["rejected"].open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                if not line.strip():
                    continue

                row = json.loads(line)
                if not isinstance(row, dict):
                    errors.append(
                        f"rejected jsonl line {line_no}: expected JSON object"
                    )
                    continue

                missing = REJECTED_REQUIRED_FIELDS - set(row)
                if missing:
                    errors.append(
                        f"rejected jsonl line {line_no}: missing fields {sorted(missing)}"
                    )

                action = row.get("action")
                if action not in {"rejected", "removed_duplicate"}:
                    errors.append(
                        f"rejected jsonl line {line_no}: invalid action={action!r}"
                    )

                if "raw_record" in row and not isinstance(row["raw_record"], dict):
                    errors.append(
                        f"rejected jsonl line {line_no}: raw_record must be an object"
                    )

                rejected_rows.append(row)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"cannot read rejected jsonl: {exc}")


if clean is not None:
    if clean.columns != CLEAN_COLUMNS:
        errors.append(
            "clean parquet columns must be exactly: "
            + ", ".join(CLEAN_COLUMNS)
        )

    if "event_id" in clean.columns and clean["event_id"].n_unique() != clean.height:
        errors.append("duplicate event_id in clean parquet")

    if "event_ts" in clean.columns and not clean.schema["event_ts"].is_temporal():
        errors.append(
            f"event_ts must have temporal dtype, got {clean.schema['event_ts']}"
        )


if issues is not None:
    if issues.columns != ISSUES_COLUMNS:
        errors.append(
            "issues csv columns must be exactly: "
            + ", ".join(ISSUES_COLUMNS)
        )

    if set(ISSUES_COLUMNS) <= set(issues.columns):
        issue_types = set(
            issues["issue_type"].drop_nulls().cast(pl.Utf8).to_list()
        )
        unknown_issue_types = sorted(issue_types - ALLOWED_ISSUE_TYPES)
        if unknown_issue_types:
            errors.append(
                f"unknown issue_type values: {unknown_issue_types}"
            )

        actions = set(
            issues["action"].drop_nulls().cast(pl.Utf8).to_list()
        )
        unknown_actions = sorted(actions - ALLOWED_ISSUE_ACTIONS)
        if unknown_actions:
            errors.append(
                f"unknown issue action values: {unknown_actions}"
            )

        null_required = issues.filter(
            pl.any_horizontal(
                [pl.col(column).is_null() for column in ISSUES_COLUMNS]
            )
        ).height
        if null_required:
            errors.append(
                f"issues csv has {null_required} rows with null required fields"
            )


if summary is not None:
    missing_keys = SUMMARY_REQUIRED_KEYS - set(summary)
    if missing_keys:
        errors.append(
            f"summary missing keys: {sorted(missing_keys)}"
        )

    if metadata is not None:
        for key in ("variant_id", "student_id", "student_name"):
            if summary.get(key) != metadata.get(key):
                errors.append(
                    f"summary {key} does not match metadata.json"
                )

    raw_input_rows = sum(
        1
        for line in RAW_EVENTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )

    if summary.get("input_records") != raw_input_rows:
        errors.append(
            "summary input_records does not match raw_iot_events.jsonl rows"
        )

    if clean is not None and summary.get("clean_records") != clean.height:
        errors.append(
            "summary clean_records does not match clean parquet rows"
        )

    expected_rejected_lines = (
        int(summary.get("rejected_records", -1))
        + int(summary.get("removed_duplicate_records", -1))
    )
    if expected_rejected_lines != len(rejected_rows):
        errors.append(
            "rejected jsonl row count does not match "
            "rejected_records + removed_duplicate_records"
        )

    try:
        input_records = int(summary["input_records"])
        clean_records = int(summary["clean_records"])
        unchanged_records = int(summary["unchanged_records"])
        repaired_records = int(summary["repaired_records"])
        rejected_records = int(summary["rejected_records"])
        removed_duplicate_records = int(summary["removed_duplicate_records"])

        if input_records != clean_records + rejected_records + removed_duplicate_records:
            errors.append(
                "summary invariant failed: "
                "input != clean + rejected + removed_duplicate"
            )

        if clean_records != unchanged_records + repaired_records:
            errors.append(
                "summary invariant failed: clean != unchanged + repaired"
            )
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"summary counters are invalid: {exc}")


if issues is not None and summary is not None and set(ISSUES_COLUMNS) <= set(issues.columns):
    issue_rows = issues.to_dicts()

    actual_actions = dict(
        Counter(str(row["action"]) for row in issue_rows)
    )
    actual_issue_types = dict(
        Counter(str(row["issue_type"]) for row in issue_rows)
    )

    if summary.get("actions_by_type") != actual_actions:
        errors.append(
            "summary actions_by_type does not match data_quality_issues.csv"
        )

    if summary.get("issues_by_type") != actual_issue_types:
        errors.append(
            "summary issues_by_type does not match data_quality_issues.csv"
        )

    for action, key in (
        ("repaired", "repaired_records"),
        ("rejected", "rejected_records"),
        ("removed_duplicate", "removed_duplicate_records"),
    ):
        if summary.get(key) != actual_actions.get(action, 0):
            errors.append(
                f"summary {key} does not match issue actions"
            )


if errors:
    for error in errors:
        print("ERR:", error)
    sys.exit(1)

print("OK: practical 02 output contract is valid")
