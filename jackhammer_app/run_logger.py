"""CSV run logger for jackhammer experiments.

Logs every jackhammer run (open and closed loop) to a CSV file in the user's
home directory. One row per run. Append-only with flush after every write so
mid-experiment crashes don't lose history.

Default location: ~/JackhammerTool/runs.csv

Schema (stable; new columns added at end if needed):
    timestamp_iso     - ISO 8601 timestamp with timezone
    date              - YYYY-MM-DD (for joining with paper forms)
    mode              - "open" or "closed"
    manipulator_id    - Manipulator that ran
    preset            - "Gentle" | "Standard" | "Custom" | "" (closed loop)
    iterations_param  - Iterations parameter (open loop only)
    phase1_steps      - Phase 1 steps
    phase1_pulses     - Phase 1 pulses
    phase2_steps      - Phase 2 steps
    phase2_pulses     - Phase 2 pulses
    target_um         - Target advancement (closed loop only)
    max_iterations    - Max iterations safety limit (closed loop only)
    iterations_used   - Iterations actually used (closed loop only)
    stop_reason       - target_reached | backward_movement | max_iterations | aborted
    advancement_um    - Actual advancement in µm
    aborted           - "true" | "false"
    app_version       - Version of Jackhammer Tool that produced the row
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

# Bump if you ever change the schema in a breaking way.
APP_VERSION = "1.0"

# Column order is the on-disk schema. Do not reorder; only append.
FIELDNAMES = [
    "timestamp_iso",
    "date",
    "mode",
    "manipulator_id",
    "preset",
    "iterations_param",
    "phase1_steps",
    "phase1_pulses",
    "phase2_steps",
    "phase2_pulses",
    "target_um",
    "max_iterations",
    "iterations_used",
    "stop_reason",
    "advancement_um",
    "aborted",
    "app_version",
]

logger = logging.getLogger(__name__)


def default_log_path() -> Path:
    """Return the default log path: ~/JackhammerTool/runs.csv."""
    return Path.home() / "JackhammerTool" / "runs.csv"


class RunLogger:
    """Append-only CSV logger for jackhammer runs.

    Thread-safe (uses a lock around writes). Creates the parent directory
    and writes the header row on first use if the file doesn't exist.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path: Path = path if path is not None else default_log_path()
        self._lock = Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Create parent dir and write header if file is new."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                with self.path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                    writer.writeheader()
        except OSError as e:
            # Don't crash the GUI if the log can't be set up - just warn.
            logger.warning("RunLogger: could not initialize %s: %s", self.path, e)

    def log_open_loop(
        self,
        manipulator_id: str,
        iterations: int,
        phase1_steps: int,
        phase1_pulses: int,
        phase2_steps: int,
        phase2_pulses: int,
        advancement_um: float,
        preset: str = "",
        aborted: bool = False,
    ) -> None:
        """Log one open-loop run."""
        self._write_row({
            "mode": "open",
            "manipulator_id": manipulator_id,
            "preset": preset,
            "iterations_param": iterations,
            "phase1_steps": phase1_steps,
            "phase1_pulses": phase1_pulses,
            "phase2_steps": phase2_steps,
            "phase2_pulses": phase2_pulses,
            "advancement_um": f"{advancement_um:.3f}",
            "aborted": "true" if aborted else "false",
        })

    def log_closed_loop(
        self,
        manipulator_id: str,
        target_um: float,
        max_iterations: int,
        phase1_steps: int,
        phase1_pulses: int,
        phase2_steps: int,
        phase2_pulses: int,
        iterations_used: int,
        stop_reason: str,
        advancement_um: float,
    ) -> None:
        """Log one closed-loop run."""
        self._write_row({
            "mode": "closed",
            "manipulator_id": manipulator_id,
            "preset": "",  # presets are open-loop concept in current GUI
            "phase1_steps": phase1_steps,
            "phase1_pulses": phase1_pulses,
            "phase2_steps": phase2_steps,
            "phase2_pulses": phase2_pulses,
            "target_um": f"{target_um:.3f}",
            "max_iterations": max_iterations,
            "iterations_used": iterations_used,
            "stop_reason": stop_reason,
            "advancement_um": f"{advancement_um:.3f}",
            "aborted": "true" if stop_reason == "aborted" else "false",
        })

    def _write_row(self, fields: dict) -> None:
        """Fill in timestamp/version fields and append one row, thread-safe."""
        now = datetime.now(timezone.utc).astimezone()
        row = {name: "" for name in FIELDNAMES}  # blanks for unused columns
        row["timestamp_iso"] = now.isoformat(timespec="seconds")
        row["date"] = now.strftime("%Y-%m-%d")
        row["app_version"] = APP_VERSION
        row.update(fields)

        with self._lock:
            try:
                with self.path.open("a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                    writer.writerow(row)
                    f.flush()
            except OSError as e:
                logger.warning("RunLogger: could not write row to %s: %s", self.path, e)
