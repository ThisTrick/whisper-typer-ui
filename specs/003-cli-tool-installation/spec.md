# Feature Specification: CLI Tool Installation and Background Service Management

**Feature Branch**: `003-cli-tool-installation`  
**Created**: 2025-10-08  
**Status**: ✅ Completed  
**Completed**: 2025-10-08  
**Input**: User description: "Так, потрібна нова фіччя для вже існуючої програми, яка наразі в нас є. Ця фічf має спростити взагалі встановлення та підтримку інструменту. Так наразі потрібно запускати її через юві вручну, і в тебе ціле вікно терміналу. Але з терміналом крутиться весь час, не закривається. Що я пропоную? По-перше, це встановлення, по прикладу uv tool install specify-cli --from git+https://github.com/github/spec-kit.git. І крім цього пропоную додати можливо CLR-команди, такі як запуск і зупинка бекграунд сервісу, який буде крутитисьна фоні для того, щоб було зручно це все робити, а також щоб ці бекграунд процеси автоматично стартували та менеджерились на всіх платформах, так як рішення кросплатформлене. Рішення має бути так само простим,  не має змінювати наявний код, а лише робити більш доступним його інфраструктуру."

## Clarifications

### Session 2025-10-08

- Q: What should happen to service logs over time? → A: Logs are stored for one day, next day they are overwritten with new logs
- Q: Should the background service automatically restart if it crashes? → A: Yes, auto-restart with exponential backoff, maximum 3 attempts
- Q: What should happen when user installs while another version exists? → A: Auto-upgrade to new version, preserve configuration
- Q: What should happen when user upgrades while service is running? → A: Auto-stop service, upgrade, notify user to restart manually
- Q: What should happen when user uninstalls while service is running? → A: Auto-stop service gracefully, then uninstall everything

## User Scenarios *(mandatory)*

### User Story 1 - One-Command Installation (Priority: P1)

User wants to install the dictation application with a single command without manual dependency management, virtual environment setup, or complex configuration. After installation, the tool is immediately available globally as a command-line utility.

**Why this priority**: Without easy installation, users cannot adopt the tool. This is the foundation for all other features and the minimum viable product.

**Manual Verification**: User runs installation command from terminal, waits for completion, then verifies the tool is available by running `whisper-typer --help` from any directory without additional setup.

**Acceptance Scenarios**:

1. **Given** user has uv installed on their system, **When** user runs installation command (e.g., `uv tool install whisper-typer-ui --from git+https://github.com/[owner]/whisper-typer-ui.git`), **Then** tool installs successfully with all dependencies
2. **Given** installation completes successfully, **When** user opens new terminal window, **Then** `whisper-typer` command is available globally in PATH
3. **Given** tool is installed, **When** user runs `whisper-typer --help`, **Then** available commands and options are displayed
4. **Given** user wants to update the tool, **When** user runs update command, **Then** tool updates to latest version without breaking existing configuration

---

### User Story 2 - Background Service Management (Priority: P2)

User wants to start the dictation service as a background daemon that runs invisibly without keeping a terminal window open. The user can start, stop, and check the status of the service using simple CLI commands.

**Why this priority**: Essential for usability - users shouldn't need to keep a terminal open. This makes the tool practical for daily use.

**Manual Verification**: User runs `whisper-typer start` command, terminal closes or returns immediately, user can use hotkey to activate dictation, then runs `whisper-typer stop` to terminate the background service.

**Acceptance Scenarios**:

1. **Given** tool is installed, **When** user runs `whisper-typer start`, **Then** service starts in background and command returns immediately without blocking terminal
2. **Given** service is running in background, **When** user closes terminal window, **Then** service continues running and responds to hotkey activation
3. **Given** service is running, **When** user runs `whisper-typer status`, **Then** output shows service is active and includes process information
4. **Given** service is running, **When** user runs `whisper-typer stop`, **Then** service terminates gracefully and all background processes exit cleanly
5. **Given** service is not running, **When** user runs `whisper-typer status`, **Then** output indicates service is stopped
6. **Given** service is already running, **When** user runs `whisper-typer start` again, **Then** system detects running instance and reports service is already active without starting duplicate

---

### User Story 3 - Automatic Startup on System Boot (Priority: P3)

User wants the dictation service to start automatically when their computer boots, so they don't have to manually start it every time. The service should integrate with the operating system's native service management.

**Why this priority**: Convenience feature that improves daily workflow, but users can manually start the service if needed. Nice-to-have rather than essential.

**Manual Verification**: User runs `whisper-typer enable`, restarts computer, and verifies service is running after boot without manual intervention.

**Acceptance Scenarios**:

1. **Given** tool is installed, **When** user runs `whisper-typer enable`, **Then** service is configured to start automatically on system boot using platform-native mechanism (systemd on Linux, launchd on macOS, Task Scheduler on Windows)
2. **Given** auto-start is enabled, **When** user reboots their system, **Then** service starts automatically in background after user login
3. **Given** auto-start is enabled, **When** user runs `whisper-typer disable`, **Then** automatic startup is removed and service will not start on next boot
4. **Given** user queries auto-start status, **When** user runs `whisper-typer status`, **Then** output indicates whether auto-start is enabled or disabled

---

### Edge Cases

