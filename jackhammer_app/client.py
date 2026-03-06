"""Client for communicating with Ephys Link server."""

import json
from typing import Optional

from socketio import SimpleClient
from socketio.exceptions import ConnectionError as SIOConnectionError

from .models import JackhammerParams, JackhammerResult


class EphysLinkClient:
    """Client for Ephys Link server communication.
    
    Handles connection management and command execution.
    """

    def __init__(self) -> None:
        """Initialize client (not connected)."""
        self._sio: Optional[SimpleClient] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self._connected

    def connect(self, host: str, port: int) -> None:
        """Connect to Ephys Link server.
        
        Args:
            host: Server hostname.
            port: Server port.
            
        Raises:
            ConnectionError: If connection fails.
        """
        url = f"http://{host}:{port}"
        try:
            self._sio = SimpleClient()
            self._sio.connect(url)
            self._connected = True
        except SIOConnectionError as e:
            self._sio = None
            self._connected = False
            raise ConnectionError(f"Could not connect to {url}: {e}") from e

    def disconnect(self) -> None:
        """Disconnect from server."""
        if self._sio:
            try:
                self._sio.disconnect()
            except Exception:
                pass
            self._sio = None
        self._connected = False

    def jackhammer(self, params: JackhammerParams) -> JackhammerResult:
        """Execute jackhammer command.
        
        Args:
            params: Jackhammer parameters.
            
        Returns:
            Result containing final position or error.
            
        Raises:
            RuntimeError: If not connected.
        """
        if not self._connected or not self._sio:
            raise RuntimeError("Not connected to server.")

        response = self._sio.call("jackhammer", json.dumps(params.to_dict()), timeout=60)
        result = json.loads(response)
        return JackhammerResult.from_dict(result)
    

    # If emergency is pressed. This will stop the current jackhammer operation immediately.
    def abort_jackhammer(self) -> None:
        """Abort closed loop jackhammer."""
        if self._connected and self._sio:
            self._sio.call("abort_jackhammer", "{}")

    def jackhammer_closed_loop(
        self,
        manipulator_id: str,
        target_um: float,
        max_iterations: int = 50,
        phase1_steps: int = 2,
        phase1_pulses: int = 70,
        phase2_steps: int = 2,
        phase2_pulses: int = -70,
    ) -> dict:
        """Execute closed-loop jackhammer command.
        
        Args:
            manipulator_id: Manipulator ID.
            target_um: Target advancement in micrometers.
            max_iterations: Maximum iterations (safety limit).
            phase1_steps: Steps in phase 1.
            phase1_pulses: Pulses in phase 1.
            phase2_steps: Steps in phase 2.
            phase2_pulses: Pulses in phase 2.
            
        Returns:
            Dictionary with position, iterations_used, stop_reason, advancement_um.
            
        Raises:
            RuntimeError: If not connected.
        """
        if not self._connected or not self._sio:
            raise RuntimeError("Not connected to server.")

        params = {
            "manipulator_id": manipulator_id,
            "closed_loop": True,
            "target_um": target_um,
            "max_iterations": max_iterations,
            "phase1_steps": phase1_steps,
            "phase1_pulses": phase1_pulses,
            "phase2_steps": phase2_steps,
            "phase2_pulses": phase2_pulses,
        }
        response = self._sio.call("jackhammer", json.dumps(params), timeout=180)
        return json.loads(response)

    def stop(self, manipulator_id: str) -> None:
        """Send emergency stop command.
        
        Args:
            manipulator_id: Manipulator to stop.
            
        Raises:
            RuntimeError: If not connected.
        """
        if not self._connected or not self._sio:
            raise RuntimeError("Not connected to server.")

        self._sio.call("stop", manipulator_id)

    def get_position(self, manipulator_id: str) -> "Position":
        """Get current manipulator position.
        
        Args:
            manipulator_id: Manipulator ID.
            
        Returns:
            Current position.
            
        Raises:
            RuntimeError: If not connected or error occurs.
        """
        from .models import Position
        
        if not self._connected or not self._sio:
            raise RuntimeError("Not connected to server.")

        response = self._sio.call("get_position", manipulator_id)
        result = json.loads(response)
        
        error = result.get("Error", "")
        if error:
            raise RuntimeError(error)
        
        return Position.from_dict(result.get("Position", {}))