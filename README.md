# Jackhammer Tool - params-logging

A version of standalone GUI application for running jackhammer mode on Sensapex manipulators via Ephys Link. Designed for neuroscientists who need to break through the dura mater without using the full Pinpoint application.
Ths specific version enables researchers to record parameters used to tun jackhammer in a .csv file for research or convenience purposes.

## What is Jackhammer Mode?

Jackhammer mode creates rapid vibration in the manipulator to help the probe penetrate the dura mater (the tough membrane covering the brain). The manipulator oscillates back and forth on the depth axis, helping the probe break through resistant tissue without excessive force.

## Requirements

- Python 3.10+
- [Ephys Link](https://github.com/VirtualBrainLab/ephys-link) server running
- Sensapex uMp manipulators

## Installation

### From Source

```bash
git clone https://github.com/VirtualBrainLab/jackhammer-tool.git
cd jackhammer-tool
git checkout params-logging
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m jackhammer_app
```

### Executable

Download `JackhammerTool.exe` from Releases and run directly.

## Usage

1. **Start Ephys Link server:**
   ```bash
   ephys-link -b -t ump
   ```
2. **Launch Jackhammer Tool**
3. **Connect** to the server (default: localhost:3000)
4. **Enter manipulator ID** (shown in Ephys Link on startup)
5. **Run Jackhammer** with desired parameters

## Features

- **Presets:** Gentle (~4.7 µm) and Standard (~23.8 µm)
- **Live prediction:** See estimated advancement as you adjust parameters
- **Position tracking:** View current position and actual advancement
- **Total advancement:** Tracks cumulative advancement per manipulator
- **Calculator tab:** Explore the empirical advancement formula
- **Emergency stop:** Ctrl+Alt+Shift+Q
- **Run logging (this branch):** Every jackhammer run is appended to a CSV file for later analysis

## Run Logging

Every open- and closed-loop run is logged as one row in:

```
%USERPROFILE%\JackhammerTool\runs.csv   (Windows)
~/JackhammerTool/runs.csv               (Mac/Linux)
```

The file is created automatically on first launch and appended to thereafter — nothing is ever overwritten or deleted by the app. Move or delete the file manually when you want to archive or reset.

### Logged columns

| Column | Description |
|---|---|
| `timestamp_iso` | When the run completed (ISO 8601, local TZ) |
| `date` | YYYY-MM-DD, for joining with paper experiment forms |
| `mode` | `open` or `closed` |
| `manipulator_id` | Manipulator that ran |
| `preset` | `Gentle`, `Standard`, `Custom`, or blank (closed loop) |
| `iterations_param` | Iterations parameter (open loop only) |
| `phase1_steps`, `phase1_pulses` | Forward-phase parameters |
| `phase2_steps`, `phase2_pulses` | Backward-phase parameters |
| `target_um` | Target advancement, µm (closed loop only) |
| `max_iterations` | Safety cap (closed loop only) |
| `iterations_used` | Iterations actually run (closed loop only) |
| `stop_reason` | `target_reached`, `backward_movement`, `max_iterations`, `aborted` |
| `advancement_um` | Actual advancement, µm |
| `aborted` | `true` if user hit emergency stop |
| `app_version` | Schema version of the writing app |

### Joining with paper forms

Each row carries `date` and `manipulator_id`, which match the experiment form fields (mouse name, experimenter, jackhammer used, bleeding, bending, probe ID). Join on `(date, manipulator_id)` to recover full session context for each run.

## Parameter Guide

| Parameter | Description |
|-----------|-------------|
| Iterations | Number of jackhammer cycles |
| Phase 1 Steps | Steps in forward phase (primary multiplier) |
| Phase 1 Pulses | Intensity of forward movement (1-100) |
| Phase 2 Steps | Steps in backward phase |
| Phase 2 Pulses | Intensity of backward movement (-100 to -1) |

### Empirical Advancement Formula

```
Δw (µm) ≈ 0.3 × I^0.9 × S₁^1.4 × P₁^0.5
```

Where I = iterations, S₁ = phase 1 steps, P₁ = phase 1 pulses.

## Safety

⚠️ **Start with Gentle preset** - only increase intensity if needed

⚠️ **Multiple small runs** are safer than one aggressive run

⚠️ **Check position** after each jackhammer call

⚠️ **Emergency stop:** Ctrl+Alt+Shift+Q

## Related Projects

- [Ephys Link](https://github.com/VirtualBrainLab/ephys-link) - Manipulator control server
- [Pinpoint](https://github.com/VirtualBrainLab/Pinpoint) - Trajectory planning application
