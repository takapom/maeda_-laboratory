# Metrics Guide

## Primary metrics

### success_rate

- **Definition**: Successful episodes / total episodes
- **Range**: 0.0 - 1.0
- **Direction**: Higher is better
- **Notes**: Connection failures and mid-episode crashes count as failures in the denominator

### collision_count_mean

- **Definition**: Total collisions across all episodes / total episodes
- **Range**: 0.0 - infinity
- **Direction**: Lower is better
- **Notes**: Counted for all episodes, including failed ones

### time_to_goal_mean_sec

- **Definition**: Average simulation time to reach goal, among successful episodes only
- **Range**: 0.0 - sim_time_limit_sec, or null
- **Direction**: Lower is better
- **Notes**: null when success_rate is 0 (no successful episodes to average)

## Diagnostic metric

### reward_mean

- **Definition**: Average cumulative reward across all episodes
- **Direction**: Higher is better
- **Notes**: Diagnostic only. Not used in pass/fail criteria by default.

## Delta interpretation

Deltas are computed as `candidate - baseline`:

| Metric | Positive delta | Negative delta |
|---|---|---|
| success_rate | Improvement | Regression |
| collision_count_mean | Regression | Improvement |
| time_to_goal_mean_sec | Regression | Improvement |
| reward_mean | Improvement | Regression |

## Evaluation profile

The `evaluation_profile.json` defines:

- **primary_metrics**: Which metrics to consider
- **weights**: Relative importance of each metric
- **pass_criteria**: Thresholds for pass/fail
  - `success_rate_min`: Minimum acceptable success rate
  - `collision_count_mean_max`: Maximum acceptable collision rate
  - `time_to_goal_mean_sec_max`: Maximum acceptable average time

A run "passes" if all specified criteria are met by the candidate.

## Re-evaluation

Since raw observations are preserved in `episodes_baseline.jsonl` / `episodes_candidate.jsonl`,
metrics can be re-computed with different weights or thresholds without re-running the simulation.
