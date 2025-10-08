# Research: Voice Dictation Application

**Date**: 2025-10-08  
**Feature**: 001-cross-platform-dictation

## Technology Stack Decisions

### 1. Transcription Engine: faster-whisper

**Decision**: Use faster-whisper (CTranslate2-based reimplementation of OpenAI Whisper)

**Rationale**:
- 4x faster than original Whisper with same accuracy
- Lower memory usage through quantization (INT8, FP16)
- Supports 99 languages (matches FR-021)
- Fully offline/local operation (FR-009a)
- Well-documented Python API with simple usage patterns
- Active maintenance (Trust Score: 6.8, 18 code snippets)

**Performance Characteristics**:
- Model sizes: tiny (39M), base (74M), small (244M), medium (769M), large-v3 (~3GB)
- CPU execution: INT8 quantization recommended, set `OMP_NUM_THREADS` for consistent performance
- Memory baseline: ~500MB for large-v3 INT8 on CPU, ~100MB baseline
- Transcription speed: ~5-10s for 30s audio on modern CPU (meets SC-002)

**Implementation Pattern**:
```python
from faster_whisper import WhisperModel

# Load model once at startup (CPU INT8 for cross-platform compatibility)
model = WhisperModel("large-v3", device="cpu", compute_type="int8")

# Transcribe with language hint
segments, info = model.transcribe(
    "audio.wav", 
    language="uk",  # Primary language from config
    beam_size=5
)

# Force completion and collect text
segments = list(segments)
full_text = " ".join([seg.text for seg in segments])
```

**Alternatives Considered**:
- OpenAI Whisper: Slower (4x), higher memory usage
- Vosk: Faster but lower accuracy, fewer languages (~20 vs 99)
- Mozilla DeepSpeech: Discontinued, English-only focus

---

### 2. Global Hotkey: pynput.keyboard

**Decision**: Use pynput.keyboard.GlobalHotKeys for cross-platform hotkey registration

**Rationale**:
- Native cross-platform support (Windows, macOS, Linux X11/Wayland)
- Simple API for global hotkeys (FR-001)
- Same library handles keyboard emulation (FR-010a) - single dependency
- Well-documented with 132 code snippets, Trust Score 8.3
- No external system dependencies

**Implementation Pattern**:
```python
from pynput import keyboard

def on_activate():
    # Start recording session
    pass

# Register global hotkey
hotkey_combo = '<ctrl>+<alt>+space'  # From config.yaml
with keyboard.GlobalHotKeys({hotkey_combo: on_activate}) as h:
    h.join()
```

**Known Limitations**:
- Hotkeys not suppressed from other applications (may conflict with existing shortcuts)
- Internal keyboard state may desynchronize (mitigated by simple toggle logic)

**Alternatives Considered**:
- keyboard library: Less mature cross-platform support
- Platform-specific APIs: Violates simplicity principle, requires 3x implementation effort

---

### 3. Keyboard Emulation: pynput.keyboard.Controller

**Decision**: Use pynput.keyboard.Controller.type() for text insertion

**Rationale**:
- Works across all target applications that accept keyboard input (FR-010, FR-010a)
- Cross-platform compatible
- Simple API: `controller.type(transcribed_text)`
- No clipboard manipulation (cleaner UX, no side effects)

**Implementation Pattern**:
```python
from pynput.keyboard import Controller

keyboard = Controller()
keyboard.type(transcribed_text)  # Simulates typing each character
```

**Performance Consideration**:
- Typing speed: ~50-100 chars/second (acceptable for typical dictation lengths)
- For very long text (>1000 chars), consider chunked typing with short delays

**Alternatives Considered**:
- Clipboard + Ctrl+V: Overwrites user's clipboard (violates user expectation)
- Platform-specific APIs (Windows SendInput, macOS CGEvent): More complex, violates simplicity

---

### 4. UI Framework: tkinter

**Decision**: Use tkinter for circular overlay UI

**Rationale**:
- Built into Python standard library (no additional dependency)
- Cross-platform (Windows, macOS, Linux)
- Sufficient for simple circular overlay (FR-004, FR-019)
- Can create transparent, always-on-top windows (FR-020, FR-020a)
- Lightweight (~5MB memory overhead)

