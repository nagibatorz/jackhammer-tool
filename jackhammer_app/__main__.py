"""Jackhammer Tool - Standalone GUI for Sensapex manipulator jackhammer mode.

A simple tool for neuroscientists to break through the dura mater
without needing the full Pinpoint application.

Requires Ephys Link server to be running.

Usage:
    python -m jackhammer_app

Emergency Stop:
    Ctrl+Alt+Shift+Q
"""

import tkinter as tk

from .gui import JackhammerGUI


def main() -> None:
    """Application entry point."""
    root = tk.Tk()
    JackhammerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()