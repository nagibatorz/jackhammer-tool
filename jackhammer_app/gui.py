"""GUI components for Jackhammer application."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from .client import EphysLinkClient
from .constants import (
    DEFAULT_HOST,
    DEFAULT_ITERATIONS,
    DEFAULT_PHASE1_PULSES,
    DEFAULT_PHASE1_STEPS,
    DEFAULT_PHASE2_PULSES,
    DEFAULT_PHASE2_STEPS,
    DEFAULT_PORT,
    PRESETS,
    TOOLTIPS,
    calculate_advancement,
)
from .models import JackhammerParams, JackhammerResult, Position


class ToolTip:
    """Hover tooltip for widgets."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        """Create tooltip for widget."""
        self.widget = widget
        self.text = text
        self.tooltip_window: Optional[tk.Toplevel] = None
        
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None) -> None:
        """Show tooltip."""
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(
            self.tooltip_window,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padding=(5, 2),
        )
        label.pack()

    def _hide(self, event=None) -> None:
        """Hide tooltip."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class StatusLog:
    """Status log text area widget."""

    def __init__(self, parent: ttk.Frame) -> None:
        """Initialize status log."""
        frame = ttk.LabelFrame(parent, text="Status", padding="5")
        frame.pack(fill="x", pady=(10, 0))

        self._text = tk.Text(frame, height=6, width=80, state="disabled")
        self._text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self._text.yview)
        scrollbar.pack(side="right", fill="y")
        self._text.configure(yscrollcommand=scrollbar.set)

    def log(self, message: str) -> None:
        """Add message to log."""
        self._text.configure(state="normal")
        self._text.insert("end", message + "\n")
        self._text.see("end")
        self._text.configure(state="disabled")


class ConnectionFrame:
    """Server connection UI section."""

    def __init__(
        self,
        parent: ttk.Frame,
        on_connect: Callable[[], None],
        on_disconnect: Callable[[], None],
    ) -> None:
        """Initialize connection frame."""
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._connected = False

        frame = ttk.LabelFrame(parent, text="Server Connection", padding="5")
        frame.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(frame)
        inner.pack(fill="x")

        ttk.Label(inner, text="Host:").pack(side="left", padx=(0, 5))
        self.host_entry = ttk.Entry(inner, width=15)
        self.host_entry.insert(0, DEFAULT_HOST)
        self.host_entry.pack(side="left")

        ttk.Label(inner, text="Port:").pack(side="left", padx=(10, 5))
        self.port_entry = ttk.Entry(inner, width=6)
        self.port_entry.insert(0, str(DEFAULT_PORT))
        self.port_entry.pack(side="left")

        self._connect_btn = ttk.Button(inner, text="Connect", command=self._toggle)
        self._connect_btn.pack(side="left", padx=(10, 0))

        self._status_label = ttk.Label(inner, text="● Disconnected", foreground="red")
        self._status_label.pack(side="left", padx=(10, 0))

    def _toggle(self) -> None:
        """Toggle connection state."""
        if self._connected:
            self._on_disconnect()
        else:
            self._on_connect()

    def set_connected(self, connected: bool) -> None:
        """Update UI for connection state."""
        self._connected = connected
        if connected:
            self._status_label.configure(text="● Connected", foreground="green")
            self._connect_btn.configure(text="Disconnect")
        else:
            self._status_label.configure(text="● Disconnected", foreground="red")
            self._connect_btn.configure(text="Connect")

    @property
    def host(self) -> str:
        return self.host_entry.get().strip()

    @property
    def port(self) -> int:
        return int(self.port_entry.get().strip())


