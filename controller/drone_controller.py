"""Drone controller stub for PoC.

This is the file that the LLM will modify to improve drone behavior.
"""

from __future__ import annotations


class DroneController:
    """Basic drone controller that navigates toward a goal position."""

    def __init__(self, goal_position: tuple[float, float, float] = (0.0, 0.0, 1.0)):
        self.goal_position = goal_position
        self.kp = 1.0  # proportional gain

    def compute_control(
        self,
        current_position: tuple[float, float, float],
        current_velocity: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        """Compute velocity command toward goal.

        Returns (vx, vy, vz) command.
        """
        error = (
            self.goal_position[0] - current_position[0],
            self.goal_position[1] - current_position[1],
            self.goal_position[2] - current_position[2],
        )
        return (
            self.kp * error[0],
            self.kp * error[1],
            self.kp * error[2],
        )
