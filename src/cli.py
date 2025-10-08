"""CLI entry point for whisper-typer command."""

import argparse
import os
import signal
import subprocess
import sys
import time
from importlib.metadata import version, PackageNotFoundError

from src import process_lock, daemon, service_manager


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
        print(f"Service is already running (PID: {pid})")
        sys.exit(1)
    
    # Launch daemon in background
    try:
        # Get the whisper-typer executable path
        import shutil
        whisper_typer_cmd = shutil.which("whisper-typer")
        if not whisper_typer_cmd:
            print("ERROR: whisper-typer command not found in PATH")
            sys.exit(1)
        
        # Start daemon as detached process
        if os.name == 'nt':  # Windows
            subprocess.Popen(
                [whisper_typer_cmd, "daemon"],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:  # Unix-like (Linux, macOS)
            subprocess.Popen(
                [whisper_typer_cmd, "daemon"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        
        # Give it a moment to start
        time.sleep(0.5)
        
        # Verify it started
        running, pid = process_lock.is_service_running()
        if running:
            print(f"Service started successfully (PID: {pid})")
        else:
            print("Service failed to start. Check logs at ~/.whisper-typer/logs/")
            sys.exit(1)
    except Exception as e:
        print(f"Error starting service: {e}")
        sys.exit(1)


def cmd_stop() -> None:
    """Stop the background service."""
    running, pid = process_lock.is_service_running()
    
    if not running:
        print("Service is not running")
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
                print("Service stopped successfully")
                return
        
        # If still running, force kill
        if os.name != 'nt':
            os.kill(pid, signal.SIGKILL)
        
        print("Service stopped (forced)")
    except ProcessLookupError:
        # Process already died
        process_lock.release_lock()
        print("Service stopped")
    except Exception as e:
        print(f"Error stopping service: {e}")
        sys.exit(1)


def cmd_status() -> None:
    """Show service status."""
    running, pid = process_lock.is_service_running()
    
    if running:
        print(f"Service Status: RUNNING")
        print(f"Process ID: {pid}")
        
        # Calculate uptime
        try:
            import psutil
            process = psutil.Process(pid)
            create_time = process.create_time()
            uptime_seconds = time.time() - create_time
            
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            if hours > 0:
                print(f"Uptime: {hours} hours {minutes} minutes")
            else:
                print(f"Uptime: {minutes} minutes")
        except Exception:
            # If uptime calculation fails, just skip it
            pass
    else:
        print("Service Status: STOPPED")
    
    # Show auto-start status
    try:
        manager = service_manager.ServiceManager()
        auto_start = manager.get_auto_start_status()
        print(f"Auto-start: {'Enabled' if auto_start else 'Disabled'}")
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
            print("Auto-start is already enabled")
            sys.exit(0)
        
        # Enable auto-start
        sm.enable()
        print("✓ Auto-start enabled successfully")
        print("The service will start automatically on system boot")
        
    except PermissionError as e:
        print(f"ERROR: Permission denied - {e}")
        print("Try running with appropriate privileges")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to enable auto-start - {e}")
        sys.exit(1)


def cmd_disable() -> None:
    """Disable auto-start on system boot."""
    try:
        sm = service_manager.ServiceManager()
        
        # Check current status
        if not sm.get_auto_start_status():
            print("Auto-start is already disabled")
            sys.exit(0)
        
        # Check if service is running - warn but don't prevent
        running, pid = process_lock.is_service_running()
        if running:
            print(f"WARNING: Service is currently running (PID: {pid})")
            print("Disabling auto-start will not stop the current session")
            print("Use 'whisper-typer stop' to stop the service now")
        
        # Disable auto-start
        sm.disable()
        print("✓ Auto-start disabled successfully")
        print("The service will no longer start automatically on system boot")
        
    except PermissionError as e:
        print(f"ERROR: Permission denied - {e}")
        print("Try running with appropriate privileges")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to disable auto-start - {e}")
        sys.exit(1)


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
    elif args.command == "daemon":
        cmd_daemon()


if __name__ == "__main__":
    main()