class ManipulatorFrame:
    """Manipulator selection UI section."""

    def __init__(self, parent: ttk.Frame) -> None:
        """Initialize manipulator frame."""
        frame = ttk.LabelFrame(parent, text="Manipulator", padding="5")
        frame.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(frame)
        inner.pack(fill="x")

        ttk.Label(inner, text="Manipulator ID:").pack(side="left", padx=(0, 5))
        self.id_entry = ttk.Entry(inner, width=10)
        self.id_entry.pack(side="left")
        ToolTip(self.id_entry, TOOLTIPS["manipulator_id"])

        self.inside_brain = tk.BooleanVar(value=False)
        checkbox = ttk.Checkbutton(
            frame,
            text="Probe is inside brain (locks non-depth axes)",
            variable=self.inside_brain,
        )
        checkbox.pack(anchor="w", pady=(5, 0))
        ToolTip(checkbox, TOOLTIPS["inside_brain"])

    @property
    def manipulator_id(self) -> str:
        return self.id_entry.get().strip()

    @property
    def is_inside_brain(self) -> bool:
        return self.inside_brain.get()


class ParametersFrame:
    """Jackhammer parameters UI section with live prediction."""

    def __init__(self, parent: ttk.Frame, on_log: Callable[[str], None]) -> None:
        """Initialize parameters frame."""
        self._on_log = on_log
        
        frame = ttk.LabelFrame(parent, text="Jackhammer Parameters", padding="5")
        frame.pack(fill="x", pady=(0, 10))

        # Preset row
        preset_row = ttk.Frame(frame)
        preset_row.pack(fill="x", pady=(0, 5))
        
        ttk.Label(preset_row, text="Preset:").pack(side="left", padx=(0, 5))
        self._preset_var = tk.StringVar(value="Gentle")
        preset_dropdown = ttk.Combobox(
            preset_row,
            textvariable=self._preset_var,
            values=list(PRESETS.keys()),
            state="readonly",
            width=12,
        )
        preset_dropdown.pack(side="left")
        preset_dropdown.bind("<<ComboboxSelected>>", self._apply_preset)
        
        self._preset_desc = ttk.Label(preset_row, text=PRESETS["Gentle"]["description"], foreground="gray")
        self._preset_desc.pack(side="left", padx=(10, 0))

        # Parameters grid
        params_frame = ttk.Frame(frame)
        params_frame.pack(fill="x", pady=(5, 0))

        # Iterations
        ttk.Label(params_frame, text="Iterations:").grid(row=0, column=0, sticky="e", padx=(0, 5))
        self.iterations_entry = ttk.Entry(params_frame, width=10)
        self.iterations_entry.insert(0, str(DEFAULT_ITERATIONS))
        self.iterations_entry.grid(row=0, column=1, sticky="w")
        self.iterations_entry.bind("<KeyRelease>", self._update_prediction)
        ToolTip(self.iterations_entry, TOOLTIPS["iterations"])

        # Phase 1
        ttk.Label(params_frame, text="Phase 1 Steps:").grid(row=1, column=0, sticky="e", padx=(0, 5))
        self.phase1_steps_entry = ttk.Entry(params_frame, width=10)
        self.phase1_steps_entry.insert(0, str(DEFAULT_PHASE1_STEPS))
        self.phase1_steps_entry.grid(row=1, column=1, sticky="w")
        self.phase1_steps_entry.bind("<KeyRelease>", self._update_prediction)
        ToolTip(self.phase1_steps_entry, TOOLTIPS["phase1_steps"])

        ttk.Label(params_frame, text="Phase 1 Pulses:").grid(row=1, column=2, sticky="e", padx=(10, 5))
        self.phase1_pulses_entry = ttk.Entry(params_frame, width=10)
        self.phase1_pulses_entry.insert(0, str(DEFAULT_PHASE1_PULSES))
        self.phase1_pulses_entry.grid(row=1, column=3, sticky="w")
        self.phase1_pulses_entry.bind("<KeyRelease>", self._update_prediction)
        ToolTip(self.phase1_pulses_entry, TOOLTIPS["phase1_pulses"])

        # Phase 2
        ttk.Label(params_frame, text="Phase 2 Steps:").grid(row=2, column=0, sticky="e", padx=(0, 5))
        self.phase2_steps_entry = ttk.Entry(params_frame, width=10)
        self.phase2_steps_entry.insert(0, str(DEFAULT_PHASE2_STEPS))
        self.phase2_steps_entry.grid(row=2, column=1, sticky="w")
        ToolTip(self.phase2_steps_entry, TOOLTIPS["phase2_steps"])

        ttk.Label(params_frame, text="Phase 2 Pulses:").grid(row=2, column=2, sticky="e", padx=(10, 5))
        self.phase2_pulses_entry = ttk.Entry(params_frame, width=10)
        self.phase2_pulses_entry.insert(0, str(DEFAULT_PHASE2_PULSES))
        self.phase2_pulses_entry.grid(row=2, column=3, sticky="w")
        ToolTip(self.phase2_pulses_entry, TOOLTIPS["phase2_pulses"])

        # Live prediction display
        pred_frame = ttk.Frame(frame)
        pred_frame.pack(fill="x", pady=(10, 5))
        
        ttk.Label(pred_frame, text="Predicted Advancement:", font=("TkDefaultFont", 9, "bold")).pack(side="left")
        self._prediction_label = ttk.Label(pred_frame, text="~4.7 µm", font=("Consolas", 10), foreground="blue")
        self._prediction_label.pack(side="left", padx=(10, 0))
        
        # Warning label (hidden by default)
        self._warning_label = ttk.Label(pred_frame, text="", foreground="red")
        self._warning_label.pack(side="left", padx=(10, 0))

        # Reset button
        ttk.Button(frame, text="Reset to Gentle", command=self.reset).pack(pady=(5, 0))

    def _update_prediction(self, event=None) -> None:
        """Update the live prediction display."""
        try:
            iterations = int(self.iterations_entry.get().strip() or "0")
            phase1_steps = int(self.phase1_steps_entry.get().strip() or "0")
            phase1_pulses = int(self.phase1_pulses_entry.get().strip() or "0")
            
            advancement = calculate_advancement(iterations, phase1_steps, phase1_pulses)
            self._prediction_label.configure(text=f"~{advancement:.1f} µm")
            
            # Show warning for high advancement
            if advancement > 20:
                self._warning_label.configure(text="⚠️ High risk of overshoot!")
            elif advancement > 10:
                self._warning_label.configure(text="⚠️ Use caution")
            else:
                self._warning_label.configure(text="")
                
        except ValueError:
            self._prediction_label.configure(text="-- µm")
            self._warning_label.configure(text="")

    def _apply_preset(self, event=None) -> None:
        """Apply selected preset values."""
        preset_name = self._preset_var.get()
        preset = PRESETS[preset_name]
        
        self._set_entry(self.iterations_entry, preset["iterations"])
        self._set_entry(self.phase1_steps_entry, preset["phase1_steps"])
        self._set_entry(self.phase1_pulses_entry, preset["phase1_pulses"])
        self._set_entry(self.phase2_steps_entry, preset["phase2_steps"])
        self._set_entry(self.phase2_pulses_entry, preset["phase2_pulses"])
        self._preset_desc.configure(text=preset["description"])
        
        self._update_prediction()
        self._on_log(f"Applied preset: {preset_name}")

    def reset(self) -> None:
        """Reset all parameters to Gentle defaults."""
        self._preset_var.set("Gentle")
        self._apply_preset()

    def _set_entry(self, entry: ttk.Entry, value: int) -> None:
        """Set entry value."""
        entry.delete(0, "end")
        entry.insert(0, str(value))

    def get_params(self, manipulator_id: str) -> Optional[JackhammerParams]:
        """Get validated parameters."""
        try:
            return JackhammerParams(
                manipulator_id=manipulator_id,
                iterations=int(self.iterations_entry.get().strip()),
                phase1_steps=int(self.phase1_steps_entry.get().strip()),
                phase1_pulses=int(self.phase1_pulses_entry.get().strip()),
                phase2_steps=int(self.phase2_steps_entry.get().strip()),
                phase2_pulses=int(self.phase2_pulses_entry.get().strip()),
            )
        except ValueError:
            messagebox.showerror("Error", "All parameters must be integers.")
            return None


