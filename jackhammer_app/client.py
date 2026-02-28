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

        response = self._sio.call("jackhammer", json.dumps(params.to_dict()))
        result = json.loads(response)
        return JackhammerResult.from_dict(result)

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