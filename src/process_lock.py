"""Process lock management using PID file with psutil validation."""

import os
import psutil


def _get_pid_file_path() -> str:
    """Get the path to the PID file."""
    lock_dir = os.path.expanduser("~/.whisper-typer")
    os.makedirs(lock_dir, exist_ok=True)
    return os.path.join(lock_dir, "service.pid")


def acquire_lock() -> bool:
    """
    Acquire process lock by creating PID file.
    
    Returns:
        True if lock acquired successfully, False if service already running.
    """
    pid_file = _get_pid_file_path()
    
    # Check if PID file exists
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Validate if process is actually running
            if psutil.pid_exists(pid):
                try:
                    # Double-check it's our process (not reused PID)
                    process = psutil.Process(pid)
                    # If we can get process info, it's likely running
                    if process.is_running():
                        return False  # Service already running
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process doesn't exist or we can't access it
                    # Treat as stale PID file
                    pass
        except (ValueError, FileNotFoundError):
            # Invalid PID file, treat as stale
            pass
    
    # Write current PID
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except IOError as e:
        raise RuntimeError(f"Failed to create PID file: {e}")


def release_lock() -> None:
    """Release process lock by removing PID file."""
    pid_file = _get_pid_file_path()
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
    except OSError:
        # Ignore errors during cleanup
        pass


def is_service_running() -> tuple[bool, int | None]:
    """
    Check if service is currently running.
    
    Returns:
        Tuple of (is_running, pid). If not running, pid is None.
    """
    pid_file = _get_pid_file_path()
    
    if not os.path.exists(pid_file):
        return False, None
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Validate if process is actually running
        if psutil.pid_exists(pid):
            try:
                process = psutil.Process(pid)
                if process.is_running():
                    return True, pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Stale PID file
        return False, None
    except (ValueError, FileNotFoundError):
        # Invalid or missing PID file
        return False, None


def get_service_pid() -> int | None:
    """
    Get the PID of the running service.
    
    Returns:
        PID if service is running, None otherwise.
    """
    running, pid = is_service_running()
    return pid if running else None
