"""Smoke test for CoppeliaSim connection."""

from __future__ import annotations

import os
import sys

from sim_eval.sim_client import SimClient, SimConnectionError


def main() -> None:
    host = os.environ.get("COPPELIASIM_HOST", "127.0.0.1")
    port = int(os.environ.get("COPPELIASIM_PORT", "23000"))
    timeout = int(os.environ.get("CONNECT_TIMEOUT_SEC", "10"))

    print(f"Connecting to CoppeliaSim at {host}:{port} (timeout={timeout}s) ...")

    client = SimClient(host=host, port=port, connect_timeout_sec=timeout)
    try:
        client.connect()
    except SimConnectionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    version = client.get_version()
    print(f"OK: Connected to CoppeliaSim v{version}")


if __name__ == "__main__":
    main()
