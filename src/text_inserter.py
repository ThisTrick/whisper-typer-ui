"""Text insertion module using clipboard paste (cross-platform)."""

import platform
import subprocess
import time
from pynput.keyboard import Controller, Key


class TextInserter:
    """Inserts text via clipboard paste (fastest and most reliable for all languages)."""
    
    def __init__(self, typing_speed: int = 100):
        """Initialize text inserter.
        
        Args:
            typing_speed: Characters per second (unused, kept for compatibility)
        """
        self.typing_speed = typing_speed
        self.controller = Controller()
        self.platform = platform.system()
    
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
        
        print(f"Pasting {len(text)} characters via clipboard...")
        
        try:
            if self.platform == "Linux":
                self._paste_linux(text)
            elif self.platform == "Windows":
                self._paste_windows(text)
            elif self.platform == "Darwin":  # macOS
                self._paste_mac(text)
            else:
                print(f"Warning: Unknown platform {self.platform}, using pynput fallback")
                self.controller.type(text)
        except Exception as e:
            print(f"Warning: Clipboard paste failed ({e}), using pynput fallback")
            self.controller.type(text)
        
        print("Text insertion complete")
    
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
        try:
            import win32clipboard
            
            # Save original clipboard
            original_clipboard = None
            try:
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    original_clipboard = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
            except:
                pass
            
            # Set clipboard with new text
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            
            # Paste with Ctrl+V
            time.sleep(0.05)
            with self.controller.pressed(Key.ctrl):
                self.controller.press('v')
                self.controller.release('v')
            
            # Wait for paste to complete
            time.sleep(0.1)
            
            # Restore original clipboard
            if original_clipboard is not None:
                try:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(original_clipboard, win32clipboard.CF_UNICODETEXT)
                    win32clipboard.CloseClipboard()
                except:
                    pass
                    
        except ImportError:
            # pywin32 not available, try using subprocess with PowerShell
            self._paste_windows_powershell(text)
    
    def _paste_windows_powershell(self, text: str) -> None:
        """Paste text via clipboard on Windows using PowerShell (fallback).
        
        Args:
            text: Text to paste
        """
        # Set clipboard using PowerShell
        subprocess.run(
            ["powershell", "-command", f"Set-Clipboard -Value '{text}'"],
            check=True,
            timeout=2.0
        )
        
        # Paste with Ctrl+V
        time.sleep(0.05)
        with self.controller.pressed(Key.ctrl):
            self.controller.press('v')
            self.controller.release('v')
        
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


