---
name: results-analyze
description: >-
  Analyze and compare drone evaluation results across runs. View metrics trends,
  compare specific runs side-by-side, re-evaluate with different profiles, and
  export analysis summaries. Use when reviewing evaluation history or deciding next steps.
compatibility: Requires Python 3.11+.
allowed-tools: Bash(python:*) Read
metadata:
  author: maeda-laboratory
  version: "0.1"
---

## Overview

This skill provides tools to analyze evaluation results stored in `$ARTIFACTS_ROOT/runs/`.

See [references/metrics-guide.md](references/metrics-guide.md) for metric definitions and interpretation.

## Available scripts

- **`scripts/compare-runs.py`** — Side-by-side comparison of two runs.
- **`scripts/trend.py`** — Show metrics trend across recent runs.
- **`scripts/re-evaluate.py`** — Re-evaluate episodes with a different evaluation_profile.
- **`scripts/export-csv.py`** — Export run history to CSV for external analysis.

## Usage examples

### Compare two runs

```bash
python3 scripts/compare-runs.py RUN_ID_A RUN_ID_B
```

### Show recent trends

```bash
python3 scripts/trend.py --limit 10
```

### Re-evaluate with a different profile

```bash
python3 scripts/re-evaluate.py RUN_ID --success-rate-min 0.8 --collision-max 2.0
```

### Export to CSV

```bash
python3 scripts/export-csv.py --output /tmp/runs.csv
```
