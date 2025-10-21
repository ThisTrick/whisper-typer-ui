"""CLI entry point for whisper-typer command."""

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import List, Optional

import shutil

from src import process_lock, daemon, service_manager, config_manager


_LOGGING_CONFIGURED = False


def _configure_logging() -> None:
    """Configure root logging once for CLI commands."""
    global _LOGGING_CONFIGURED
    if not _LOGGING_CONFIGURED:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        _LOGGING_CONFIGURED = True


_configure_logging()


logger = logging.getLogger(__name__)


def _find_pythonw_executable() -> Optional[str]:
    """Return pythonw.exe path when available (Windows only)."""
    candidates = [
        shutil.which("pythonw.exe"),
        shutil.which("pythonw"),
        str(Path(sys.executable).with_name("pythonw.exe")),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _build_windows_launch_cmd(default_cli: Optional[str]) -> List[str]:
    """Build a background launch command for Windows that hides the console."""
    pythonw_path = _find_pythonw_executable()
    if pythonw_path:
        return [pythonw_path, "-m", "src.daemon"]
    if default_cli:
        return [default_cli, "daemon"]
    # Fall back to python executable if everything else fails
    return [sys.executable, "-m", "src.cli", "daemon"]


def get_version() -> str:
    """Get package version from metadata."""
    try:
        return version("whisper-typer-ui")
    except PackageNotFoundError:
        return "unknown"


def cmd_start() -> None:
    """Start the background service."""
    # Check if already running
    running, pid = process_lock.is_service_running()
    if running:
        logger.info(f"Service is already running (PID: {pid})")
        sys.exit(1)
    
    # Launch daemon in background
    try:
        # Get the whisper-typer executable path if available (installed via uv/pip)
        whisper_typer_cmd = shutil.which("whisper-typer")
        
        # Start daemon as detached process
        if os.name == 'nt':  # Windows
            launch_cmd = _build_windows_launch_cmd(whisper_typer_cmd)
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | subprocess.CREATE_NEW_PROCESS_GROUP
            creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
            startupinfo = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
            startupinfo.wShowWindow = 0  # type: ignore[attr-defined]
            env = os.environ.copy()
            env.setdefault("WHISPER_TYPER_HIDE_CONSOLE", "1")
            env.setdefault("PYTHONUNBUFFERED", "1")
            subprocess.Popen(
                launch_cmd,
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
                startupinfo=startupinfo,
                env=env,
            )
        else:  # Unix-like (Linux, macOS)
            if not whisper_typer_cmd:
                logger.error("whisper-typer command not found in PATH")
                sys.exit(1)
            subprocess.Popen(
                [whisper_typer_cmd, "daemon"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
        
        # Give it a moment to start
        time.sleep(0.5)
        
        # Verify it started
        running, pid = process_lock.is_service_running()
        if running:
            logger.info(f"Service started successfully (PID: {pid})")
        else:
            logger.error("Service failed to start. Check logs at ~/.whisper-typer/logs/")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting service: {e}")
        sys.exit(1)


def cmd_stop() -> None:
    """Stop the background service."""
    running, pid = process_lock.is_service_running()
    
    if not running:
        logger.info("Service is not running")
        sys.exit(0)
    
    try:
        # Send SIGTERM for graceful shutdown
        if os.name == 'nt':  # Windows
            # Windows doesn't support SIGTERM, use taskkill
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True, capture_output=True)
        else:  # Unix-like
            os.kill(pid, signal.SIGTERM)
        
        # Wait up to 2 seconds for graceful shutdown
        for _ in range(20):
            time.sleep(0.1)
            if not process_lock.is_service_running()[0]:
                logger.info("Service stopped successfully")
                return
        
        # If still running, force kill
        if os.name != 'nt':
            os.kill(pid, signal.SIGKILL)
        
        logger.info("Service stopped (forced)")
    except ProcessLookupError:
        # Process already died
        process_lock.release_lock()
        logger.info("Service stopped")
    except Exception as e:
        logger.error(f"Error stopping service: {e}")
        sys.exit(1)


def cmd_status() -> None:
    """Show service status."""
    running, pid = process_lock.is_service_running()
    
    if running:
        logger.info(f"Service Status: RUNNING")
        logger.info(f"Process ID: {pid}")
        
        # Calculate uptime
        try:
            import psutil
            process = psutil.Process(pid)
            create_time = process.create_time()
            uptime_seconds = time.time() - create_time
            
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            if hours > 0:
                logger.info(f"Uptime: {hours} hours {minutes} minutes")
            else:
                logger.info(f"Uptime: {minutes} minutes")
        except Exception:
            # If uptime calculation fails, just skip it
            pass
    else:
        logger.info("Service Status: STOPPED")
    
    # Show auto-start status
    try:
        manager = service_manager.ServiceManager()
        auto_start = manager.get_auto_start_status()
        logger.info(f"Auto-start: {'Enabled' if auto_start else 'Disabled'}")
    except Exception:
        # If we can't check auto-start status, skip it
        pass


def cmd_daemon() -> None:
    """Run daemon (hidden command for service managers)."""
    daemon.start_daemon()


def cmd_enable() -> None:
    """Enable auto-start on system boot."""
    try:
        sm = service_manager.ServiceManager()
        
        # Check current status
        if sm.get_auto_start_status():
            logger.info("Auto-start is already enabled")
            sys.exit(0)
        
        # Enable auto-start
        sm.enable()
        logger.info("✓ Auto-start enabled successfully")
        logger.info("The service will start automatically on system boot")
        
    except PermissionError as e:
        logger.error(f"Permission denied - {e}")
        logger.error("Try running with appropriate privileges")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to enable auto-start - {e}")
        sys.exit(1)


def cmd_disable() -> None:
    """Disable auto-start on system boot."""
    try:
        sm = service_manager.ServiceManager()
        
        # Check current status
        if not sm.get_auto_start_status():
            logger.info("Auto-start is already disabled")
            sys.exit(0)
        
        # Check if service is running - warn but don't prevent
        running, pid = process_lock.is_service_running()
        if running:
            logger.warning(f"Service is currently running (PID: {pid})")
            logger.warning("Disabling auto-start will not stop the current session")
            logger.warning("Use 'whisper-typer stop' to stop the service now")
        
        # Disable auto-start
        sm.disable()
        logger.info("✓ Auto-start disabled successfully")
        logger.info("The service will no longer start automatically on system boot")
        
    except PermissionError as e:
        logger.error(f"Permission denied - {e}")
        logger.error("Try running with appropriate privileges")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to disable auto-start - {e}")
        sys.exit(1)


def cmd_config(args: argparse.Namespace) -> None:
    """Handle config subcommands."""
    if args.config_action == "edit":
        config_manager.open_config_in_editor()
    elif args.config_action == "show":
        config_manager.show_config()
    elif args.config_action == "path":
        config_path = config_manager.ensure_config_exists()
        logger.info(str(config_path))
    elif args.config_action == "reset":
        config_manager.reset_config()
    elif args.config_action == "validate":
        is_valid = config_manager.validate_config()
        sys.exit(0 if is_valid else 1)
    else:
        # Default: show path and basic help
        config_path = config_manager.ensure_config_exists()
        logger.info(f"Configuration file: {config_path}")
        logger.info("Available commands:")
        logger.info("  whisper-typer config edit     - Edit configuration in your default editor")
        logger.info("  whisper-typer config show     - Display current configuration")
        logger.info("  whisper-typer config path     - Show configuration file path")
        logger.info("  whisper-typer config reset    - Reset to default configuration")
        logger.info("  whisper-typer config validate - Validate configuration file")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="whisper-typer",
        description="Cross-platform voice dictation desktop application",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # start command
    subparsers.add_parser(
        "start",
        help="Start the background service"
    )
    
    # stop command
    subparsers.add_parser(
        "stop",
        help="Stop the background service"
    )
    
    # status command
    subparsers.add_parser(
        "status",
        help="Show service status"
    )
    
    # enable command
    subparsers.add_parser(
        "enable",
        help="Enable auto-start on system boot"
    )
    
    # disable command
    subparsers.add_parser(
        "disable",
        help="Disable auto-start on system boot"
    )
    
    # config command
    config_parser = subparsers.add_parser(
        "config",
        help="Manage configuration file"
    )
    config_parser.add_argument(
        "config_action",
        nargs="?",
        choices=["edit", "show", "path", "reset", "validate"],
        help="Configuration action (edit/show/path/reset/validate)"
    )
    
    # daemon command (hidden - used by service managers)
    subparsers.add_parser(
        "daemon",
        help=argparse.SUPPRESS  # Hidden from help
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # Command handlers
    if args.command == "start":
        cmd_start()
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "status":
        cmd_status()
    elif args.command == "enable":
        cmd_enable()
    elif args.command == "disable":
        cmd_disable()
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "daemon":
        cmd_daemon()


if __name__ == "__main__":
    main()
