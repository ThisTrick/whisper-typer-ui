# Implementation Plan: Voice Dictation Application

**Branch**: `001-cross-platform-dictation` | **Date**: 2025-10-08 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-cross-platform-dictation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Cross-platform voice dictation desktop application activated via global hotkey. User presses hotkey → microphone starts recording → circular UI overlay appears in bottom-right corner with pulsating animation → user stops recording (click or hotkey) → faster-whisper transcribes audio locally → transcribed text inserted via keyboard emulation into previously focused text field. Emphasis on speed, simplicity, and performance using tkinter for UI and faster-whisper for offline transcription.

## Technical Context

**Language/Version**: Python 3.11+ (async support, mature cross-platform libraries)  
**Primary Dependencies**: faster-whisper (transcription), tkinter (UI), pynput (keyboard emulation), sounddevice (audio recording), pynput (global hotkey), PyInstaller (packaging)  
**Storage**: N/A (no persistence - FR-026, FR-027)  
**Testing**: Manual verification only (Constitution Principle III)  
**Target Platform**: Windows 10+, macOS 11+, Linux (Ubuntu 20.04+, X11/Wayland)  
**Project Type**: Single desktop application  
**Performance Goals**: <1s hotkey activation, <10s transcription for 30s audio, <100MB memory baseline, <500MB during transcription  
**Constraints**: Offline-only (no internet required), fixed 5-10s processing time for 30s audio (SC-002), 95% success rate (SC-003)  
**Scale/Scope**: Single-user desktop utility, ~2000 LOC estimated, 3 main modules (hotkey, recording, transcription)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Simplicity First**: Single Python process, direct library usage, no frameworks, flat module structure
- [x] **User Installation Priority**: PyInstaller single executable, no manual dependencies, platform-specific installers
- [x] **No Automated Testing**: Manual verification only per spec and constitution
- [x] **Minimal Documentation**: README with installation + usage only
- [x] **Dependency Minimization**: 5 core dependencies (faster-whisper, tkinter, pynput, sounddevice, PyInstaller), all essential
- [x] **Cross-Platform**: Python + tkinter native on all platforms, pynput handles platform keyboard differences


## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── whisper-typer-ui.py  # Entry point: initialize app, start hotkey listener
├── hotkey_manager.py    # Global hotkey registration (pynput.keyboard)
├── audio_recorder.py    # Audio capture via sounddevice
├── transcriber.py       # faster-whisper wrapper, model loading
├── text_inserter.py     # Keyboard emulation via pynput
├── ui_overlay.py        # Tkinter circular overlay with animations
├── config.py            # Load primary language, hotkey from config file
└── utils.py             # Shared helpers (icon changes, error display)

assets/
├── microphone.png       # Microphone icon for UI
└── processing.png       # Processing icon for transcription state

config.yaml              # User-editable: primary_language, hotkey
README.md                # Installation + usage instructions
pyproject.toml           # uv dependency management
.python-version          # Python version for uv
build.py                 # PyInstaller build script for all platforms
```

**Structure Decision**: Single project structure chosen because this is a standalone desktop application with no backend/frontend separation. All modules live in `src/` with flat organization. No tests directory per Constitution Principle III.

## Complexity Tracking

No constitution violations. All design decisions align with principles:

- **Simplicity First**: Single Python process, flat module structure, direct library usage
- **No Automated Testing**: Manual verification only
- **Minimal Documentation**: README + quickstart.md only
- **User Installation Priority**: PyInstaller single executable with bundled dependencies
- **Dependency Minimization**: 5 core runtime dependencies (all essential)
- **Cross-Platform**: Python + pynput + tkinter handle platform differences natively

No additional complexity justification required.