class ControlFrame:
    """Control buttons UI section."""

    def __init__(
        self,
        parent: ttk.Frame,
        on_run: Callable[[], None],
        on_stop: Callable[[], None],
        on_help: Callable[[], None],
    ) -> None:
        """Initialize control frame."""
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(0, 10))

        self.run_btn = ttk.Button(frame, text="Run Jackhammer", command=on_run, state="disabled")
        self.run_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

        style = ttk.Style()
        style.configure("Emergency.TButton", foreground="red")

        self.stop_btn = ttk.Button(
            frame,
            text="EMERGENCY STOP (Ctrl+Alt+Shift+Q)",
            command=on_stop,
            style="Emergency.TButton",
        )
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=(5, 5))

        self.help_btn = ttk.Button(frame, text="Help", command=on_help)
        self.help_btn.pack(side="left", padx=(5, 0))

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable run button."""
        self.run_btn.configure(state="normal" if enabled else "disabled")


class PositionFrame:
    """Position display UI section with advancement tracking."""

    def __init__(
        self,
        parent: ttk.Frame,
        on_get_position: Callable[[], None],
        on_reset_total: Callable[[], None],
    ) -> None:
        """Initialize position frame."""
        frame = ttk.LabelFrame(parent, text="Position & Advancement", padding="5")
        frame.pack(fill="x", pady=(0, 10))

        # Position row
        pos_row = ttk.Frame(frame)
        pos_row.pack(fill="x", pady=(0, 5))

        self.get_pos_btn = ttk.Button(
            pos_row, text="Get Position", command=on_get_position, state="disabled"
        )
        self.get_pos_btn.pack(side="left", padx=(0, 10))

        self.position_label = ttk.Label(pos_row, text="x: --  y: --  z: --  w: --", font=("Consolas", 10))
        self.position_label.pack(side="left", fill="x", expand=True)

        # Advancement row
        adv_row = ttk.Frame(frame)
        adv_row.pack(fill="x")

        ttk.Label(adv_row, text="Last Actual:").pack(side="left", padx=(0, 5))
        self._actual_label = ttk.Label(adv_row, text="-- µm", font=("Consolas", 10), foreground="blue")
        self._actual_label.pack(side="left", padx=(0, 20))

        ttk.Label(adv_row, text="Total:").pack(side="left", padx=(0, 5))
        self._total_label = ttk.Label(adv_row, text="0.0 µm", font=("Consolas", 10, "bold"), foreground="green")
        self._total_label.pack(side="left", padx=(0, 10))

        self._reset_btn = ttk.Button(adv_row, text="Reset Total", command=on_reset_total)
        self._reset_btn.pack(side="left")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable get position button."""
        self.get_pos_btn.configure(state="normal" if enabled else "disabled")

    def update_position(self, position: Position) -> None:
        """Update displayed position."""
        text = f"x: {position.x:.4f}   y: {position.y:.4f}   z: {position.z:.4f}   w: {position.w:.4f}"
        self.position_label.configure(text=text)

    def update_actual_advancement(self, advancement_um: float) -> None:
        """Update the last actual advancement display."""
        sign = "+" if advancement_um >= 0 else ""
        self._actual_label.configure(text=f"{sign}{advancement_um:.1f} µm")

    def update_total_advancement(self, total_um: float) -> None:
        """Update the total advancement display."""
        self._total_label.configure(text=f"{total_um:.1f} µm")

    def clear_actual(self) -> None:
        """Clear the actual advancement display."""
        self._actual_label.configure(text="-- µm")


