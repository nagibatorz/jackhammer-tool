"""Constants and default values for Jackhammer application."""

# Server connection defaults
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 3000

# Jackhammer parameter defaults (Gentle - safe for dura)
DEFAULT_ITERATIONS = 2
DEFAULT_PHASE1_STEPS = 1
DEFAULT_PHASE1_PULSES = 70
DEFAULT_PHASE2_STEPS = 1
DEFAULT_PHASE2_PULSES = -70

# Axis (always depth for jackhammer)
DEPTH_AXIS = 3

# Presets
PRESETS = {
    "Gentle": {
        "iterations": 2,
        "phase1_steps": 1,
        "phase1_pulses": 70,
        "phase2_steps": 1,
        "phase2_pulses": -70,
        "description": "Safe for dura. ~4.7 µm per call.",
        "predicted_um": 4.7,
    },
    "Standard": {
        "iterations": 10,
        "phase1_steps": 1,
        "phase1_pulses": 100,
        "phase2_steps": 1,
        "phase2_pulses": -100,
        "description": "SDK defaults. ~23.8 µm per call.",
        "predicted_um": 23.8,
    },
}

# Tooltips for parameters
TOOLTIPS = {
    "manipulator_id": "The ID number of the manipulator (shown in Ephys Link on startup).",
    "iterations": "Number of jackhammer cycles. Higher = more vibration.",
    "phase1_steps": "Steps in forward phase. Primary multiplier for advancement.",
    "phase1_pulses": "Pulse intensity for forward phase (1-100). Acts as dampener.",
    "phase2_steps": "Steps in backward phase. Usually less than phase 1.",
    "phase2_pulses": "Pulse intensity for backward phase (-100 to -1). Negative = backward.",
    "inside_brain": "Check this when the probe is inside brain tissue. Reminds you to be careful.",
}


def calculate_advancement(iterations: int, phase1_steps: int, phase1_pulses: int) -> float:
    """Calculate predicted advancement in micrometers.
    
    Based on empirical formula: Δw ≈ 0.3 · I^0.9 · S1^1.4 · P1^0.5
    
    Args:
        iterations: Number of jackhammer cycles.
        phase1_steps: Steps in phase 1.
        phase1_pulses: Pulse count for phase 1 (absolute value used).
        
    Returns:
        Predicted advancement in micrometers.
    """
    if iterations <= 0 or phase1_steps <= 0 or phase1_pulses == 0:
        return 0.0
    return 0.3 * (iterations ** 0.9) * (phase1_steps ** 1.4) * (abs(phase1_pulses) ** 0.5)