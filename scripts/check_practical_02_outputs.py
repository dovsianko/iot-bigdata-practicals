#!/usr/bin/env python3
from pathlib import Path
import json
import sys
import polars as pl

ROOT = Path('/workspace') if Path('/workspace').exists() else Path.cwd()
if not (ROOT / 'data' / 'input').exists() and (ROOT.parent / 'data' / 'input').exists():
    ROOT = ROOT.parent

RESULTS_DIR = ROOT / 'results' / 'practical_02'
required = {
    'clean': RESULTS_DIR / 'clean_iot_events.parquet',
    'issues': RESULTS_DIR / 'data_quality_issues.csv',
    'rejected': RESULTS_DIR / 'rejected_iot_events.jsonl',
    'summary': RESULTS_DIR / 'cleaning_summary.json',
}

errors = []
for name, path in required.items():
    if not path.is_file():
        errors.append(f'missing {name}: {path}')

if not errors:
    clean = pl.read_parquet(required['clean'])
    issues = pl.read_csv(required['issues'])
    with required['summary'].open('r', encoding='utf-8') as f:
        summary = json.load(f)

    for col in ['event_id', 'event_ts', 'device_id', 'event_type', 'metric', 'value']:
        if col not in clean.columns:
            errors.append(f'missing clean column: {col}')

    if 'event_id' in clean.columns and clean['event_id'].n_unique() != clean.height:
        errors.append('duplicate event_id in clean parquet')

    if summary.get('clean_records') != clean.height:
        errors.append('summary clean_records does not match parquet rows')

    if issues.height == 0:
        print('WARN: data_quality_issues.csv is empty')

if errors:
    for error in errors:
        print('ERR:', error)
    sys.exit(1)

print('OK: practical 02 outputs found in results/practical_02')
