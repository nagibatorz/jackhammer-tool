"""Data models for Jackhammer application."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class JackhammerParams:
    """Parameters for a jackhammer command."""

    manipulator_id: str
    iterations: int
    phase1_steps: int
    phase1_pulses: int
    phase2_steps: int
    phase2_pulses: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "manipulator_id": self.manipulator_id,
            "iterations": self.iterations,
            "phase1_steps": self.phase1_steps,
            "phase1_pulses": self.phase1_pulses,
            "phase2_steps": self.phase2_steps,
            "phase2_pulses": self.phase2_pulses,
        }


@dataclass
class Position:
    """Manipulator position."""

    x: float
    y: float
    z: float
    w: float

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        """Create Position from dictionary."""
        return cls(
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            z=data.get("z", 0.0),
            w=data.get("w", 0.0),
        )

    def __str__(self) -> str:
        return f"x={self.x:.4f}, y={self.y:.4f}, z={self.z:.4f}, w={self.w:.4f}"


@dataclass
class JackhammerResult:
    """Result of a jackhammer command."""

    position: Optional[Position]
    error: str

    @classmethod
    def from_dict(cls, data: dict) -> "JackhammerResult":
        """Create JackhammerResult from server response."""
        error = data.get("Error", "")
        position = None
        if not error and "Position" in data:
            position = Position.from_dict(data["Position"])
        return cls(position=position, error=error)

    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return not self.error