**Implementation Pattern**:
```python
import tkinter as tk

# Create overlay window
root = tk.Tk()
root.attributes('-topmost', True)  # Always on top (FR-020)
root.attributes('-alpha', 0.9)  # Semi-transparent
root.overrideredirect(True)  # No window decorations
root.geometry('80x80+{}+{}'.format(screen_width-100, screen_height-100))  # Bottom-right

# Circular canvas with pulsating animation
canvas = tk.Canvas(root, width=80, height=80, highlightthickness=0)
circle = canvas.create_oval(10, 10, 70, 70, outline='red', width=3)

def pulsate():
    # Animate outline width 3 -> 6 -> 3
    pass
```

**Animation Strategy**:
- Pulsating border: Use `canvas.itemconfig()` to change outline width in timer loop
- Icon change: Use `canvas.create_image()` with different PNG assets (microphone.png, processing.png)

**Alternatives Considered**:
- PyQt/PySide: Overkill for simple overlay, large dependency (~50MB)
- PySimpleGUI: Additional dependency, not as lightweight
- Custom OpenGL: Unnecessary complexity

---

### 5. Audio Recording: sounddevice

**Decision**: Use sounddevice for cross-platform audio capture

**Rationale**:
- Cross-platform (Windows/WASAPI, macOS/CoreAudio, Linux/ALSA)
- NumPy integration (faster-whisper accepts NumPy arrays)
- Simple blocking/non-blocking recording API
- Active maintenance, well-documented

**Implementation Pattern**:
```python
import sounddevice as sd
import numpy as np

# Record until stopped
sample_rate = 16000  # Whisper expects 16kHz
recording = []

def callback(indata, frames, time, status):
    recording.append(indata.copy())

with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
    # Wait for user to stop recording
    pass

# Convert to NumPy array for faster-whisper
audio_data = np.concatenate(recording, axis=0)
```

**Alternatives Considered**:
- pyaudio: More complex API, requires PortAudio installation
- wave module: Standard library but lower-level, harder to use

---

### 6. Configuration: YAML file

**Decision**: Use config.yaml for user settings (primary language, hotkey)

**Rationale**:
- Human-readable and editable (FR-024, SC-012)
- No UI required for configuration (FR-025)
- Python standard library support via `pip install pyyaml`
- Simple key-value structure sufficient

**Configuration Schema**:
```yaml
# config.yaml
primary_language: "uk"  # ISO 639-1 code
hotkey: "<ctrl>+<alt>+space"
model_size: "large-v3"
compute_type: "int8"
```

**Implementation**:
```bash
uv add pyyaml
```

**Alternatives Considered**:
- JSON: Less human-friendly for editing
- Environment variables: Harder to persist changes
- Command-line only: Requires remembering syntax

---

### 7. Packaging: PyInstaller

**Decision**: Use PyInstaller for single-executable distribution

**Rationale**:
- Creates standalone executables for Windows (.exe), macOS (.app), Linux (binary)
- Bundles Python interpreter + all dependencies (FR-002, Principle II)
- No user-side Python installation required
- Cross-platform build support
- Simple build script

**Build Strategy**:
```python
# build.py
import PyInstaller.__main__

PyInstaller.__main__.run([
    'src/whisper-typer-ui.py',
    '--onefile',  # Single executable
    '--windowed',  # No console window
    '--name=WhisperTyper',
    '--add-data=assets:assets',
    '--add-data=config.yaml:.',
    '--hidden-import=faster_whisper',
    '--hidden-import=pynput'
])
```

**Distribution Targets**:
- Windows: .exe installer via Inno Setup or NSIS
- macOS: .dmg with drag-to-Applications
- Linux: .AppImage or .deb package

**Alternatives Considered**:
- cx_Freeze: Less mature, fewer platform options
- Nuitka: Compilation takes longer, overkill for utility app
- pip install: Requires Python knowledge (violates Principle II)

---

## Performance Optimization Strategies

### 1. Model Loading at Startup
- Load faster-whisper model once during app initialization (not per transcription)
- Use INT8 quantization for CPU to balance accuracy/speed/memory
- Cache model in memory for entire app lifetime

### 2. Audio Buffer Management
- Record to memory-only buffer (no disk I/O - FR-026, FR-027)
- Use NumPy arrays directly (zero-copy to faster-whisper)
- Delete audio immediately after transcription (FR-026)

### 3. UI Responsiveness
- Run transcription in separate thread (non-blocking UI)
- Update UI overlay from main thread only (avoid tkinter threading issues)
- Use asyncio for concurrent hotkey listening + UI updates

