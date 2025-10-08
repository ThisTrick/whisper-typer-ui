# Research: CLI Tool Installation and Background Service Management

**Feature**: 003-cli-tool-installation  
**Date**: 2025-10-08  
**Context**: Enable `uv tool install` installation and cross-platform daemon management

## Research Questions

### 1. How does `uv tool install` work?

**Decision**: Use `pyproject.toml` `[project.scripts]` entry point

**Rationale**:
- `uv tool install` reads `pyproject.toml` and creates isolated environment
- `[project.scripts]` defines CLI command that becomes globally available
- `uv` automatically handles PATH configuration and dependency installation
- Example: `uv tool install whisper-typer-ui --from git+https://github.com/owner/whisper-typer-ui.git`

**Implementation approach**:

```toml
[project.scripts]
whisper-typer = "src.cli:main"
```

**Alternatives considered**:
- Manual setup.py: Rejected (deprecated, uv prefers pyproject.toml)
- Custom installer script: Rejected (adds complexity, uv already handles this)

**Reference**: Similar to spec-kit approach mentioned by user

---

### 2. Cross-Platform Daemon Management

**Decision**: Platform-specific service integration with unified Python wrapper

**Rationale**:
- Each OS has native service management (systemd/launchd/Task Scheduler)
- Python `subprocess` module can interact with all three
- Auto-start requires native service configuration files
- Simplest approach: detect platform and use appropriate native tool

**Implementation strategy**:

**Linux (systemd)**:
- Create `~/.config/systemd/user/whisper-typer.service` unit file
- Commands: `systemctl --user enable/disable/start/stop whisper-typer`
- Service file contains: `ExecStart=whisper-typer daemon` (internal daemon command)

**macOS (launchd)**:
- Create `~/Library/LaunchAgents/com.whisper-typer.plist` file
- Commands: `launchctl load/unload/start/stop ~/Library/LaunchAgents/com.whisper-typer.plist`
- Plist contains: `<string>whisper-typer</string><string>daemon</string>`

**Windows (Task Scheduler)**:
- Use `schtasks /create` to register task
- Commands: `schtasks /run /tn WhisperTyper`, `schtasks /end /tn WhisperTyper`
- Task triggers on user login, runs `whisper-typer daemon`

**Alternatives considered**:
- Python daemon libraries (python-daemon): Rejected (doesn't integrate with OS service managers for auto-start)
- Cross-platform service wrapper (supervisor): Rejected (adds external dependency, increases complexity)
- Direct fork/background: Rejected (no OS integration, manual auto-start configuration)

---

### 3. Process Locking (Single Instance)

**Decision**: PID file with process validation via `psutil`

**Rationale**:
- Simple, cross-platform approach
- PID file prevents duplicate starts
- `psutil.pid_exists()` validates process is actually running (handles stale PID files)
- Lock file location: `~/.whisper-typer/service.pid`

**Implementation**:

```python
import psutil
import os

def acquire_lock():
    pid_file = os.path.expanduser("~/.whisper-typer/service.pid")
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            pid = int(f.read().strip())
        if psutil.pid_exists(pid):
            return False  # Already running
    # Write current PID
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
    return True
```

**Alternatives considered**:
- File locking (fcntl/msvcrt): Rejected (platform-specific APIs, more complex)
- Socket binding: Rejected (requires port management, firewall implications)

---

### 4. Log Rotation Strategy

**Decision**: Daily log overwrite (single log file per day)

**Rationale**:
- Spec clarification: logs stored for one day, next day overwritten
- Simple implementation: check log file date on service start
- Log location: `~/.whisper-typer/logs/service-YYYY-MM-DD.log`
- Current day symlink: `~/.whisper-typer/logs/current.log` → `service-2025-10-08.log`

**Implementation**:

```python
import datetime
import os

def get_log_file():
    log_dir = os.path.expanduser("~/.whisper-typer/logs")
    os.makedirs(log_dir, exist_ok=True)
    today = datetime.date.today().isoformat()
    log_file = os.path.join(log_dir, f"service-{today}.log")
    
    # Delete old log files (keep only today)
    for f in os.listdir(log_dir):
        if f.startswith("service-") and f != f"service-{today}.log":
            os.remove(os.path.join(log_dir, f))
    
    return log_file
```

**Alternatives considered**:
- Python logging.handlers.RotatingFileHandler: Rejected (size-based, not date-based per spec)
- External logrotate: Rejected (requires system configuration, not user-friendly)

---

### 5. Service Crash Recovery

**Decision**: Platform-native restart policies with exponential backoff

**Rationale**:
- Spec clarification: auto-restart max 3 times with exponential backoff
- systemd/launchd/Task Scheduler all support restart policies
- Offload retry logic to OS service manager (simpler than custom implementation)

**Implementation**:

**Linux (systemd)**:

```ini
[Service]
Restart=on-failure
RestartSec=5s
StartLimitBurst=3
StartLimitIntervalSec=60s
```

**macOS (launchd)**:

```xml
<key>KeepAlive</key>
<dict>
    <key>SuccessfulExit</key>
    <false/>
</dict>
<key>ThrottleInterval</key>
<integer>5</integer>
```

**Windows (Task Scheduler)**:

- Use `/V1` task with restart on failure settings
- XML configuration: `<RestartCount>3</RestartCount>`, `<Interval>PT5S</Interval>`

**Alternatives considered**:
- Custom Python retry logic: Rejected (duplicates OS capabilities, more code to maintain)
- No auto-restart: Rejected (doesn't meet spec requirement)

---

### 6. Configuration Preservation During Upgrade

**Decision**: Skip config files during uninstall, `uv` preserves user data

**Rationale**:
- Config location: `~/.whisper-typer/config.yaml` (outside uv install directory)
- `uv tool install --force` overwrites code but not user home directory
- Upgrade workflow: stop service → `uv tool install --force` → notify user to restart

**Implementation**: No special handling needed, config already in user home directory

---

### 7. Daemon Implementation

**Decision**: Hidden `daemon` subcommand that runs main application

**Rationale**:
- Existing `whisper-typer-ui.py` contains application logic
- `daemon` command imports and runs existing code in background
- Service managers call `whisper-typer daemon` (not exposed in `--help` for end users)

**Implementation**:

```python
# src/cli.py
def daemon():
    """Hidden command called by service managers"""
    from src import whisper_typer_ui
    whisper_typer_ui.main()  # Runs existing application

# Service file calls: whisper-typer daemon
```

**Alternatives considered**:
- Separate daemon binary: Rejected (duplicates code, against "don't modify existing code" constraint)
- Direct Python file invocation: Rejected (requires users to know internal paths)

---

## Summary

**Key Technologies**:

- `pyproject.toml [project.scripts]` for CLI entry point
- `psutil` for process management (PID validation, status checking)
- Platform-native service managers (systemd/launchd/Task Scheduler)
- PID file locking at `~/.whisper-typer/service.pid`
- Daily log rotation at `~/.whisper-typer/logs/service-YYYY-MM-DD.log`

**Architecture**: Minimal wrapper layer around existing application code. Four new Python files handle CLI, daemon launching, service management, and process locking. No changes to existing application logic.
