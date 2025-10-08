# Tasks: CLI Tool Installation and Background Service Management

**Input**: Design documents from `/specs/003-cli-tool-installation/`
**Prerequisites**: plan.md, spec.md (user stories), research.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and manual verification of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

All paths are at repository root:
- `pyproject.toml` - Project configuration with CLI entry point
- `src/` - All Python source files (4 new files, existing files unchanged)
- `README.md` - User documentation update

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project configuration and dependency management

- [ ] T001 Add `psutil` dependency to `pyproject.toml` under `[project.dependencies]`
- [ ] T002 [P] Add `[project.scripts]` entry point in `pyproject.toml`: `whisper-typer = "src.cli:main"`
- [ ] T003 [P] Create log directory structure in `~/.whisper-typer/logs/` (handled in code, not a separate task)

**Checkpoint**: Project configured for `uv tool install` - dependencies and CLI entry point ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create `src/process_lock.py` - Implement PID file locking with `psutil` validation
  - Function: `acquire_lock()` - Creates `~/.whisper-typer/service.pid`, validates existing PID
  - Function: `release_lock()` - Removes PID file on clean shutdown
  - Function: `is_service_running()` - Checks if service PID exists and is alive
- [ ] T005 Create `src/daemon.py` - Implement daemon launcher that wraps existing application
  - Function: `start_daemon()` - Imports and runs existing `whisper-typer-ui.main()` in background
  - Setup daily log rotation (delete old logs, create today's log file)
  - Acquire process lock before starting
  - Handle graceful shutdown signals (SIGTERM, SIGINT)
- [ ] T006 [P] Create `src/service_manager.py` - Platform-specific service integration
  - Class: `ServiceManager` with platform detection (Linux/macOS/Windows)
  - Method: `enable()` - Creates systemd/launchd/Task Scheduler configuration
  - Method: `disable()` - Removes auto-start configuration
  - Method: `get_auto_start_status()` - Returns True/False for auto-start enabled
  - Template generation for service files (systemd unit, launchd plist, Task Scheduler XML)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - One-Command Installation (Priority: P1) 🎯 MVP

**Goal**: Enable single-command installation via `uv tool install` with globally available CLI

**Manual Verification**:

1. Run `uv tool install whisper-typer-ui --from git+[repo-url]`
2. Open new terminal window
3. Run `whisper-typer --help`
4. Verify output shows available commands (start, stop, status, enable, disable)

### Implementation for User Story 1

- [ ] T007 [US1] Create `src/cli.py` - Implement CLI entry point with argument parsing
  - Function: `main()` - Entry point called by `whisper-typer` command
  - Subcommand: `--help` - Display usage information
  - Subcommand: `--version` - Display version from `pyproject.toml`
  - Basic CLI structure using `argparse` (no commands implemented yet, just help/version)
- [ ] T008 [US1] Update `pyproject.toml` - Add project metadata
  - `[project]` section: name, version, description, authors
  - Ensure `[project.scripts]` entry point is correct
  - Verify `dependencies = ["psutil"]`
- [ ] T009 [US1] Test installation locally
  - Run `uv tool install . --force` from repository root
  - Verify `whisper-typer --help` works
  - Verify `whisper-typer --version` displays correct version

**Checkpoint**: At this point, `uv tool install` works and `whisper-typer --help` is functional (MVP foundation ready)

---

## Phase 4: User Story 2 - Background Service Management (Priority: P2)

**Goal**: Enable start/stop/status commands for background daemon management

**Manual Verification**:

1. Run `whisper-typer start`
2. Verify terminal returns immediately (non-blocking)
3. Close terminal window
4. Press hotkey - verify dictation works
5. Run `whisper-typer status` - verify shows "RUNNING" with PID
6. Run `whisper-typer stop` - verify service terminates
7. Run `whisper-typer status` - verify shows "STOPPED"

### Implementation for User Story 2

- [ ] T010 [US2] Implement `start` command in `src/cli.py`
  - Import `daemon.start_daemon()` and `process_lock.is_service_running()`
  - Check if service already running (report and exit if yes)
  - Launch daemon in background using `subprocess.Popen()` with detached process
  - Return immediately to terminal (non-blocking)
- [ ] T011 [US2] Implement `stop` command in `src/cli.py`
  - Import `process_lock.is_service_running()` and read PID file
  - If not running, report "Service not running" and exit
  - Send SIGTERM to PID, wait up to 2 seconds for graceful shutdown
  - If still alive, send SIGKILL
  - Remove PID file
- [ ] T012 [US2] Implement `status` command in `src/cli.py`
  - Import `process_lock.is_service_running()` and read PID file
  - Check if service running, display status (RUNNING/STOPPED)
  - If running: display PID and calculate uptime from process start time (via `psutil.Process(pid).create_time()`)
  - Display auto-start status (call `service_manager.get_auto_start_status()`)
- [ ] T013 [US2] Add daemon subcommand (hidden) in `src/cli.py`
  - Subcommand: `daemon` (not shown in `--help`, used by service managers)
  - Calls `daemon.start_daemon()` directly
  - Used by systemd/launchd/Task Scheduler to start service
- [ ] T014 [US2] Test service lifecycle manually
  - Test `whisper-typer start` → verify background process starts
  - Close terminal → verify service continues running
  - Test hotkey → verify dictation works
  - Test `whisper-typer status` → verify shows correct status
  - Test `whisper-typer stop` → verify graceful shutdown
  - Test duplicate start detection (start when already running)

**Checkpoint**: At this point, User Stories 1 AND 2 are complete - installation and basic service management work

---

## Phase 5: User Story 3 - Automatic Startup on System Boot (Priority: P3)

**Goal**: Enable auto-start configuration via `enable`/`disable` commands

**Manual Verification**:

1. Run `whisper-typer enable`
2. Restart computer
3. After login, run `whisper-typer status`
4. Verify shows "RUNNING" and "Auto-start: Enabled"
5. Run `whisper-typer disable`
6. Run `whisper-typer status`
7. Verify shows "Auto-start: Disabled"

### Implementation for User Story 3

- [ ] T015 [US3] Implement `enable` command in `src/cli.py`
  - Import `service_manager.ServiceManager`
  - Detect platform (Linux/macOS/Windows)
  - Call `service_manager.enable()` to create platform-specific service configuration
  - Display success message with platform-specific details
  - Handle permission errors gracefully
- [ ] T016 [US3] Implement `disable` command in `src/cli.py`
  - Import `service_manager.ServiceManager`
  - Call `service_manager.disable()` to remove auto-start configuration
  - Display success message
  - Handle case where auto-start not configured (no-op)
- [ ] T017 [P] [US3] Implement Linux systemd integration in `src/service_manager.py`
  - Create `~/.config/systemd/user/whisper-typer.service` unit file
  - Template: `ExecStart=whisper-typer daemon`, `Restart=on-failure`, `RestartSec=5s`, `StartLimitBurst=3`
  - Enable via `systemctl --user enable whisper-typer`
  - Disable via `systemctl --user disable whisper-typer`
- [ ] T018 [P] [US3] Implement macOS launchd integration in `src/service_manager.py`
  - Create `~/Library/LaunchAgents/com.whisper-typer.plist` file
  - Template: Launch on login, `KeepAlive` with crash recovery, `ThrottleInterval` 5 seconds
  - Enable via `launchctl load` command
  - Disable via `launchctl unload` command
- [ ] T019 [P] [US3] Implement Windows Task Scheduler integration in `src/service_manager.py`
  - Create task via `schtasks /create` command
  - Configure: trigger on user login, run `whisper-typer daemon`, restart on failure (max 3 times)
  - Enable/disable via `schtasks` commands
  - Handle UAC/permissions gracefully
- [ ] T020 [US3] Test auto-start on all platforms
  - Linux: Run `whisper-typer enable`, reboot, verify service auto-starts
  - macOS: Run `whisper-typer enable`, reboot, verify service auto-starts
  - Windows: Run `whisper-typer enable`, reboot, verify service auto-starts
  - Test `disable` command removes auto-start on all platforms

**Checkpoint**: All user stories complete - installation, service management, and auto-start work on all platforms

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements affecting multiple user stories

- [ ] T021 [P] Update `README.md` with installation instructions
  - Add "Installation" section with `uv tool install` command
  - Add "Usage" section with CLI commands (start/stop/status/enable/disable)
  - Add "Upgrade" section with stop → reinstall → start workflow
  - Add "Uninstallation" section with stop → disable → uninstall workflow
  - Add "Troubleshooting" section referencing log location
- [ ] T022 [P] Add error handling for common scenarios
  - Handle `uv` not installed (installation instructions)
  - Handle microphone permissions denied (system settings instructions)
  - Handle log directory creation failures
  - Handle service file creation permission errors
- [ ] T023 Handle upgrade workflow edge cases
  - Detect running service during upgrade (auto-stop, notify user)
  - Preserve configuration during upgrade (already in `~/.whisper-typer/`)
  - Test `uv tool install --reinstall` workflow
- [ ] T024 Handle uninstall workflow edge cases
  - Detect running service during uninstall (auto-stop)
  - Clean up PID file if stale
  - Option to preserve or remove config directory (keep by default)
- [ ] T025 Validate against quickstart.md scenarios
  - Walk through all quickstart.md examples
  - Verify all manual verification steps pass
  - Verify troubleshooting steps work

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T003) - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (T004-T006)
- **User Story 2 (Phase 4)**: Depends on User Story 1 (T007-T009) - needs CLI foundation
- **User Story 3 (Phase 5)**: Depends on User Story 2 (T010-T014) - needs service management
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 completion - needs CLI entry point and help system
- **User Story 3 (P3)**: Depends on US2 completion - needs service start/stop functionality