### 4. Memory Footprint
- Baseline: ~100MB (Python + tkinter + pynput)
- Active recording: +20MB (audio buffer)
- Transcription: +500MB (large-v3 INT8 model)
- Total peak: ~620MB (within <500MB baseline + <500MB transcription target)

---

## Cross-Platform Considerations

### Windows
- Global hotkeys: pynput uses Win32 hooks (SetWindowsHookEx)
- Audio: WASAPI via sounddevice
- UI overlay: tkinter Toplevel with `-topmost` attribute
- Keyboard emulation: SendInput API via pynput

### macOS
- Global hotkeys: pynput uses Quartz Event Services
- Audio: CoreAudio via sounddevice
- UI overlay: tkinter Toplevel with `-topmost` (may require Accessibility permissions)
- Keyboard emulation: CGEvent API via pynput
- **Special requirement**: Request Accessibility permissions for global hotkeys

### Linux (X11/Wayland)
- Global hotkeys: pynput uses X11 protocol (XGrabKey) or Wayland input-method
- Audio: ALSA/PulseAudio via sounddevice
- UI overlay: tkinter Toplevel with `-topmost` (X11 override-redirect)
- Keyboard emulation: XTest extension via pynput
- **Special requirement**: May need X11 forwarding for remote sessions

---

## Risk Mitigation

### 1. Transcription Accuracy
- **Risk**: Inaccurate transcription for non-primary languages
- **Mitigation**: Allow primary language configuration (FR-022, FR-023), use beam_size=5 for better accuracy

### 2. Hotkey Conflicts
- **Risk**: User's chosen hotkey conflicts with other applications
- **Mitigation**: Make hotkey configurable (FR-018), provide sensible default, document common conflicts

### 3. Microphone Permissions
- **Risk**: User denies microphone access
- **Mitigation**: Auto-dismiss error message (FR-016a, SC-014), clear error text explaining permissions

### 4. Platform-Specific Bugs
- **Risk**: Behavior differences across Windows/macOS/Linux
- **Mitigation**: Manual testing on all platforms (SC-004), simple architecture reduces platform-specific code paths

### 5. Large Model Download
- **Risk**: 3GB model download on first run
- **Mitigation**: Bundle smaller model (base ~74MB) with installer, allow user to download large-v3 later via config

---

## Implementation Priority (Aligns with User Stories)

### Phase P1: Hotkey-Activated Recording (MVP)
1. Global hotkey registration (pynput)
2. Microphone detection and recording (sounddevice)
3. Circular UI overlay with pulsating animation (tkinter)
4. Recording start/stop toggle

### Phase P2: Transcription and Insertion
1. faster-whisper integration with INT8 CPU model
2. Transcription processing after recording completes
3. Keyboard emulation for text insertion (pynput.keyboard.Controller)
4. Icon change during transcription (FR-008b)
5. Empty result handling (FR-010b)

### Phase P3: Cross-Platform Polish
1. Configuration file support (YAML)
2. Primary language configuration
3. PyInstaller build scripts for all platforms
4. Platform-specific installers (.exe, .dmg, .AppImage)
5. Error handling for permissions/microphone issues

---

## Dependencies Summary

**Core Runtime** (managed via uv):
- faster-whisper ~= 1.0.0
- pynput ~= 1.7.0
- sounddevice ~= 0.4.0
- numpy ~= 1.24.0
- pyyaml ~= 6.0

**Build-Time Only**:
- PyInstaller ~= 6.0.0

**Package Manager**: uv (fast, reliable Python package installer)

**Total Dependency Count**: 5 runtime + 1 build-time = 6 total (meets Constitution dependency minimization)

---

## Open Questions Resolved

1. **Q**: Which transcription engine?  
   **A**: faster-whisper (fastest + accurate + 99 languages)

2. **Q**: How to handle empty transcription results?  
   **A**: Silent dismissal, no error (FR-010b, clarification session)

3. **Q**: CPU vs GPU for transcription?  
   **A**: CPU with INT8 (cross-platform compatibility, no CUDA requirement)

4. **Q**: Model size for bundling?  
   **A**: Base model (74MB) bundled, large-v3 optional download

5. **Q**: Threading model?  
   **A**: Main thread for UI + hotkey listener, separate thread for transcription

---

## Next Steps

Proceed to Phase 1: Design artifacts (data-model.md, contracts/, quickstart.md)
