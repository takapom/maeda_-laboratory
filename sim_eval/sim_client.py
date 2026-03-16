"""CoppeliaSim ZeroMQ Remote API client wrapper."""

from __future__ import annotations

import time
from typing import Any


class SimConnectionError(Exception):
    pass


class SimClient:
    """Thin wrapper around CoppeliaSim ZeroMQ Remote API."""

    def __init__(self, host: str, port: int, connect_timeout_sec: int = 30):
        self.host = host
        self.port = port
        self.connect_timeout_sec = connect_timeout_sec
        self._sim: Any = None

    def connect(self) -> None:
        """Establish connection to CoppeliaSim via ZeroMQ Remote API."""
        try:
            from coppeliasim_zmqremoteapi_client import RemoteAPIClient
        except ImportError as e:
            raise SimConnectionError(
                "coppeliasim-zmqremoteapi-client is not installed. "
                "Run: pip install coppeliasim-zmqremoteapi-client"
            ) from e

        deadline = time.monotonic() + self.connect_timeout_sec
        last_err: Exception | None = None

        while time.monotonic() < deadline:
            try:
                client = RemoteAPIClient(host=self.host, port=self.port)
                self._sim = client.require("sim")
                # Verify connection by calling a lightweight API
                self._sim.getInt32Param(self._sim.intparam_program_version)
                return
            except Exception as e:
                last_err = e
                time.sleep(1)

        raise SimConnectionError(
            f"Failed to connect to CoppeliaSim at {self.host}:{self.port} "
            f"within {self.connect_timeout_sec}s: {last_err}"
        )

    @property
    def sim(self) -> Any:
        if self._sim is None:
            raise SimConnectionError("Not connected. Call connect() first.")
        return self._sim

    def load_scene(self, scene_path: str) -> None:
        """Load a scene file."""
        self.sim.loadScene(scene_path)

    def start_simulation(self) -> None:
        """Start simulation in stepping mode."""
        self.sim.setStepping(True)
        self.sim.startSimulation()

    def step(self) -> None:
        """Advance simulation by one step."""
        self.sim.step()

    def stop_simulation(self) -> None:
        """Stop the running simulation."""
        self.sim.stopSimulation()
        # Wait until simulation actually stops
        while self.sim.getSimulationState() != self.sim.simulation_stopped:
            time.sleep(0.05)

    def get_simulation_time(self) -> float:
        return self.sim.getSimulationTime()

    def get_version(self) -> str:
        v = self.sim.getInt32Param(self.sim.intparam_program_version)
        major = v // 10000
        minor = (v // 100) % 100
        patch = v % 100
        return f"{major}.{minor}.{patch}"