- What happens when user tries to start service while it's already running?
- What happens when user tries to stop service that's not running?
- What happens when service fails to start due to port conflicts or permission errors?
- What happens when user enables auto-start but lacks system permissions to create startup entries?
- What happens on platforms where native service management is unavailable or restricted?
- What happens when service crashes 3 times and exhausts restart attempts (is user notified)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support installation via `uv tool install whisper-typer-ui --from git+[repository-url]` command
- **FR-002**: Installation MUST make `whisper-typer` command globally available in user's PATH
- **FR-002a**: When installing over existing version, system MUST auto-upgrade and preserve existing configuration files
- **FR-002b**: If service is running during upgrade, system MUST stop service, complete upgrade, and notify user to manually restart service
- **FR-003**: System MUST include CLI commands: `start`, `stop`, `status`, `enable`, `disable`
- **FR-004**: `whisper-typer start` command MUST launch service in background and return terminal control immediately
- **FR-005**: Background service MUST run as a daemon process without visible terminal window
- **FR-006**: `whisper-typer stop` command MUST gracefully terminate all background service processes
- **FR-007**: `whisper-typer status` command MUST report whether service is running or stopped
- **FR-008**: `whisper-typer status` command MUST show process ID and uptime when service is running
- **FR-009**: `whisper-typer enable` command MUST configure service to start automatically on system boot
- **FR-010**: `whisper-typer disable` command MUST remove automatic startup configuration
- **FR-011**: System MUST use platform-native service management mechanisms (systemd on Linux, launchd on macOS, Windows Task Scheduler/Services on Windows)
- **FR-012**: System MUST prevent multiple instances from running simultaneously
- **FR-013**: System MUST provide `--help` option showing all available commands and usage
- **FR-014**: System MUST support `whisper-typer --version` to display installed version
- **FR-015**: CLI commands MUST work consistently across Windows, macOS, and Linux
- **FR-016**: Installation MUST NOT require existing code modifications
- **FR-017**: Service MUST write logs to standard location accessible for troubleshooting
- **FR-018**: Service logs MUST be overwritten daily (previous day's logs are replaced with new logs)
- **FR-019**: System MUST handle missing dependencies gracefully with clear error messages
- **FR-020**: Uninstallation via `uv tool uninstall whisper-typer-ui` MUST remove all installed components cleanly
- **FR-020a**: If service is running during uninstallation, system MUST gracefully stop service before removing components
- **FR-021**: Service MUST respect existing configuration files (hotkey settings, language preferences) from manual launches
- **FR-022**: System MUST detect if service crashed and report status accurately
- **FR-023**: Service logs MUST include timestamps and severity levels (info, warning, error)
- **FR-024**: System MUST provide clear error messages when service fails to start (permissions, port conflicts, missing dependencies)
- **FR-025**: Service MUST automatically restart after crash using exponential backoff strategy with maximum 3 restart attempts
- **FR-026**: After 3 failed restart attempts, service MUST remain stopped until user manually restarts it

### Key Entities

- **CLI Tool**: Globally installed command-line interface exposing installation, service management, and configuration commands
- **Background Service**: Long-running daemon process that handles hotkey monitoring, audio recording, transcription, and text insertion
- **Service Manager**: Platform-specific component that integrates with native OS service management (systemd, launchd, Task Scheduler)
- **Process Lock**: Mechanism preventing multiple service instances from running simultaneously
- **Service Log**: Timestamped record of service events, errors, and status changes for troubleshooting
- **Auto-Start Configuration**: Platform-native configuration ensuring service launches on system boot

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can install the tool with a single command in under 2 minutes (excluding download time)
- **SC-002**: `whisper-typer` command is available globally immediately after installation without shell restart
- **SC-003**: Service starts in background within 3 seconds of `whisper-typer start` command
- **SC-004**: Terminal returns control to user immediately after `start` command (non-blocking)
- **SC-005**: Service continues running after terminal window closes
- **SC-006**: `status` command executes in under 1 second and accurately reports service state
- **SC-007**: `stop` command terminates service within 2 seconds without orphaned processes
- **SC-008**: Auto-start configuration works on all supported platforms (Windows, macOS, Linux)
- **SC-009**: Service auto-starts within 30 seconds of user login after boot when enabled
- **SC-010**: Multiple `start` commands do not create duplicate service instances
- **SC-011**: Existing functionality (hotkey, recording, transcription) remains unchanged from current implementation
- **SC-012**: Installation requires zero manual dependency management or virtual environment setup
- **SC-013**: Service logs are accessible and contain sufficient information for basic troubleshooting
- **SC-014**: Uninstallation removes all components without leaving residual files or configurations
- **SC-015**: Error messages clearly indicate root cause when service fails to start (permissions, dependencies, conflicts)

### Assumptions

- Users have `uv` installed or can install it via standard package managers
- Users have sufficient permissions to install global tools via `uv`
- Existing application code is refactored to support both manual execution and background daemon mode
- Service manager implementations use standard platform APIs (systemd, launchd, Task Scheduler)
- Users running `enable` command have necessary permissions to create system startup entries
- Log files are stored in user-writable locations or standard system log directories
- Service runs with same permissions as the user who started it
- Daily log overwrite prevents disk space issues (only current day's logs are retained)
- Existing configuration files (config.yaml) are preserved and respected by background service
- Installation directory is automatically added to PATH by `uv tool install`
