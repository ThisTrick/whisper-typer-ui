"""Platform-specific service management for auto-start configuration."""

import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal, Optional


PlatformType = Literal["linux", "darwin", "windows"]


logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages platform-native service integration for auto-start."""
    
    def __init__(self):
        """Initialize service manager with platform detection."""
        system = platform.system().lower()
        if system == "linux":
            self.platform: PlatformType = "linux"
        elif system == "darwin":
            self.platform: PlatformType = "darwin"
        elif system == "windows":
            self.platform: PlatformType = "windows"
        else:
            raise RuntimeError(f"Unsupported platform: {system}")
    
    def enable(self) -> None:
        """Enable auto-start on system boot."""
        if self.platform == "linux":
            self._enable_systemd()
        elif self.platform == "darwin":
            self._enable_launchd()
        elif self.platform == "windows":
            self._enable_task_scheduler()
    
    def disable(self) -> None:
        """Disable auto-start on system boot."""
        if self.platform == "linux":
            self._disable_systemd()
        elif self.platform == "darwin":
            self._disable_launchd()
        elif self.platform == "windows":
            self._disable_task_scheduler()
    
    def get_auto_start_status(self) -> bool:
        """
        Check if auto-start is enabled.
        
        Returns:
            True if auto-start is configured, False otherwise.
        """
        if self.platform == "linux":
            return self._is_systemd_enabled()
        elif self.platform == "darwin":
            return self._is_launchd_enabled()
        elif self.platform == "windows":
            return self._is_task_scheduler_enabled()
        return False
    
    # Linux (systemd) implementation
    
    def _get_systemd_service_file(self) -> Path:
        """Get path to systemd service file."""
        return Path.home() / ".config" / "systemd" / "user" / "whisper-typer.service"
    
    def _enable_systemd(self) -> None:
        """Create and enable systemd user service."""
        service_file = self._get_systemd_service_file()
        service_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Get path to whisper-typer command
        whisper_typer_cmd = self._get_command_path()
        
        # Generate systemd unit file
        unit_content = f"""[Unit]
Description=Whisper Typer Voice Dictation Service
After=default.target

[Service]
Type=simple
ExecStart={whisper_typer_cmd} daemon
Restart=on-failure
RestartSec=5s
StartLimitBurst=3
StartLimitIntervalSec=60s

[Install]
WantedBy=default.target
"""
        
        # Write service file
        service_file.write_text(unit_content)
        
        # Reload systemd and enable service
        try:
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, capture_output=True)
            subprocess.run(["systemctl", "--user", "enable", "whisper-typer.service"], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to enable systemd service: {e.stderr.decode()}")
    
    def _disable_systemd(self) -> None:
        """Disable and remove systemd user service."""
        try:
            subprocess.run(["systemctl", "--user", "disable", "whisper-typer.service"], capture_output=True)
            subprocess.run(["systemctl", "--user", "stop", "whisper-typer.service"], capture_output=True)
        except subprocess.CalledProcessError:
            pass  # Ignore errors if service doesn't exist
        
        # Remove service file
        service_file = self._get_systemd_service_file()
        if service_file.exists():
            service_file.unlink()
    
    def _is_systemd_enabled(self) -> bool:
        """Check if systemd service is enabled."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-enabled", "whisper-typer.service"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0 and "enabled" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    # macOS (launchd) implementation
    
    def _get_launchd_plist_file(self) -> Path:
        """Get path to launchd plist file."""
        return Path.home() / "Library" / "LaunchAgents" / "com.whisper-typer.plist"
    
    def _enable_launchd(self) -> None:
        """Create and load launchd plist."""
        plist_file = self._get_launchd_plist_file()
        plist_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Get path to whisper-typer command
        whisper_typer_cmd = self._get_command_path()
        
        # Generate plist file
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.whisper-typer</string>
    <key>ProgramArguments</key>
    <array>
        <string>{whisper_typer_cmd}</string>
        <string>daemon</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>ThrottleInterval</key>
    <integer>5</integer>
    <key>StandardOutPath</key>
    <string>{Path.home() / '.whisper-typer' / 'logs' / 'launchd-stdout.log'}</string>
    <key>StandardErrorPath</key>
    <string>{Path.home() / '.whisper-typer' / 'logs' / 'launchd-stderr.log'}</string>
