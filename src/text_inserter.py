"""Text insertion module using clipboard paste (cross-platform)."""

import contextlib
import logging
import platform
import subprocess
import time
from typing import Optional

from pynput.keyboard import Controller, Key, KeyCode


logger = logging.getLogger(__name__)

if platform.system() == "Windows":
    import ctypes
    from ctypes import wintypes

    class _WindowsClipboardHelper:
        """Low-level clipboard + keypress helper that bypasses locale issues."""

        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002
        KEYEVENTF_KEYUP = 0x0002
        VK_CONTROL = 0x11
        VK_V = 0x56

        def __init__(self) -> None:
            self.user32 = ctypes.windll.user32
            self.kernel32 = ctypes.windll.kernel32

        def _open_clipboard(self) -> bool:
            """Try to open the clipboard with a few quick retries."""
            for _ in range(5):
                if self.user32.OpenClipboard(None):
                    return True
                time.sleep(0.01)
            return False

        def read_text(self) -> Optional[str]:
            """Return current clipboard contents as text, if available."""
            if not self._open_clipboard():
                return None
            try:
                handle = self.user32.GetClipboardData(self.CF_UNICODETEXT)
                if not handle:
                    return None
                locked = self.kernel32.GlobalLock(handle)
                if not locked:
                    return None
                try:
                    return ctypes.wstring_at(locked)
                finally:
                    self.kernel32.GlobalUnlock(handle)
            finally:
                self.user32.CloseClipboard()

        def write_text(self, text: str) -> None:
            """Replace clipboard contents with the provided Unicode text."""
            data = text.encode("utf-16-le") + b"\x00\x00"
            handle = self.kernel32.GlobalAlloc(self.GMEM_MOVEABLE, len(data))
            if not handle:
                raise OSError("GlobalAlloc failed")
            locked = self.kernel32.GlobalLock(handle)
            if not locked:
                self.kernel32.GlobalFree(handle)
                raise OSError("GlobalLock failed")
            try:
                ctypes.memmove(locked, data, len(data))
            finally:
                self.kernel32.GlobalUnlock(handle)

            if not self._open_clipboard():
                self.kernel32.GlobalFree(handle)
                raise OSError("OpenClipboard failed")
            try:
                if not self.user32.EmptyClipboard():
                    raise OSError("EmptyClipboard failed")
                if not self.user32.SetClipboardData(self.CF_UNICODETEXT, handle):
                    raise OSError("SetClipboardData failed")
                # Ownership is transferred to the system on success.
                handle = None
            finally:
                self.user32.CloseClipboard()

            if handle is not None:
                self.kernel32.GlobalFree(handle)

        def send_ctrl_v(self) -> None:
            """Issue a literal Ctrl+V keystroke via virtual key codes."""
            self.user32.keybd_event(self.VK_CONTROL, 0, 0, 0)
            self.user32.keybd_event(self.VK_V, 0, 0, 0)
            self.user32.keybd_event(self.VK_V, 0, self.KEYEVENTF_KEYUP, 0)
            self.user32.keybd_event(self.VK_CONTROL, 0, self.KEYEVENTF_KEYUP, 0)
else:
    _WindowsClipboardHelper = None


