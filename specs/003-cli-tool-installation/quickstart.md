# Quickstart: CLI Tool Installation and Background Service Management

**Feature**: 003-cli-tool-installation  
**Audience**: End users installing whisper-typer-ui

## Installation

### Prerequisites

- `uv` package manager installed ([installation guide](https://github.com/astral-sh/uv))
- Git (for installing from repository)

### Install Command

```bash
uv tool install whisper-typer-ui --from git+https://github.com/[owner]/whisper-typer-ui.git
```

**What this does**:

- Downloads and installs whisper-typer-ui in isolated environment
- Makes `whisper-typer` command globally available
- Installs all dependencies automatically
- No manual virtual environment or dependency management needed

**Verification**:

```bash
whisper-typer --help
```

Expected output: List of available commands (start, stop, status, enable, disable)

---

## Basic Usage

### Start Background Service

```bash
whisper-typer start
```

**What happens**:

- Service starts in background as daemon process
- Terminal returns immediately (non-blocking)
- Hotkey activation now works globally
- Service continues running after terminal closes

**Verification**:

- Close terminal window
- Press configured hotkey
- UI should appear and recording should work

### Check Service Status

```bash
whisper-typer status
```

**Output when running**:

```text
Service Status: RUNNING
Process ID: 12345
Uptime: 2 hours 15 minutes
Auto-start: Enabled
```

**Output when stopped**:

```text
Service Status: STOPPED
Auto-start: Disabled
```

### Stop Service

```bash
whisper-typer stop
```

**What happens**:

- Service terminates gracefully
- All background processes exit cleanly
- Hotkey no longer responds

**Verification**:

```bash
whisper-typer status
# Should show: Service Status: STOPPED
```

---

## Auto-Start Configuration

### Enable Auto-Start (Launch on Boot)

```bash
whisper-typer enable
```

**What happens**:

- Service configured to start automatically when you log in
- Uses platform-native service management:
  - Linux: systemd user service
  - macOS: LaunchAgent
  - Windows: Task Scheduler
- Next reboot: service starts automatically

**Verification**:

1. Run `whisper-typer enable`
2. Restart computer
3. After login, run `whisper-typer status`
4. Should show: `Service Status: RUNNING` and `Auto-start: Enabled`

### Disable Auto-Start

```bash
whisper-typer disable
```

**What happens**:

- Removes automatic startup configuration
- Service continues running until manually stopped or next reboot
- Next reboot: service will NOT start automatically

---

## Upgrade

### Update to Latest Version

```bash
whisper-typer stop                # Stop running service
uv tool install whisper-typer-ui --from git+https://github.com/[owner]/whisper-typer-ui.git --reinstall
whisper-typer start              # Restart with new version
```

**What happens**:

- Service stops gracefully
- New version installed
- Configuration preserved (hotkey settings, language preferences)
- User manually restarts service

**Note**: If service is running during upgrade, it will be automatically stopped, but you must manually restart it.

---

## Uninstallation

```bash
whisper-typer stop                # Stop service if running
whisper-typer disable            # Remove auto-start configuration
uv tool uninstall whisper-typer-ui
```

**What happens**:

- Service stops gracefully
- Auto-start removed
- Application removed
- Configuration files remain in `~/.whisper-typer/` (manual deletion if desired)

---

## Troubleshooting

### Service Won't Start

**Check logs**:

```bash
cat ~/.whisper-typer/logs/service-$(date +%Y-%m-%d).log
```

**Common issues**:

- **Microphone permissions denied**: Grant permissions in system settings
- **Another instance running**: Check `whisper-typer status`, stop if needed
- **Missing dependencies**: Reinstall with `uv tool install --reinstall`

### Hotkey Not Working

1. Check service status: `whisper-typer status`
2. If stopped, start it: `whisper-typer start`
3. Check configuration: `cat ~/.whisper-typer/config.yaml`
4. Verify hotkey not conflicting with other applications

### Service Crashes Repeatedly

Service automatically restarts up to 3 times with exponential backoff. If crashes persist:

1. Check today's log: `~/.whisper-typer/logs/service-$(date +%Y-%m-%d).log`
2. Stop service: `whisper-typer stop`
3. Check for conflicting applications
4. Reinstall if needed

---

## Configuration

Configuration file location: `~/.whisper-typer/config.yaml`

Edit this file to change:

- Hotkey combination
- Primary language for transcription
- Other application settings

**After editing config**:

```bash
whisper-typer stop
whisper-typer start
```

Service must be restarted for changes to take effect.

---

## File Locations

- **Configuration**: `~/.whisper-typer/config.yaml`
- **Logs**: `~/.whisper-typer/logs/service-YYYY-MM-DD.log`
- **PID lock file**: `~/.whisper-typer/service.pid`
- **Service files** (auto-managed):
  - Linux: `~/.config/systemd/user/whisper-typer.service`
  - macOS: `~/Library/LaunchAgents/com.whisper-typer.plist`
  - Windows: Task Scheduler entry "WhisperTyper"

**Note**: Logs are kept for current day only. Previous day's logs are automatically deleted.