</dict>
</plist>
"""
        
        # Write plist file
        plist_file.write_text(plist_content)
        
        # Load plist
        try:
            subprocess.run(["launchctl", "load", str(plist_file)], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to load launchd plist: {e.stderr.decode()}")
    
    def _disable_launchd(self) -> None:
        """Unload and remove launchd plist."""
        plist_file = self._get_launchd_plist_file()
        
        if plist_file.exists():
            try:
                subprocess.run(["launchctl", "unload", str(plist_file)], capture_output=True)
            except subprocess.CalledProcessError:
                pass  # Ignore errors
            
            plist_file.unlink()
    
    def _is_launchd_enabled(self) -> bool:
        """Check if launchd plist exists and is loaded."""
        plist_file = self._get_launchd_plist_file()
        if not plist_file.exists():
            return False
        
        try:
            result = subprocess.run(
                ["launchctl", "list", "com.whisper-typer"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    # Windows (Task Scheduler) implementation

    def _find_pythonw(self) -> Optional[str]:
        """Locate pythonw executable for background execution on Windows."""
        def _supports_cli_import(pythonw_path: str) -> bool:
            try:
                subprocess.run(
                    [pythonw_path, "-c", "import src.cli"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                logger.debug("pythonw candidate %s failed import check", pythonw_path)
                return False
            return True

        candidates = [
            str(Path(sys.executable).with_name("pythonw.exe")),
            shutil.which("pythonw.exe"),
            shutil.which("pythonw"),
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                if _supports_cli_import(candidate):
                    return candidate
                logger.debug("Skipping pythonw candidate %s after failed validation", candidate)
        return None

    def _get_windows_daemon_command(self) -> str:
        """Construct the Task Scheduler command line for daemon start."""
        pythonw_path = self._find_pythonw()
        if pythonw_path:
            return f'"{pythonw_path}" -m src.daemon'
        return f'"{sys.executable}" -m src.daemon'
    
    def _enable_task_scheduler(self) -> None:
        """Create Task Scheduler task for auto-start."""
        command_line = self._get_windows_daemon_command()
        
        # Create task using schtasks command
        task_name = "WhisperTyper"
        
        try:
            # Delete existing task if present
            subprocess.run(
                ["schtasks", "/delete", "/tn", task_name, "/f"],
                capture_output=True
            )
        except subprocess.CalledProcessError:
            pass  # Ignore if task doesn't exist
        
        # Create new task
        try:
            subprocess.run([
                "schtasks", "/create",
                "/tn", task_name,
                "/tr", command_line,
                "/sc", "onlogon",
                "/rl", "limited",
                "/f"
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create Task Scheduler task: {e.stderr.decode()}")
    
    def _disable_task_scheduler(self) -> None:
        """Remove Task Scheduler task."""
        task_name = "WhisperTyper"
        
        try:
            subprocess.run(
                ["schtasks", "/delete", "/tn", task_name, "/f"],
                capture_output=True
            )
        except subprocess.CalledProcessError:
            pass  # Ignore if task doesn't exist
    
    def _is_task_scheduler_enabled(self) -> bool:
        """Check if Task Scheduler task exists."""
        task_name = "WhisperTyper"
        
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/tn", task_name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    # Helper methods
    
    def _get_command_path(self) -> str:
        """
        Get the full path to the whisper-typer command.
        
        Returns:
            Full path to whisper-typer executable/script.
        """
        # Try to find whisper-typer in PATH
        import shutil
        cmd_path = shutil.which("whisper-typer")
        
        if cmd_path:
            return cmd_path
        
        # Fallback: use current Python executable with -m flag
        # This works when installed via uv tool install
        return f"{sys.executable} -m src.cli"