class TextInserter:
    """Inserts text via clipboard paste (fastest and most reliable for all languages)."""
    
    def __init__(self, typing_speed: int = 100):
        """Initialize text inserter.
        
        Args:
            typing_speed: Characters per second (unused, kept for compatibility)
        """
        self.typing_speed = typing_speed
        self.platform = platform.system()
        self.controller = Controller()
        self._windows_helper = _WindowsClipboardHelper() if self.platform == "Windows" else None
        self._windows_v_key = KeyCode.from_vk(0x56) if self.platform == "Windows" else None
    
    def type_text(self, text: str) -> None:
        """Type text into currently focused application via clipboard paste.
        
        This method uses clipboard paste for all platforms, which is:
        - Fastest (instant vs character-by-character)
        - Most reliable for Unicode (Cyrillic, Chinese, emoji, etc.)
        - Cross-platform compatible
        
        Args:
            text: Text to paste
        """
        if not text:
            return
        
        logger.info(f"Pasting {len(text)} characters via clipboard...")
        
        try:
            if self.platform == "Linux":
                self._paste_linux(text)
            elif self.platform == "Windows":
                self._paste_windows(text)
            elif self.platform == "Darwin":  # macOS
                self._paste_mac(text)
            else:
                logger.warning(f"Unknown platform {self.platform}, using pynput fallback")
                self.controller.type(text)
        except Exception as e:
            logger.warning(f"Clipboard paste failed ({e}), using pynput fallback")
            self.controller.type(text)
        
        logger.info("Text insertion complete")
    
    def _paste_linux(self, text: str) -> None:
        """Paste text via clipboard on Linux using xclip.
        
        Args:
            text: Text to paste
        """
        # Save current clipboard
        original_clipboard = None
        try:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True,
                text=True,
                timeout=0.5
            )
            if result.returncode == 0:
                original_clipboard = result.stdout
        except:
            pass
        
        # Set clipboard with new text
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text.encode('utf-8'),
            check=True,
            timeout=1.0
        )
        
        # Small delay to ensure clipboard is ready
        time.sleep(0.05)
        
        # Paste with Ctrl+V
        with self.controller.pressed(Key.ctrl):
            self.controller.press('v')
            self.controller.release('v')
        
        # Wait for paste to complete
        time.sleep(0.1)
        
        # Restore original clipboard
        if original_clipboard is not None:
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=original_clipboard.encode('utf-8'),
                    timeout=0.5
                )
            except:
                pass
    
    def _paste_windows(self, text: str) -> None:
        """Paste text via clipboard on Windows.
        
        Args:
            text: Text to paste
        """
        helper = self._windows_helper
        if helper is None:
            self._paste_windows_subprocess(text)
            return

        original_clipboard: Optional[str] = None
        try:
            original_clipboard = helper.read_text()
        except OSError:
            pass

        try:
            helper.write_text(text)
            time.sleep(0.03)
            helper.send_ctrl_v()
            time.sleep(0.08)
        finally:
            if original_clipboard is not None:
                with contextlib.suppress(OSError):
                    helper.write_text(original_clipboard)
    
    def _paste_windows_subprocess(self, text: str) -> None:
        """Best-effort clipboard paste using PowerShell fallback on Windows."""
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Set-Clipboard"],
            input=text,
            text=True,
            check=True,
            timeout=2.0
        )
        time.sleep(0.05)
        key_v = self._windows_v_key or 'v'
        with self.controller.pressed(Key.ctrl):
            self.controller.press(key_v)
            self.controller.release(key_v)
        time.sleep(0.1)
    
    def _paste_mac(self, text: str) -> None:
        """Paste text via clipboard on macOS using pbcopy.
        
        Args:
            text: Text to paste
        """
        # Save original clipboard
        original_clipboard = None
        try:
            result = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                text=True,
                timeout=0.5
            )
            if result.returncode == 0:
                original_clipboard = result.stdout
        except:
            pass
        
        # Set clipboard with new text
        subprocess.run(
            ["pbcopy"],
            input=text.encode('utf-8'),
            check=True,
            timeout=1.0
        )
        
        # Paste with Cmd+V
        time.sleep(0.05)
        with self.controller.pressed(Key.cmd):
            self.controller.press('v')
            self.controller.release('v')
        
        # Wait for paste to complete
        time.sleep(0.1)
        
        # Restore original clipboard
        if original_clipboard is not None:
            try:
                subprocess.run(
                    ["pbcopy"],
                    input=original_clipboard.encode('utf-8'),
                    timeout=0.5
                )
            except:
                pass


