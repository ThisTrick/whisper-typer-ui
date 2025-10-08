# whisper-typer-ui Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-08

## Active Technologies
- Python 3.11+ (async support, mature cross-platform libraries) + faster-whisper (transcription), tkinter (UI), pynput (keyboard emulation), sounddevice (audio recording), pynput (global hotkey), PyInstaller (packaging) (001-cross-platform-dictation)
- Python stdlib: concurrent.futures.ThreadPoolExecutor, queue.Queue, threading, time (002-streaming-transcription)
- N/A (no persistence - FR-026, FR-027) (001-cross-platform-dictation)

## Project Structure
```
src/
tests/
```

## Commands
cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style
Python 3.11+ (async support, mature cross-platform libraries): Follow standard conventions

## Recent Changes
- 002-streaming-transcription: ✅ Completed - Added streaming audio transcription with parallel chunk processing (ThreadPoolExecutor, 3 workers), time-based 30s chunking, ordered text insertion
- 002-streaming-transcription: Added N/A (no new dependencies - uses stdlib only)
- 001-cross-platform-dictation: Added Python 3.11+ (async support, mature cross-platform libraries) + faster-whisper (transcription), tkinter (UI), pynput (keyboard emulation), sounddevice (audio recording), pynput (global hotkey), PyInstaller (packaging)
- 001-cross-platform-dictation: Added Python 3.11+ (async support, mature cross-platform libraries) + faster-whisper (transcription), tkinter (UI), pynput (keyboard emulation), sounddevice (audio recording), pynput (global hotkey), PyInstaller (packaging)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
