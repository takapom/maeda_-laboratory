---
name: eval-run
description: >-
  Run a drone controller evaluation. Generates a patch.diff from controller/ changes,
  then executes Agent Runner to evaluate baseline vs candidate on CoppeliaSim.
  Use when the user wants to evaluate controller code changes or run a simulation comparison.
compatibility: Requires Python 3.11+, git, and project venv (.venv) activated.
allowed-tools: Bash(git:*) Bash(python:*) Read Write
metadata:
  author: maeda-laboratory
  version: "0.1"
---

## Overview

This skill runs an end-to-end evaluation of controller code changes against the baseline.

The workflow is:

1. Generate a `patch.diff` from current `controller/` changes
2. Execute Agent Runner with the patch
3. Report evaluation results (metrics, comparison, pass/fail)

See [references/workflow.md](references/workflow.md) for the detailed step-by-step procedure.

## Quick start

Generate a patch and run evaluation:

```bash
bash scripts/run-eval.sh --goal "Describe the optimization goal"
```

## Available scripts

- **`scripts/run-eval.sh`** — Main entry point. Generates patch from working tree, runs evaluation, prints summary.
- **`scripts/gen-patch.sh`** — Generates `patch.diff` from uncommitted `controller/` changes.
- **`scripts/show-results.sh`** — Displays metrics and summary from a completed run.

## Typical usage

### 1. Modify controller code

Edit files under `controller/` to improve drone behavior (e.g., tune gains, change logic).

### 2. Run evaluation

```bash
bash scripts/run-eval.sh --goal "Reduce collision count while maintaining success rate"
```

The script will:
- Detect the project root and venv
- Generate a patch from uncommitted `controller/` changes
- Run Agent Runner with the patch
- Print the evaluation summary

### 3. Review results

```bash
bash scripts/show-results.sh <run_id>
```

Or inspect artifacts directly:

```bash
cat $ARTIFACTS_ROOT/runs/<run_id>/summary.json | python3 -m json.tool
cat $ARTIFACTS_ROOT/runs/<run_id>/metrics.json | python3 -m json.tool
```

## Environment variables

The scripts respect the following (with defaults):

| Variable | Default | Description |
|---|---|---|
| `ARTIFACTS_ROOT` | `/tmp/drone-poc/artifacts` | Where run artifacts are stored |
| `WORKSPACE_ROOT` | `/tmp/drone-poc/workspace` | Where fresh clones are created |
| `COPPELIASIM_HOST` | `127.0.0.1` | CoppeliaSim host |
| `COPPELIASIM_PORT` | `23000` | CoppeliaSim port |

## Error handling

- If no `controller/` changes exist, the patch generation step fails with a clear message.
- If Agent Runner exits non-zero, the script prints stderr and the path to `stdout.log`.
- Stale lock files are detected and reported with removal instructions.
