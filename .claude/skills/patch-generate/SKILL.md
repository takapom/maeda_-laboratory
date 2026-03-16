---
name: patch-generate
description: >-
  Generate a controller patch for drone evaluation. Reads the current controller/ code,
  analyzes the optimization goal, modifies controller/ files, and produces a patch.diff.
  Use when the user wants to improve drone controller behavior or create a candidate for evaluation.
compatibility: Requires Python 3.11+, git.
allowed-tools: Bash(git:*) Read Write Edit
metadata:
  author: maeda-laboratory
  version: "0.1"
---

## Overview

This skill guides the process of modifying `controller/` code to achieve an optimization goal,
then generates a `patch.diff` suitable for evaluation via `eval-run`.

See [references/controller-guide.md](references/controller-guide.md) for details on the controller architecture and modification patterns.

## Workflow

### 1. Understand the current controller

Read the controller code to understand the current implementation:

```bash
bash scripts/read-controller.sh
```

### 2. Review past evaluation results (optional)

If previous runs exist, check what has been tried:

```bash
bash scripts/list-past-goals.sh
```

### 3. Modify controller code

Based on the optimization goal, edit files under `controller/`.

**Rules:**
- Only modify files under `controller/`
- Do not modify `eval/` (fixed in PoC)
- Keep changes focused on the stated goal
- Ensure the code remains valid Python

### 4. Validate changes

```bash
bash scripts/validate-patch.sh
```

This runs:
- Syntax check on modified files
- Generates a preview diff
- Confirms changes are within `controller/` only

### 5. Generate patch.diff

```bash
bash scripts/gen-patch.sh --output /tmp/drone-poc/patch.diff
```

### 6. Hand off to evaluation

The generated patch can be used with `eval-run`:

```bash
bash .claude/skills/eval-run/scripts/run-eval.sh \
  --goal "The optimization goal" \
  --patch-file /tmp/drone-poc/patch.diff
```

## Available scripts

- **`scripts/read-controller.sh`** — Print all controller/ source files with context.
- **`scripts/list-past-goals.sh`** — List goals from previous evaluation runs.
- **`scripts/validate-patch.sh`** — Validate controller/ changes before generating a patch.
- **`scripts/gen-patch.sh`** — Generate patch.diff from controller/ changes.

## Common modification patterns

| Goal | Typical change |
|---|---|
| Faster response | Increase `kp` (proportional gain) |
| Reduce overshoot | Add derivative term or damping |
| Avoid collisions | Add obstacle avoidance logic |
| Smoother trajectory | Add trajectory smoothing / filtering |