### Within Each User Story

- **US1**: T007 → T008 → T009 (sequential)
- **US2**: T010-T013 can be done in parallel [P], then T014 (testing)
- **US3**: T015-T016 depend on T017-T019 platform implementations (can be parallel [P])

### Parallel Opportunities

- **Setup**: T002 and T003 can run in parallel
- **Foundational**: T006 can run in parallel with T004-T005
- **US3**: T017, T018, T019 (platform-specific) can run in parallel if testing on multiple platforms
- **Polish**: T021 and T022 can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Can run together (different files):
Task T004: "Create src/process_lock.py"
Task T006: "Create src/service_manager.py"

# Must wait for both before:
Task T005: "Create src/daemon.py" (uses process_lock)
```

## Parallel Example: User Story 3

```bash
# Platform-specific implementations (if testing on multiple platforms):
Task T017: "Implement Linux systemd integration"
Task T018: "Implement macOS launchd integration"
Task T019: "Implement Windows Task Scheduler integration"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T006) - CRITICAL
3. Complete Phase 3: User Story 1 (T007-T009)
4. **STOP and VALIDATE**: Run `uv tool install`, verify `whisper-typer --help` works
5. Ready for basic installation (no service management yet)

### Recommended Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Verify `uv tool install` works → MVP ready for distribution!
3. Add User Story 2 → Verify service management works → Daily usage enabled
4. Add User Story 3 → Verify auto-start works → Convenience complete
5. Polish phase → Production ready

### Full Feature Delivery

Complete all phases T001-T025 in order for full feature with all user stories and polish.

---

## Total Task Count: 25 tasks

- **Phase 1 (Setup)**: 3 tasks
- **Phase 2 (Foundational)**: 3 tasks
- **Phase 3 (US1)**: 3 tasks
- **Phase 4 (US2)**: 5 tasks
- **Phase 5 (US3)**: 6 tasks
- **Phase 6 (Polish)**: 5 tasks

**Parallel Opportunities**: 8 tasks marked [P] for potential parallelization

**Manual Verification Points**: 3 checkpoints (one per user story) for incremental validation
