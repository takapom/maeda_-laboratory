# Evaluation Run Workflow

## Prerequisites

- Project venv (`.venv`) must be set up: `pip install -e ".[dev]"`
- The repo must have at least one commit (Agent Runner clones from it)
- `controller/` changes must be present in the working tree (unstaged or staged)

## Step-by-step procedure

### 1. Prepare controller changes

Edit files under `controller/` to improve the drone behavior. Changes should be limited to `controller/` only — `eval/` is fixed in PoC.

### 2. Generate patch.diff

```bash
bash scripts/gen-patch.sh
```

This creates a `patch.diff` in `/tmp/drone-poc/` from the current `controller/` diff.

If no changes are detected, the script exits with code 1 and prints an error.

### 3. Run evaluation

```bash
bash scripts/run-eval.sh --goal "<optimization goal>"
```

Or with explicit options:

```bash
bash scripts/run-eval.sh \
  --goal "Increase proportional gain for faster response" \
  --constraints "Do not increase collision count"
```

What happens internally:

1. `gen-patch.sh` generates `/tmp/drone-poc/patch.diff`
2. Agent Runner is invoked:
   - Acquires lock
   - Fresh clones the repo at HEAD
   - Applies patch to the clone
   - Runs `make lint`, `make typecheck`, `make unit`
   - Launches sim-eval as subprocess
   - sim-eval evaluates baseline and candidate with same seeds/scene
   - Writes metrics.json, summary.json, episodes JSONL
   - Releases lock

### 4. Review results

```bash
bash scripts/show-results.sh <run_id>
```

The script prints:
- Run status (succeeded / failed / timed_out)
- Baseline vs candidate metrics
- Delta (improvement/regression)
- Pass/fail based on evaluation_profile

### 5. Iterate

Based on results, modify `controller/` and re-run from step 2.

## Artifacts layout

After a run, `$ARTIFACTS_ROOT/runs/<run_id>/` contains:

```
request.json              Goal and constraints
patch.diff                The exact diff applied
git.json                  Repo URL, base_ref, SHA
params.json               Seeds, episodes, timeouts
patch_provider.json       How the patch was generated
runtime.json              Python version, dependency hash
evaluation_profile.json   Weights, pass criteria
metrics.json              Baseline/candidate metrics + delta
summary.json              Pass/fail judgment + reason
episodes_baseline.jsonl   Per-episode raw observations (baseline)
episodes_candidate.jsonl  Per-episode raw observations (candidate)
stdout.log                sim-eval stdout
stderr.log                sim-eval stderr
```

## Troubleshooting

### Lock file remains after crash

```bash
rm $ARTIFACTS_ROOT/locks/active_run.lock
```

### No controller changes detected

Ensure you have uncommitted changes in `controller/`. Staged or unstaged both work.

### sim-eval timeout

Increase `SIM_TIME_LIMIT_SEC` or `CONNECT_TIMEOUT_SEC` environment variables.
