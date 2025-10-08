"""Daemon launcher that wraps existing application with log rotation."""

import datetime
import os
import signal
import sys
import logging
from pathlib import Path

from src import process_lock


def _setup_logging() -> str:
    """
    Setup daily log rotation and configure logging.
    
    Returns:
        Path to today's log file.
    """
    log_dir = Path.home() / ".whisper-typer" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    today = datetime.date.today().isoformat()
    log_file = log_dir / f"service-{today}.log"
    
    # Delete old log files (keep only today)
    for old_log in log_dir.glob("service-*.log"):
        if old_log.name != f"service-{today}.log":
            try:
                old_log.unlink()
            except OSError:
                # Ignore errors during cleanup
                pass
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)  # Also log to stdout for debugging
        ]
    )
    
    return str(log_file)


def _handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    logging.info(f"Received signal {signum}, shutting down gracefully...")
    process_lock.release_lock()
    sys.exit(0)


def start_daemon() -> None:
    """
    Start the daemon service.
    
    This function:
    1. Sets up daily log rotation
    2. Acquires process lock
    3. Registers signal handlers
    4. Imports and runs existing application
    """
    # Setup logging first
    log_file = _setup_logging()
    logging.info(f"Starting whisper-typer daemon (log file: {log_file})")
    
    # Acquire process lock
    if not process_lock.acquire_lock():
        logging.error("Service is already running")
        sys.exit(1)
    
    logging.info(f"Acquired process lock (PID: {os.getpid()})")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
    
    try:
        # Import and run existing application
        # Note: Using importlib to import file with dashes in name
        import importlib.util
        
        # Determine the path to whisper-typer-ui.py
        src_dir = os.path.dirname(os.path.abspath(__file__))
        main_file = os.path.join(src_dir, "whisper-typer-ui.py")
        
        # Load module dynamically
        spec = importlib.util.spec_from_file_location("whisper_typer_ui", main_file)
        whisper_typer_ui = importlib.util.module_from_spec(spec)
        
        logging.info("Starting whisper-typer-ui application...")
        spec.loader.exec_module(whisper_typer_ui)
        whisper_typer_ui.main()
    except Exception as e:
        logging.error(f"Application crashed: {e}", exc_info=True)
        process_lock.release_lock()
        sys.exit(1)
    finally:
        # Ensure lock is released on exit
        process_lock.release_lock()
        logging.info("Daemon stopped")


if __name__ == "__main__":
    start_daemon()