class CalculatorTab:
    """Calculator tab for exploring advancement predictions."""

    def __init__(self, parent: ttk.Frame) -> None:
        """Initialize calculator tab."""
        # Formula explanation
        formula_frame = ttk.LabelFrame(parent, text="Empirical Formula", padding="10")
        formula_frame.pack(fill="x", pady=(0, 10))

        formula_text = """Advancement Δw (µm) ≈ 0.3 × I^0.9 × S₁^1.4 × P₁^0.5

Where:
  I  = Iterations (number of cycles)
  S₁ = Phase 1 Steps (primary multiplier)
  P₁ = Phase 1 Pulses (acts as dampener)

Note: Steps are the primary driver of advancement.
      Pulses provide raw mechanical force but scale slower."""

        ttk.Label(formula_frame, text=formula_text, justify="left", font=("Consolas", 9)).pack(anchor="w")

        # Interactive calculator
        calc_frame = ttk.LabelFrame(parent, text="Try Custom Parameters", padding="10")
        calc_frame.pack(fill="x", pady=(0, 10))

        # Input row
        input_row = ttk.Frame(calc_frame)
        input_row.pack(fill="x", pady=(0, 10))

        ttk.Label(input_row, text="Iterations:").pack(side="left", padx=(0, 5))
        self._iter_entry = ttk.Entry(input_row, width=6)
        self._iter_entry.insert(0, "1")
        self._iter_entry.pack(side="left")
        self._iter_entry.bind("<KeyRelease>", self._calculate)

        ttk.Label(input_row, text="Steps:").pack(side="left", padx=(10, 5))
        self._steps_entry = ttk.Entry(input_row, width=6)
        self._steps_entry.insert(0, "1")
        self._steps_entry.pack(side="left")
        self._steps_entry.bind("<KeyRelease>", self._calculate)

        ttk.Label(input_row, text="Pulses:").pack(side="left", padx=(10, 5))
        self._pulses_entry = ttk.Entry(input_row, width=6)
        self._pulses_entry.insert(0, "70")
        self._pulses_entry.pack(side="left")
        self._pulses_entry.bind("<KeyRelease>", self._calculate)

        # Result
        result_row = ttk.Frame(calc_frame)
        result_row.pack(fill="x")

        ttk.Label(result_row, text="Predicted:", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        self._result_label = ttk.Label(result_row, text="~2.5 µm", font=("Consolas", 12), foreground="blue")
        self._result_label.pack(side="left", padx=(10, 0))

        # Reference table
        ref_frame = ttk.LabelFrame(parent, text="Parameter Safety Tiers", padding="10")
        ref_frame.pack(fill="x")

        ref_text = """🟢 Ultra-Safe (Dura Approach)     ~2-4 µm
   Iterations: 1, Steps: 1/1, Pulses: 80/-80
   
🟡 Moderate (Tissue Navigation)   ~10-12 µm
   Iterations: 1, Steps: 5/2, Pulses: 10/-10
   
🔴 Aggressive (SDK Defaults)      ~30 µm
   Iterations: 1, Steps: 10/5, Pulses: 15/-15
   USE WITH CAUTION - High risk of overshoot!

⚠️  Golden Rule: Use 1 iteration per call, check position,
    repeat. A sudden spike in Δw means dura breakthrough."""

        ttk.Label(ref_frame, text=ref_text, justify="left", font=("Consolas", 9)).pack(anchor="w")

    def _calculate(self, event=None) -> None:
        """Calculate and display result."""
        try:
            iterations = int(self._iter_entry.get().strip() or "0")
            steps = int(self._steps_entry.get().strip() or "0")
            pulses = int(self._pulses_entry.get().strip() or "0")
            
            result = calculate_advancement(iterations, steps, pulses)
            self._result_label.configure(text=f"~{result:.1f} µm")
        except ValueError:
            self._result_label.configure(text="-- µm")


class HelpWindow:
    """Help window with usage information."""

    def __init__(self, parent: tk.Tk) -> None:
        """Create help window."""
        self.window = tk.Toplevel(parent)
        self.window.title("Jackhammer Tool - Help")
        self.window.resizable(False, False)
        self.window.transient(parent)
        
        main_frame = ttk.Frame(self.window, padding="15")
        main_frame.pack(fill="both", expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)

        # Overview tab
        overview_frame = ttk.Frame(notebook, padding="10")
        notebook.add(overview_frame, text="Overview")
        overview_text = """WHAT IS JACKHAMMER?

Jackhammer mode creates rapid vibration in the manipulator to help 
the probe break through the dura mater (the tough membrane covering 
the brain).

HOW IT WORKS:

The manipulator oscillates back and forth on the depth axis. Each 
cycle consists of two phases:
  • Phase 1: Forward movement (positive pulses)
  • Phase 2: Backward movement (negative pulses)

IMPORTANT: Jackhammer operates in "open loop" - it doesn't track
position during movement. Always check position after running.

ADVANCEMENT BEHAVIOR:

Advancement is highly sensitive to Steps (S₁) and scales non-linearly
with Iterations (I), while Pulses (P₁) act more like a dampener.

Empirical formula: Δw ≈ 0.3 × I^0.9 × S₁^1.4 × P₁^0.5"""

        ttk.Label(overview_frame, text=overview_text, justify="left").pack(anchor="w")

        # Parameters tab
        params_frame = ttk.Frame(notebook, padding="10")
        notebook.add(params_frame, text="Parameters")
        params_text = """PARAMETER GUIDE:

Iterations (I)
  Number of complete jackhammer cycles. Scales as I^0.9.
  More iterations = more advancement, but diminishing returns.

Phase 1 Steps (S₁) - PRIMARY DRIVER
  Steps in forward phase. Scales as S₁^1.4 (superlinear!).
  This is the main multiplier. Small increases = big effects.

Phase 1 Pulses (P₁) - DAMPENER
  Pulse intensity (1-100). Scales as P₁^0.5 (sublinear).
  Provides raw mechanical force, but effect plateaus.

Phase 2 Steps/Pulses
  Control the retraction phase. Usually less than Phase 1.

PRESETS:

Gentle (Default) - ~4.7 µm per call
  iterations=2, steps=1/1, pulses=70/-70
  Safe for dura approach. May need multiple calls.

Standard - ~23.8 µm per call
  iterations=10, steps=1/1, pulses=100/-100
  SDK defaults. Use with caution near dura."""

        ttk.Label(params_frame, text=params_text, justify="left").pack(anchor="w")

        # Safety tab
        safety_frame = ttk.Frame(notebook, padding="10")
        notebook.add(safety_frame, text="Safety")
        safety_text = """SAFETY WARNINGS:

⚠️  THE GOLDEN RULE FOR DURA APPROACH:
    Do NOT bundle iterations. Use 1 iteration per call,
    check position, repeat. Once you see a sudden spike
    in Δw, you have broken through - STOP IMMEDIATELY.

⚠️  EMERGENCY STOP: Ctrl+Alt+Shift+Q stops all movement.

⚠️  START GENTLE: Always begin with Gentle preset (~4.7 µm).
    Only increase if needed.

⚠️  CHECK POSITION: After each run, verify probe position.
    Movement is unpredictable and history-dependent.

⚠️  MULTIPLE SMALL RUNS: Safer than one aggressive run.

PARAMETER SAFETY TIERS:

🟢 Ultra-Safe (~2-4 µm): I=1, S=1/1, P=80/-80
🟡 Moderate (~10-12 µm): I=1, S=5/2, P=10/-10  
🔴 Aggressive (~30 µm):  I=1, S=10/5, P=15/-15"""

        ttk.Label(safety_frame, text=safety_text, justify="left").pack(anchor="w")

        # Workflow tab
        workflow_frame = ttk.Frame(notebook, padding="10")
        notebook.add(workflow_frame, text="Workflow")
        workflow_text = """RECOMMENDED WORKFLOW:

1. START EPHYS LINK
   Terminal: ephys-link -b -t ump
   Note manipulator IDs shown at startup.

2. CONNECT
   Enter host/port, click Connect.
   Status should turn green.

3. ENTER MANIPULATOR ID
   Type the ID of your target manipulator.

4. CHECK INITIAL POSITION
   Click "Get Position". Note the W (depth) value.

5. RUN JACKHAMMER (ITERATIVE APPROACH)
   a. Use Gentle preset (1-2 iterations)
   b. Click "Run Jackhammer"
   c. Check new position
   d. Calculate Δw (change in depth)
   e. If Δw is small → repeat from (a)
   f. If Δw suddenly spikes → STOP (dura breakthrough!)

6. AFTER BREAKTHROUGH
   Probe is through dura. Continue insertion normally.

TROUBLESHOOTING:
• No movement? → Check connection, try higher pulses
• Too much movement? → Reduce steps first, then iterations
• Inconsistent? → Tissue resistance varies, this is normal"""

        ttk.Label(workflow_frame, text=workflow_text, justify="left").pack(anchor="w")

        ttk.Button(main_frame, text="Close", command=self.window.destroy).pack(pady=(10, 0))

        # Center window
        self.window.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.window.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")


class JackhammerGUI:
    """Main GUI application with tabs."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize application."""
        self.root = root
        self.root.title("Jackhammer Tool")
        self.root.resizable(False, False)

        self._client = EphysLinkClient()
        
        # Track advancement per manipulator
        self._totals: dict[str, float] = {}  # {manipulator_id: total_um}
        self._position_before: Optional[Position] = None

        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Create notebook for tabs
        self._notebook = ttk.Notebook(main_frame)
        self._notebook.pack(fill="both", expand=True)

        # Control tab
        control_frame = ttk.Frame(self._notebook, padding="10")
        self._notebook.add(control_frame, text="Control")

        self._connection = ConnectionFrame(control_frame, self._connect, self._disconnect)
        self._manipulator = ManipulatorFrame(control_frame)
        
        # Create status early for logging
        self._status = StatusLog(control_frame)
        
        self._parameters = ParametersFrame(control_frame, self._status.log)
        self._controls = ControlFrame(control_frame, self._run_jackhammer, self._emergency_stop, self._show_help)
        self._position = PositionFrame(control_frame, self._get_position, self._reset_total)

        # Calculator tab
        calc_frame = ttk.Frame(self._notebook, padding="10")
        self._notebook.add(calc_frame, text="Calculator")
        self._calculator = CalculatorTab(calc_frame)

        # Bind emergency stop keys
        self.root.bind("<Control-Alt-Shift-Q>", lambda e: self._emergency_stop())
        self.root.bind("<Control-Alt-Shift-q>", lambda e: self._emergency_stop())

        # Handle close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Log startup
        self._status.log("Jackhammer Tool started. Click Help for usage guide.")

    def _connect(self) -> None:
        """Connect to server."""
        try:
            port = self._connection.port
        except ValueError:
            messagebox.showerror("Error", "Port must be a number.")
            return

        self._status.log(f"Connecting to {self._connection.host}:{port}...")

        try:
            self._client.connect(self._connection.host, port)
            self._connection.set_connected(True)
            self._controls.set_enabled(True)
            self._position.set_enabled(True)
            self._status.log("Connected successfully.")
        except ConnectionError as e:
            self._status.log(f"Connection failed: {e}")
            messagebox.showerror("Connection Error", str(e))

    def _disconnect(self) -> None:
        """Disconnect from server."""
        self._client.disconnect()
        self._connection.set_connected(False)
        self._controls.set_enabled(False)
        self._position.set_enabled(False)
        self._status.log("Disconnected.")

    def _run_jackhammer(self) -> None:
        """Execute jackhammer."""
        manip_id = self._manipulator.manipulator_id
        if not manip_id:
            messagebox.showerror("Error", "Manipulator ID is required.")
            return

        params = self._parameters.get_params(manip_id)
        if not params:
            return

        if self._manipulator.is_inside_brain:
            if not messagebox.askokcancel(
                "Warning",
                "Probe is marked as inside brain.\n\n"
                "Jackhammer will only move on the depth axis.\n\n"
                "Continue?",
            ):
                return

        # Get position before jackhammer
        try:
            self._position_before = self._client.get_position(manip_id)
        except Exception:
            self._position_before = None

        self._controls.set_enabled(False)
        self._status.log(f"Running jackhammer on manipulator {manip_id}...")

        thread = threading.Thread(target=self._execute, args=(params,))
        thread.start()

    def _execute(self, params: JackhammerParams) -> None:
        """Execute jackhammer in background."""
        try:
            result = self._client.jackhammer(params)
            self.root.after(0, self._handle_result, result)
        except Exception as e:
            self.root.after(0, self._handle_error, str(e))

    def _handle_result(self, result: JackhammerResult) -> None:
        """Handle result in main thread."""
        self._controls.set_enabled(True)
        manip_id = self._manipulator.manipulator_id

        if result.success:
            self._status.log("Jackhammer complete!")
            self._status.log(f"  Final position: {result.position}")
            
            if result.position:
                self._position.update_position(result.position)
                
                # Calculate actual advancement
                if self._position_before is not None:
                    # w is depth, convert mm to µm
                    actual_um = (result.position.w - self._position_before.w) * 1000
                    self._position.update_actual_advancement(actual_um)
                    self._status.log(f"  Actual advancement: {actual_um:+.1f} µm")
                    
                    # Update total for this manipulator
                    if manip_id not in self._totals:
                        self._totals[manip_id] = 0.0
                    self._totals[manip_id] += actual_um
                    self._position.update_total_advancement(self._totals[manip_id])
                    self._status.log(f"  Total advancement: {self._totals[manip_id]:.1f} µm")
                
                self._position_before = None
        else:
            self._status.log(f"Error: {result.error}")
            messagebox.showerror("Jackhammer Error", result.error)

    def _handle_error(self, error: str) -> None:
        """Handle error in main thread."""
        self._controls.set_enabled(True)
        self._status.log(f"Error: {error}")
        messagebox.showerror("Error", error)

    def _get_position(self) -> None:
        """Get and display current position."""
        manip_id = self._manipulator.manipulator_id
        if not manip_id:
            messagebox.showerror("Error", "Manipulator ID is required.")
            return

        try:
            position = self._client.get_position(manip_id)
            self._position.update_position(position)
            self._status.log(f"Position: {position}")
            
            # Show current total for this manipulator
            total = self._totals.get(manip_id, 0.0)
            self._position.update_total_advancement(total)
        except Exception as e:
            self._status.log(f"Get position failed: {e}")
            messagebox.showerror("Error", str(e))

    def _reset_total(self) -> None:
        """Reset total advancement for current manipulator."""
        manip_id = self._manipulator.manipulator_id
        if not manip_id:
            messagebox.showerror("Error", "Manipulator ID is required.")
            return
        
        self._totals[manip_id] = 0.0
        self._position.update_total_advancement(0.0)
        self._position.clear_actual()
        self._status.log(f"Total advancement reset for manipulator {manip_id}.")

    def _emergency_stop(self) -> None:
        """Emergency stop."""
        self._status.log("!!! EMERGENCY STOP !!!")

        manip_id = self._manipulator.manipulator_id
        if not manip_id:
            self._status.log("No manipulator ID specified.")
            return

        if not self._client.is_connected:
            self._status.log("Not connected.")
            return

        try:
            self._client.stop(manip_id)
            self._status.log(f"Stop sent to manipulator {manip_id}.")
        except Exception as e:
            self._status.log(f"Stop failed: {e}")

    def _show_help(self) -> None:
        """Show help window."""
        HelpWindow(self.root)

    def _on_close(self) -> None:
        """Handle window close."""
        self._disconnect()
        self.root.destroy()