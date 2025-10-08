# Quickstart Guide: Voice Dictation Application

**Feature**: 001-cross-platform-dictation  
**Date**: 2025-10-08  
**Target Audience**: Developers implementing the feature

## Prerequisites

- Python 3.11+
- uv package manager (https://github.com/astral-sh/uv)
- Git
- ~4GB disk space (for faster-whisper models)
- Microphone access on development machine

## Development Environment Setup

### 1. Clone and Navigate

```bash
cd /home/den/git/whisper-typer-ui
git checkout 001-cross-platform-dictation
```

### 2. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install Dependencies

```bash
uv sync
```

**pyproject.toml** (or requirements.txt for uv):

```text
faster-whisper>=1.0.0,<2.0.0
pynput>=1.7.0,<2.0.0
sounddevice>=0.4.0,<1.0.0
numpy>=1.24.0,<2.0.0
pyyaml>=6.0,<7.0
```

### 4. Download Model (First Run Only)

```bash
# Automatically downloaded on first transcription
# Or manually download for offline development:
uv run python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
```

Model will be cached in `~/.cache/huggingface/hub/` (~74MB for base model).

## Project Structure

```text
src/
├── whisper-typer-ui.py  # Entry point: run this file
├── hotkey_manager.py    # Global hotkey registration
├── audio_recorder.py    # Microphone capture
├── transcriber.py       # faster-whisper wrapper
├── text_inserter.py     # Keyboard emulation
├── ui_overlay.py        # tkinter circular UI
├── config.py            # YAML config loader
└── utils.py             # Shared helpers

assets/
├── microphone.png       # UI icon (recording state)
└── processing.png       # UI icon (transcribing state)

config.yaml              # User configuration
```

## Running the Application

### Development Mode

```bash
uv run python src/whisper-typer-ui.py
```

**What happens**:

1. Config loaded from `config.yaml`
2. faster-whisper model loaded (may take 5-10s first time)
3. Global hotkey registered (default: Ctrl+Alt+Space)
4. Application runs in background
5. Press hotkey → UI appears → speak → click icon or press hotkey again → text inserted

### With Custom Config

```bash
# Edit config.yaml first
uv run python src/whisper-typer-ui.py
```

**config.yaml example**:

```yaml
primary_language: "uk"
hotkey: "<ctrl>+<alt>+space"
model_size: "base"
compute_type: "int8"
```

## Implementation Phases

### Phase P1: Hotkey + Recording (MVP)

**Goal**: Hotkey activates, microphone records, UI shows pulsating circle

**Files to implement**:

1. `src/hotkey_manager.py` - GlobalHotKeys setup
2. `src/audio_recorder.py` - sounddevice recording
3. `src/ui_overlay.py` - tkinter circular overlay
4. `src/whisper-typer-ui.py` - Wire up hotkey → recording → UI

**Verification**:

- Press hotkey → circular UI appears in bottom-right
- Microphone permission requested (if first time)
- Red pulsating border visible
- Click icon or press hotkey again → UI disappears

**Exit Criteria (P1)**:

- [x] SC-001: Hotkey activates within 1s
- [x] FR-001: Global hotkey works across all apps
- [x] FR-004: Circular UI in bottom-right corner
- [x] FR-005: Pulsating animation during recording

---

### Phase P2: Transcription + Insertion

**Goal**: Recording stops → transcription → text appears in focused app

**Files to implement**:

1. `src/transcriber.py` - faster-whisper integration
2. `src/text_inserter.py` - pynput keyboard emulation
3. `src/config.py` - YAML config loader
4. Update `src/ui_overlay.py` - Add processing icon state
5. Update `src/whisper-typer-ui.py` - Wire up transcription pipeline

**Implementation Flow**:

```python
# whisper-typer-ui.py orchestration
def on_hotkey_press():
    if session.state == IDLE:
        # Start recording
        session.start_recording()
        ui.show()
        ui.start_pulsation()
        ui.set_icon(MICROPHONE)
    else:
        # Stop recording, start transcription
        session.stop_recording()
        ui.stop_pulsation()
        ui.set_icon(PROCESSING)
        
        # Worker thread
        result = transcriber.transcribe(session.audio_buffer, language=config.primary_language)
        
        if result.text:
            text_inserter.type(result.text)
        
        ui.hide()
        session.cleanup()  # Delete audio buffer
```

**Verification**:

- Speak "test message" → stop recording → wait 5-10s → "test message" appears in focused text field
- Empty recording (no speech) → UI disappears immediately without typing anything
- Icon changes from microphone to processing symbol during transcription

**Exit Criteria (P2)**:

- [x] SC-002: Transcription completes within 5-10s for 30s audio
- [x] SC-005: Text inserts correctly 90% of the time
- [x] FR-009: Transcription happens after recording (not during)
- [x] FR-009b: faster-whisper used
- [x] FR-010: Text inserted into previously focused field
- [x] FR-010b: Empty result handled silently
- [x] FR-008b: Icon changes during processing

---

### Phase P3: Cross-Platform + Packaging

**Goal**: Build single executable for Windows, macOS, Linux

**Files to implement**:

1. `build.py` - PyInstaller build script
2. Platform-specific installers (optional)
3. README.md - Installation instructions

**Build Commands**:

```bash
# Windows
python build.py --platform windows

# macOS
python build.py --platform macos

# Linux
python build.py --platform linux
```

**Build Output**:

- `dist/WhisperTyper.exe` (Windows)
- `dist/WhisperTyper.app` (macOS)
- `dist/WhisperTyper` (Linux binary)

**Verification**:

- Install on clean VM/machine without Python
- Run executable → application works identically to development mode
- Repeat on all 3 platforms

**Exit Criteria (P3)**:

- [x] SC-006: Install and run within 5 minutes
- [x] SC-004: UI responsive on all platforms
- [x] FR-013: Native support for Windows, macOS, Linux

---

## Common Development Tasks

### Testing Transcription Accuracy

```bash
# Record 30s audio sample
uv run python -c "
from src.audio_recorder import AudioRecorder
from src.transcriber import Transcriber

recorder = AudioRecorder()
audio = recorder.record(duration=30)
transcriber = Transcriber(model_size='base', language='uk')
result = transcriber.transcribe(audio)
print(result.text)
"
```

### Testing Hotkey Registration

```bash
# Run minimal hotkey test
uv run python -c "
from src.hotkey_manager import HotkeyManager

def callback():
    print('Hotkey pressed!')

mgr = HotkeyManager('<ctrl>+<alt>+space')
mgr.register(callback)
mgr.start()  # Blocking
"
```

### Testing UI Overlay

```bash
# Show UI without recording
uv run python -c "
from src.ui_overlay import UIOverlay
import time

ui = UIOverlay()
ui.show()
ui.start_pulsation()
time.sleep(5)
ui.hide()
"
```

### Changing Model Size

Edit `config.yaml`:

```yaml
model_size: "large-v3"  # Options: tiny, base, small, medium, large-v3
```

**Model Comparison**:

| Model | Size | Speed (30s audio) | Accuracy | Languages |
|-------|------|-------------------|----------|-----------|
| tiny | 39MB | ~2s | Low | 99 |
| base | 74MB | ~5s | Medium | 99 |
| small | 244MB | ~10s | Good | 99 |
| medium | 769MB | ~20s | Better | 99 |
| large-v3 | 3GB | ~30s | Best | 99 |

**Recommendation**: Start with `base` for development, `small` for production.

---

## Debugging Tips

### Enable Verbose Logging

```python
# Add to top of whisper-typer-ui.py
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("faster_whisper").setLevel(logging.DEBUG)
```

### Check Microphone Access

```bash
uv run python -c "import sounddevice as sd; print(sd.query_devices())"
```

### Test Keyboard Emulation

```bash
uv run python -c "
from pynput.keyboard import Controller
import time

kb = Controller()
time.sleep(3)  # Switch to text editor
kb.type('Hello from pynput!')
"
```

### Profile Transcription Speed

```python
import time
from src.transcriber import Transcriber

transcriber = Transcriber()
start = time.time()
result = transcriber.transcribe(audio_buffer)
print(f"Transcription took {time.time() - start:.2f}s")
```

---

## Troubleshooting

### "No module named 'faster_whisper'"

```bash
uv sync
```

### "Could not find default audio device"

**Linux**: Install ALSA or PulseAudio

```bash
sudo apt-get install libasound2-dev libportaudio2
```

**macOS**: Grant microphone permissions in System Preferences → Security & Privacy → Microphone

**Windows**: Check Device Manager → Audio inputs and outputs

### Hotkey not working

- **Conflict**: Another app using same hotkey. Change in `config.yaml`
- **Permissions**: On macOS, grant Accessibility permissions in System Preferences
- **Wayland**: Global hotkeys may not work on Wayland (use X11 session)

### Transcription very slow

- **CPU threads**: Set `OMP_NUM_THREADS=4` before running
- **Model size**: Use smaller model (`tiny` or `base`)
- **Compute type**: Use `int8` instead of `float16`

---

## Next Steps After Implementation

1. **Manual Testing**: Follow Phase P1/P2/P3 exit criteria
2. **Cross-Platform Verification**: Test on Windows, macOS, Linux VMs
3. **Performance Profiling**: Measure SC-001 (1s activation) and SC-002 (5-10s transcription)
4. **User Feedback**: Share executable with 2-3 users for real-world testing
5. **README Documentation**: Write installation guide for end users

---

## References

- **faster-whisper docs**: https://github.com/systran/faster-whisper
- **pynput docs**: https://pynput.readthedocs.io/
- **sounddevice docs**: https://python-sounddevice.readthedocs.io/
- **PyInstaller docs**: https://pyinstaller.org/
- **Feature spec**: [spec.md](./spec.md)
- **Research findings**: [research.md](./research.md)
- **Data model**: [data-model.md](./data-model.md)
