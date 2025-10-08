"""Global hotkey manager for Whisper Typer UI."""

from typing import Callable

from pynput import keyboard


class HotkeyManager:
    """Manages global hotkey registration and listening."""
    
    def __init__(self, hotkey_combination: str):
        """Initialize hotkey manager.
        
        Args:
            hotkey_combination: Hotkey in pynput format (e.g., "<ctrl>+<alt>+space")
            
        Raises:
            ValueError: If hotkey_combination cannot be parsed
        """
        self.hotkey_combination = hotkey_combination
        self.callback: Callable[[], None] | None = None
        self._listener: keyboard.GlobalHotKeys | None = None
        
        # Validate hotkey format by attempting to parse it
        try:
            keyboard.HotKey.parse(hotkey_combination)
        except Exception as e:
            raise ValueError(f"Invalid hotkey combination '{hotkey_combination}': {e}")
    
    def register(self, callback: Callable[[], None]) -> None:
        """Register callback function to be invoked when hotkey is pressed.
        
        Args:
            callback: Function with no parameters, no return value
        """
        self.callback = callback
    
    def start(self) -> None:
        """Start listening for hotkey presses (blocking call).
        
        This method blocks until stop() is called or the application exits.
        """
        if self.callback is None:
            raise RuntimeError("No callback registered. Call register() first.")
        
        # Create GlobalHotKeys listener with our hotkey
        hotkey_dict = {self.hotkey_combination: self.callback}
        self._listener = keyboard.GlobalHotKeys(hotkey_dict)
        
        # Start listener (blocking)
        self._listener.start()
        self._listener.join()  # Block until stopped
    
    def stop(self) -> None:
        """Stop hotkey listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None
