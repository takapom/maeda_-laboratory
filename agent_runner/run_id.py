"""Run ID generation."""

from __future__ import annotations

import time
import uuid


def generate() -> str:
    """Generate a unique run ID: timestamp + short uuid."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    short = uuid.uuid4().hex[:8]
    return f"{ts}-{short}"
