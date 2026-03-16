# Controller Architecture Guide

## Directory structure

```
controller/
  __init__.py
  drone_controller.py    # Main controller class
```

## DroneController class

The core class in `drone_controller.py`:

```python
class DroneController:
    def __init__(self, goal_position):
        self.goal_position = goal_position
        self.kp = 1.0  # proportional gain

    def compute_control(self, current_position, current_velocity):
        # Returns (vx, vy, vz) velocity command
        ...
```

### Key interface

- **Input**: `current_position (x, y, z)` and `current_velocity (vx, vy, vz)`
- **Output**: `(vx, vy, vz)` velocity command tuple
- **Goal**: Navigate to `self.goal_position` while minimizing collisions and time

### Evaluation metrics

The controller is evaluated on:

1. **success_rate** — Fraction of episodes reaching the goal
2. **collision_count_mean** — Average collisions per episode (lower is better)
3. **time_to_goal_mean_sec** — Average time to reach goal in successful episodes (lower is better)
4. **reward_mean** — Average cumulative reward (diagnostic)

## Modification guidelines

### Safe changes

- Tuning gain parameters (`kp`, `kd`, `ki`)
- Adding new control terms (derivative, integral)
- Adding obstacle detection/avoidance logic
- Adding trajectory smoothing
- Adding state estimation improvements

### Avoid

- Changing the `compute_control` method signature
- Importing modules not available in the eval environment
- Adding file I/O or network calls
- Modifying files outside `controller/`

## Adding new files

New files can be added under `controller/`. They will be included in the patch.
Import them from `drone_controller.py` as needed:

```python
# controller/utils.py
def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))

# controller/drone_controller.py
from controller.utils import clamp
```
