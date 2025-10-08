# Implementation Tasks: Voice Dictation Application

**Feature Branch**: `001-cross-platform-dictation`  
**Date**: 2025-10-08  
**Total Tasks**: 28  
**Estimated Complexity**: Medium (2000 LOC, 8 modules, 3 user stories)

## Task Organization

Tasks are organized by user story priority (P1 → P2 → P3) to enable incremental delivery and independent manual verification.

**Execution Strategy**:
1. Complete **Setup Phase** (project initialization)
2. Complete **Foundational Phase** (blocking prerequisites)
3. Deliver **User Story 1** (MVP: hotkey + recording + UI)
4. Deliver **User Story 2** (transcription + text insertion)
5. Deliver **User Story 3** (cross-platform packaging)
6. Complete **Polish Phase** (error handling, optimization)

## Phase 1: Setup & Project Initialization

**Goal**: Initialize project structure, dependencies, and configuration system.

**Manual Verification**: Run `uv sync` successfully, application imports all modules without errors.

### T001: Initialize Python project with uv [P] ✓

**File**: `pyproject.toml`, `.python-version`

**Description**: Create `pyproject.toml` with project metadata and dependencies, set Python 3.11+ in `.python-version`.

**Dependencies**:
```toml
[project]
name = "whisper-typer-ui"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "faster-whisper>=1.0.0,<2.0.0",
    "pynput>=1.7.0,<2.0.0",
    "sounddevice>=0.4.0,<1.0.0",
    "numpy>=1.24.0,<2.0.0",
    "pyyaml>=6.0,<7.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Acceptance**: `uv sync` runs successfully, creates virtual environment.

---

### T002: Create project directory structure [P] ✓

**Files**: `src/`, `assets/`, `config.yaml`

**Description**: Create directory structure per plan.md:
- `src/` directory for Python modules
- `assets/` directory for UI icons
- Root-level `config.yaml` with default values

**Structure**:
```text
src/
assets/
config.yaml
```

**Acceptance**: Directories exist, `config.yaml` contains default configuration.

---

### T003: Create default configuration file [P] ✓

**File**: `config.yaml`

**Description**: Create user-editable YAML configuration with sensible defaults.

**Content**:
```yaml
# Whisper Typer UI Configuration
primary_language: "en"
hotkey: "<ctrl>+<alt>+space"
model_size: "base"
compute_type: "int8"
```

**Acceptance**: File exists, valid YAML syntax, contains all required keys.

---

### T004: Implement configuration loader module ✓

**File**: `src/config.py`

**Description**: Create `AppConfig` class that loads and validates `config.yaml`. Include default values for missing keys.

**API** (from contracts/internal-api.md):
```python
class AppConfig:
    def __init__(self, config_path: str = "config.yaml")
    
    @property
    def primary_language(self) -> str
    
    @property
    def hotkey_combo(self) -> str
    
    @property
    def model_size(self) -> str
    
    @property
    def compute_type(self) -> str
    
    def validate(self) -> None
```

**Acceptance**: Config loads successfully, raises `ConfigError` for invalid YAML, provides defaults for missing keys.

---

### T005: Create shared utilities and exceptions module ✓

**File**: `src/utils.py`

**Description**: Define custom exception classes and shared helper functions.

**Exceptions** (from contracts/internal-api.md):
```python
class MicrophoneError(Exception):
    device_name: str | None
    error_code: str  # "NO_DEVICE" | "PERMISSION_DENIED" | "DEVICE_BUSY"

class TranscriptionError(Exception):
    original_exception: Exception
    audio_length: float

class ConfigError(Exception):
    config_key: str

class ModelLoadError(Exception):
    model_size: str
    device: str
```

**Acceptance**: All exception classes defined with proper attributes, importable from other modules.

---

### T006: Create UI icon assets [P] ✓

**Files**: `assets/microphone.png`, `assets/processing.png`

**Description**: Create or source simple PNG icons:
- `microphone.png`: Microphone icon for recording state (64x64px, transparent background)
- `processing.png`: Hourglass/spinner icon for transcription state (64x64px, transparent background)

**Acceptance**: Both PNG files exist, correct size, transparent background, visually clear at 64x64px.

---

## Phase 2: Foundational Components (Blocking Prerequisites)

**Goal**: Implement core infrastructure required by ALL user stories (config loading, exceptions, data models).

**Manual Verification**: All modules import successfully, config loads without errors.

### T007: Define core data models and enums ✓

**File**: `src/utils.py` (add to existing)

**Description**: Create data model enums and dataclasses from data-model.md.

**Classes**:
```python
from enum import Enum
from dataclasses import dataclass
import numpy as np

class SessionState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    INSERTING = "inserting"
    COMPLETED = "completed"
    ERROR = "error"

class IconType(Enum):
    MICROPHONE = "assets/microphone.png"
    PROCESSING = "assets/processing.png"
    ERROR = "assets/error.png"

@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    processing_time: float
```

**Acceptance**: All enums and dataclasses defined, importable, type hints correct.

---

## Phase 3: User Story 1 - Hotkey-Activated Voice Recording (P1 - MVP)

**Story Goal**: User presses global hotkey → UI appears → microphone records → user stops recording → UI disappears.

**Manual Verification Criteria**:
1. Press hotkey while in any application → circular UI appears in bottom-right corner
2. Microphone icon visible, pulsating red border animation active
3. Click icon or press hotkey again → recording stops, UI disappears
4. Works across different applications (text editor, browser, email client)

**Exit Criteria**: All acceptance scenarios from User Story 1 pass manual verification.

---

### T008: [US1] Implement global hotkey manager ✓

**File**: `src/hotkey_manager.py`

**Description**: Create `HotkeyManager` class using pynput.keyboard.GlobalHotKeys for cross-platform hotkey registration.

**API** (from contracts/internal-api.md):
```python
class HotkeyManager:
    def __init__(self, hotkey_combination: str)
    def register(self, callback: Callable[[], None]) -> None
    def start(self) -> None  # Blocking
    def stop(self) -> None
```

**Implementation Pattern** (from research.md):
```python
from pynput import keyboard

def on_activate():
    # Start recording session
    pass

# Register global hotkey
hotkey_combo = '<ctrl>+<alt>+space'
with keyboard.GlobalHotKeys({hotkey_combo: on_activate}) as h:
    h.join()
```

**Acceptance**: Hotkey callback fires when key combination pressed, works across all applications.

**Dependencies**: None (foundational)

---

### T009: [US1] Implement audio recorder module ✓

**File**: `src/audio_recorder.py`

**Description**: Create `AudioRecorder` class using sounddevice for microphone capture.

**API** (from contracts/internal-api.md):
```python
class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1)
    def start_recording(self) -> None
    def stop_recording(self) -> np.ndarray
    def is_recording(self) -> bool
```

**Implementation Pattern** (from research.md):
```python
import sounddevice as sd
import numpy as np

sample_rate = 16000  # Whisper expects 16kHz
recording = []

def callback(indata, frames, time, status):
    recording.append(indata.copy())

with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
    # Wait for user to stop recording
    pass

audio_data = np.concatenate(recording, axis=0)
```

**Acceptance**: Records audio to NumPy array, raises `MicrophoneError` if device unavailable.

**Dependencies**: None (foundational)

---

### T010: [US1] Implement tkinter UI overlay - basic structure ✓

**File**: `src/ui_overlay.py`

**Description**: Create `UIOverlay` class with tkinter circular window, fixed position in bottom-right corner.

**API** (from contracts/internal-api.md):
```python
class UIOverlay:
    def __init__(self, size: int = 80, margin: int = 20)
    def show(self) -> None
    def hide(self) -> None
    def set_icon(self, icon_type: IconType) -> None
    def start_pulsation(self) -> None
    def stop_pulsation(self) -> None
    def show_error(self, message: str, duration: float = 2.5) -> None
```

**Implementation Pattern** (from research.md):
```python
import tkinter as tk

root = tk.Tk()
root.attributes('-topmost', True)  # Always on top
root.attributes('-alpha', 0.9)  # Semi-transparent
root.overrideredirect(True)  # No window decorations

# Bottom-right positioning
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = screen_width - 80 - 20  # size + margin
y = screen_height - 80 - 20
root.geometry(f'80x80+{x}+{y}')

canvas = tk.Canvas(root, width=80, height=80, highlightthickness=0)
circle = canvas.create_oval(10, 10, 70, 70, outline='red', width=3)
```

**Acceptance**: Window appears in bottom-right corner, always on top, no decorations, fixed size.

**Dependencies**: None (foundational)

---

### T011: [US1] Add icon display to UI overlay [P] ✓

**File**: `src/ui_overlay.py` (extend existing)

**Description**: Implement `set_icon()` method to display microphone/processing icons inside circle.

**Implementation**:
```python
from PIL import Image, ImageTk

def set_icon(self, icon_type: IconType):
    image = Image.open(icon_type.value)
    photo = ImageTk.PhotoImage(image)
    self.canvas.create_image(40, 40, image=photo)
```

**Acceptance**: Icons display correctly inside circle, switch between microphone and processing icons.

**Dependencies**: T010 (same file, sequential)

---

### T012: [US1] Add pulsating animation to UI overlay [P] ✓

**File**: `src/ui_overlay.py` (extend existing)

**Description**: Implement `start_pulsation()` and `stop_pulsation()` methods with border width animation (3px → 6px → 3px).

**Implementation**:
```python
def pulsate(self):
    current_width = self.canvas.itemcget(self.circle_id, 'width')
    new_width = 6 if int(current_width) == 3 else 3
    self.canvas.itemconfig(self.circle_id, width=new_width)
    if self.pulsating:
        self.window.after(500, self.pulsate)  # 2 FPS

def start_pulsation(self):
    self.pulsating = True
    self.pulsate()

def stop_pulsation(self):
    self.pulsating = False
    self.canvas.itemconfig(self.circle_id, width=3)
```

**Acceptance**: Border pulsates smoothly, stops when `stop_pulsation()` called.

**Dependencies**: T010 (same file, sequential)

---

### T013: [US1] Implement main application entry point - User Story 1 only ✓

**File**: `src/whisper-typer-ui.py`

**Description**: Create main entry point that wires together hotkey manager, audio recorder, and UI overlay for User Story 1 functionality.

**Implementation**:
```python
from config import AppConfig
from hotkey_manager import HotkeyManager
from audio_recorder import AudioRecorder
from ui_overlay import UIOverlay, IconType
from utils import SessionState

config = AppConfig()
hotkey_mgr = HotkeyManager(config.hotkey_combo)
recorder = AudioRecorder()
ui = UIOverlay()

session_state = SessionState.IDLE

def on_hotkey_press():
    global session_state
    
    if session_state == SessionState.IDLE:
        # Start recording
        session_state = SessionState.RECORDING
        recorder.start_recording()
        ui.show()
        ui.set_icon(IconType.MICROPHONE)
        ui.start_pulsation()
    else:
        # Stop recording
        audio_buffer = recorder.stop_recording()
        ui.stop_pulsation()
        ui.hide()
        session_state = SessionState.IDLE
        # TODO: Transcription in User Story 2

hotkey_mgr.register(on_hotkey_press)
hotkey_mgr.start()
```

**Acceptance**: Hotkey activates recording, UI shows with pulsating animation, second hotkey press stops recording and hides UI.

**Dependencies**: T008, T009, T010, T011, T012

---

### T014: [US1] Add click-to-stop functionality to UI overlay ✓

**File**: `src/ui_overlay.py` (extend existing)

**Description**: Add mouse click event handler to canvas that triggers recording stop.

**Implementation**:
```python
def __init__(self, ...):
    # ... existing code ...
    self.canvas.bind('<Button-1>', self._on_click)
    self.click_callback = None

def set_click_callback(self, callback: Callable[[], None]):
    self.click_callback = callback

def _on_click(self, event):
    if self.click_callback:
        self.click_callback()
```

**Update `whisper-typer-ui.py`**:
```python
def on_ui_click():
    if session_state == SessionState.RECORDING:
        on_hotkey_press()  # Reuse stop logic

ui.set_click_callback(on_ui_click)
```

**Acceptance**: Clicking microphone icon stops recording and hides UI.

**Dependencies**: T013

---

**🏁 CHECKPOINT 1**: User Story 1 (MVP) Complete - Manual Verification Required

**Verification Steps**:
1. Run `uv run python src/whisper-typer-ui.py`
2. Press configured hotkey (default: Ctrl+Alt+Space)
3. Verify: Circular UI appears in bottom-right corner with microphone icon and pulsating red border
4. Verify: Audio recording starts (check microphone indicator on OS)
5. Click microphone icon or press hotkey again
6. Verify: UI disappears, recording stops
7. Test in multiple applications (text editor, browser, terminal)

**Exit Criteria**: All 4 acceptance scenarios from User Story 1 specification pass.

---

## Phase 4: User Story 2 - Complete Recording Then Transcription (P2)

**Story Goal**: Recording stops → audio transcribed locally → text inserted into previously focused text field.

**Manual Verification Criteria**:
1. After stopping recording, UI icon changes to processing indicator
2. Transcription completes within 5-10s for 30s audio
3. Transcribed text appears in previously focused text field (cursor positioned at end)
4. Empty recording (no speech) → UI disappears immediately without typing anything

**Exit Criteria**: All acceptance scenarios from User Story 2 pass manual verification.

---

### T015: [US2] Implement faster-whisper transcriber module ✓

**File**: `src/transcriber.py`

**Description**: Create `Transcriber` class wrapping faster-whisper with model loading and transcription.

**API** (from contracts/internal-api.md):
```python
class Transcriber:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en"
    )
    def transcribe(self, audio_buffer: np.ndarray) -> TranscriptionResult
```

**Implementation Pattern** (from research.md):
```python
from faster_whisper import WhisperModel
import time

class Transcriber:
    def __init__(self, model_size="base", device="cpu", compute_type="int8", language="en"):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.language = language
    
    def transcribe(self, audio_buffer):
        start = time.time()
        segments, info = self.model.transcribe(
            audio_buffer,
            language=self.language,
            beam_size=5
        )
        segments = list(segments)  # Force completion
        text = " ".join([seg.text for seg in segments])
        
        return TranscriptionResult(
            text=text.strip(),
            language=info.language,
            confidence=info.language_probability,
            processing_time=time.time() - start
        )
```

**Acceptance**: Model loads successfully, transcribes audio buffer, returns `TranscriptionResult` with text.

**Dependencies**: None (can develop in parallel with US1)

---

### T016: [US2] Implement keyboard emulation text inserter module [P] ✓

**File**: `src/text_inserter.py`

**Description**: Create `TextInserter` class using pynput.keyboard.Controller for keyboard emulation.

**API** (from contracts/internal-api.md):
```python
class TextInserter:
    def __init__(self, typing_speed: int = 100)
    def type_text(self, text: str) -> None
```

**Implementation Pattern** (from research.md):
```python
from pynput.keyboard import Controller

class TextInserter:
    def __init__(self, typing_speed=100):
        self.controller = Controller()
        self.typing_speed = typing_speed
    
    def type_text(self, text: str):
        self.controller.type(text)
```

**Acceptance**: Types text into focused application, works across different apps.

**Dependencies**: None (can develop in parallel with US1 and T015)

---

### T017: [US2] Add transcription processing to main application ✓

**File**: `src/whisper-typer-ui.py` (extend existing)

**Description**: Integrate transcriber and text inserter into hotkey callback flow. Run transcription in worker thread.

**Implementation**:
```python
from threading import Thread
from transcriber import Transcriber
from text_inserter import TextInserter

transcriber = Transcriber(
    model_size=config.model_size,
    compute_type=config.compute_type,
    language=config.primary_language
)
text_inserter = TextInserter()

def process_transcription(audio_buffer):
    # Update UI to processing state
    ui.stop_pulsation()
    ui.set_icon(IconType.PROCESSING)
    
    # Transcribe in worker thread
    result = transcriber.transcribe(audio_buffer)
    
    # Insert text if not empty
    if result.text:
        text_inserter.type_text(result.text)
    
    # Hide UI
    ui.hide()
    session_state = SessionState.IDLE

def on_hotkey_press():
    # ... existing start logic ...
    else:
        # Stop recording
        audio_buffer = recorder.stop_recording()
        session_state = SessionState.TRANSCRIBING
        
        # Process in worker thread
        thread = Thread(target=process_transcription, args=(audio_buffer,))
        thread.start()
```

**Acceptance**: After recording stops, transcription runs, text inserted, UI hides. Empty results handled silently.

**Dependencies**: T013, T015, T016

---

### T018: [US2] Implement audio buffer cleanup ✓

**File**: `src/whisper-typer-ui.py` (extend existing)

**Description**: Ensure audio buffer is deleted immediately after transcription per FR-026, FR-027.

**Implementation**:
```python
def process_transcription(audio_buffer):
    try:
        # ... transcription logic ...
        pass
    finally:
        # Delete audio buffer immediately
        audio_buffer = None
        del audio_buffer
```

**Acceptance**: Audio buffer deleted in finally block, no persistence to disk.

**Dependencies**: T017 (same file, sequential)

---

**🏁 CHECKPOINT 2**: User Story 2 Complete - Manual Verification Required

**Verification Steps**:
1. Run `uv run python src/whisper-typer-ui.py`
2. Press hotkey, speak "test message", press hotkey again
3. Verify: UI icon changes from microphone to processing indicator
4. Wait 5-10 seconds
5. Verify: "test message" appears in previously focused text field
6. Test empty recording: press hotkey, wait in silence, press hotkey again
7. Verify: UI disappears immediately without typing anything
8. Test in different text fields (browser URL bar, text editor, email compose)

**Exit Criteria**: All 4 acceptance scenarios from User Story 2 specification pass.

---

## Phase 5: User Story 3 - Cross-Platform Compatibility (P3)

**Story Goal**: Application runs natively on Windows, macOS, and Linux with consistent behavior.

**Manual Verification Criteria**:
1. Install on Windows VM → all functionality works identically to development platform
2. Install on macOS VM → all functionality works identically
3. Install on Linux VM → all functionality works identically
4. Single executable, no manual dependency installation required

**Exit Criteria**: All acceptance scenarios from User Story 3 pass manual verification on all 3 platforms.

---

### T019: [US3] Create PyInstaller build script [P] ✓

**File**: `build.py`

**Description**: Create build script using PyInstaller to generate single executable for each platform.

**Implementation** (from research.md):
```python
import PyInstaller.__main__
import sys

platform = sys.argv[1] if len(sys.argv) > 1 else "linux"

PyInstaller.__main__.run([
    'src/whisper-typer-ui.py',
    '--onefile',
    '--windowed',
    '--name=WhisperTyper',
    '--add-data=assets:assets',
    '--add-data=config.yaml:.',
    '--hidden-import=faster_whisper',
    '--hidden-import=pynput',
    '--hidden-import=sounddevice',
    f'--icon=assets/microphone.{"ico" if platform == "windows" else "png"}',
])
```

**Acceptance**: Running `uv run python build.py` generates `dist/WhisperTyper` executable.

**Dependencies**: None (can develop in parallel)

---

### T020: [US3] Test Windows build [P]

**Platform**: Windows 10+

**Description**: Build executable on Windows, test all User Story 1 and 2 scenarios.

**Build Command**:
```bash
uv run python build.py windows
```

**Verification**:
- Double-click `dist/WhisperTyper.exe` → application runs
- Global hotkey works across Windows applications
- UI appears correctly in bottom-right corner
- Transcription and text insertion work

**Acceptance**: All functionality from US1 and US2 works on clean Windows VM without Python installed.

**Dependencies**: T019

---

### T021: [US3] Test macOS build [P]

**Platform**: macOS 11+

**Description**: Build executable on macOS, test all User Story 1 and 2 scenarios.

**Build Command**:
```bash
uv run python build.py macos
```

**Special Handling**:
- Request Accessibility permissions for global hotkeys
- Request Microphone permissions

**Verification**:
- Open `dist/WhisperTyper.app` → application runs
- Grant Accessibility and Microphone permissions when prompted
- Global hotkey works across macOS applications
- UI appears correctly in bottom-right corner
- Transcription and text insertion work

**Acceptance**: All functionality from US1 and US2 works on clean macOS VM without Python installed.

**Dependencies**: T019

---

### T022: [US3] Test Linux build [P]

**Platform**: Ubuntu 20.04+ (X11 and Wayland)

**Description**: Build executable on Linux, test all User Story 1 and 2 scenarios on both X11 and Wayland.

**Build Command**:
```bash
uv run python build.py linux
```

**Verification**:
- Run `./dist/WhisperTyper` → application runs
- Global hotkey works across Linux applications (test on X11)
- Test on Wayland session (may have limitations)
- UI appears correctly in bottom-right corner
- Transcription and text insertion work

**Acceptance**: All functionality from US1 and US2 works on clean Ubuntu VM without Python installed. Document Wayland limitations if any.

**Dependencies**: T019

---

**🏁 CHECKPOINT 3**: User Story 3 Complete - Manual Verification Required

**Verification Steps**:
1. Build executable for each platform
2. Copy executable to clean VM (no Python, no dependencies)
3. Run executable on each platform
4. Verify all US1 and US2 scenarios work identically on all platforms
5. Document any platform-specific issues or workarounds

**Exit Criteria**: All 3 acceptance scenarios from User Story 3 specification pass.

---

## Phase 6: Polish & Error Handling (Cross-Cutting Concerns)

**Goal**: Implement error handling, edge cases, and performance optimizations.

---

### T023: Implement microphone error handling

**File**: `src/audio_recorder.py` (extend existing)

**Description**: Add error detection for microphone unavailable, permissions denied, device busy.

**Implementation**:
```python
import sounddevice as sd
from utils import MicrophoneError

def start_recording(self):
    try:
        devices = sd.query_devices()
        if not devices:
            raise MicrophoneError(None, "NO_DEVICE")
        # ... existing recording logic ...
    except PermissionError:
        raise MicrophoneError(None, "PERMISSION_DENIED")
    except Exception as e:
        raise MicrophoneError(None, "DEVICE_BUSY")
```

**Update `whisper-typer-ui.py`**:
```python
try:
    recorder.start_recording()
except MicrophoneError as e:
    ui.show_error(f"Microphone error: {e.error_code}", duration=2.5)
```

**Acceptance**: Errors display briefly in UI (2-3s), auto-dismiss per FR-016a.

**Dependencies**: T009

---

### T024: Implement transcription error handling

**File**: `src/transcriber.py` (extend existing)

**Description**: Wrap faster-whisper calls with try/except, raise `TranscriptionError` on failure.

**Implementation**:
```python
from utils import TranscriptionError

def transcribe(self, audio_buffer):
    try:
        # ... existing transcription logic ...
    except Exception as e:
        raise TranscriptionError(e, len(audio_buffer))
```

**Update `whisper-typer-ui.py`**:
```python
try:
    result = transcriber.transcribe(audio_buffer)
except TranscriptionError as e:
    ui.show_error("Transcription failed", duration=2.5)
```

**Acceptance**: Transcription errors display briefly, application continues running.

**Dependencies**: T015

---

### T025: Handle duplicate hotkey press (UI already visible)

**File**: `src/whisper-typer-ui.py` (extend existing)

**Description**: Add state check to prevent starting new recording while one is active.

**Implementation**:
```python
def on_hotkey_press():
    if session_state == SessionState.RECORDING:
        # Stop current recording (existing logic)
        pass
    elif session_state == SessionState.TRANSCRIBING:
        # Ignore - transcription in progress
        return
    elif session_state == SessionState.IDLE:
        # Start new recording (existing logic)
        pass
```

**Acceptance**: Pressing hotkey during transcription does nothing, pressing during recording stops it.

**Dependencies**: T017

---

### T026: Implement UI error display method

**File**: `src/ui_overlay.py` (extend existing)

**Description**: Implement `show_error()` method with auto-dismiss timer.

**Implementation**:
```python
def show_error(self, message: str, duration: float = 2.5):
    self.show()
    # Change to error icon or display text
    self.set_icon(IconType.ERROR)
    # Auto-dismiss after duration
    self.window.after(int(duration * 1000), self.hide)
```

**Acceptance**: Error messages display for specified duration, auto-dismiss.

**Dependencies**: T010

---

### T027: Optimize model loading at startup [P]

**File**: `src/whisper-typer-ui.py` (extend existing)

**Description**: Load faster-whisper model during startup (not on first transcription) with loading indicator.

**Implementation**:
```python
print("Loading transcription model...")
transcriber = Transcriber(
    model_size=config.model_size,
    compute_type=config.compute_type,
    language=config.primary_language
)
print("Model loaded. Press hotkey to activate.")
```

**Acceptance**: Model loads once at startup, no delay on first transcription.

**Dependencies**: T015

---

### T028: Create end-user README documentation ✓

**File**: `README.md`

**Description**: Write minimal README with installation and usage instructions per Constitution Principle IV.

**Content Structure**:
```markdown
# Whisper Typer UI

Voice dictation application for Windows, macOS, and Linux.

## Installation

1. Download WhisperTyper executable for your platform
2. Run the executable
3. Grant microphone permissions when prompted

## Usage

1. Press Ctrl+Alt+Space to start recording
2. Speak your message
3. Press Ctrl+Alt+Space again or click the microphone icon to stop
4. Transcribed text will appear in your focused text field

## Configuration

Edit `config.yaml` to change:
- Primary language
- Hotkey combination
- Model size (tiny, base, small, medium, large-v3)

## Troubleshooting

- **Microphone not found**: Check microphone connection and permissions
- **Hotkey not working**: Change hotkey in config.yaml
- **Slow transcription**: Use smaller model (tiny or base)
```

**Acceptance**: README contains installation, usage, configuration, and troubleshooting sections only.

**Dependencies**: None (can write in parallel)

---

## Dependency Graph

**User Story Completion Order** (sequential delivery):

```text
Setup Phase (T001-T006)
    ↓
Foundational Phase (T007)
    ↓
User Story 1 [P1] (T008-T014) ← MVP RELEASE
    ↓
User Story 2 [P2] (T015-T018)
    ↓
User Story 3 [P3] (T019-T022)
    ↓
Polish Phase (T023-T028)
```

**Within-Story Dependencies**:

```text
User Story 1 (P1):
  T008 [P] ─┐
  T009 [P] ─┼─→ T013 → T014
  T010 [P] ─┤
  T011 [P] ─┘
  T012 [P] ─┘

User Story 2 (P2):
  T015 [P] ─┐
  T016 [P] ─┼─→ T017 → T018
  T013     ─┘

User Story 3 (P3):
  T019 → T020 [P]
      → T021 [P]
      → T022 [P]

Polish Phase:
  T023 [P]
  T024 [P]
  T025
  T026 [P]
  T027 [P]
  T028 [P]
```

## Parallel Execution Opportunities

**Setup Phase** (6 parallelizable tasks):
```bash
# All T001-T006 can run in parallel
T001: Initialize pyproject.toml [P]
T002: Create directory structure [P]
T003: Create config.yaml [P]
T006: Create icon assets [P]

# Sequential after:
T004: Implement config.py (needs T003)
T005: Implement utils.py (needs T002)
```

**User Story 1** (5 parallelizable foundation tasks):
```bash
# Foundation modules (parallel)
T008: hotkey_manager.py [P]
T009: audio_recorder.py [P]
T010: ui_overlay.py base [P]

# UI enhancements (parallel after T010)
T011: Icon display [P]
T012: Pulsation animation [P]

# Integration (sequential)
T013: Main application integration
T014: Click handler
```

**User Story 2** (2 parallelizable tasks):
```bash
# Core modules (parallel)
T015: transcriber.py [P]
T016: text_inserter.py [P]

# Integration (sequential)
T017: Integrate into main app
T018: Audio cleanup
```

**User Story 3** (3 parallelizable platform builds):
```bash
T019: Build script

# Platform testing (parallel after T019)
T020: Windows build [P]
T021: macOS build [P]
T022: Linux build [P]
```

## Manual Verification Checklist

### After User Story 1 (MVP):
- [ ] Hotkey activates from any application
- [ ] UI appears in bottom-right corner
- [ ] Microphone icon visible with pulsating red border
- [ ] Click icon stops recording
- [ ] Hotkey press stops recording
- [ ] UI disappears after stop
- [ ] Works in: text editor, browser, email client

### After User Story 2:
- [ ] Icon changes to processing indicator after recording stops
- [ ] Transcription completes in 5-10s for 30s audio
- [ ] Transcribed text appears in previously focused field
- [ ] Cursor positioned at end of inserted text
- [ ] Empty recording (silence) → UI disappears immediately
- [ ] Works in: browser URL bar, terminal, rich text editor

### After User Story 3:
- [ ] Windows executable runs without Python installed
- [ ] macOS executable runs without Python installed
- [ ] Linux executable runs without Python installed
- [ ] All US1 and US2 scenarios work on all 3 platforms
- [ ] Executable size <200MB per platform

### After Polish Phase:
- [ ] Microphone errors display and auto-dismiss
- [ ] Transcription errors display and auto-dismiss
- [ ] Duplicate hotkey presses handled gracefully
- [ ] Model loads at startup (no first-use delay)
- [ ] README documentation clear and minimal

## Implementation Strategy

**MVP-First Delivery**:
1. **Week 1**: Complete User Story 1 (T001-T014) → Release MVP for single-platform testing
2. **Week 2**: Complete User Story 2 (T015-T018) → Release beta with transcription
3. **Week 3**: Complete User Story 3 (T019-T022) → Release v1.0 cross-platform
4. **Week 4**: Polish Phase (T023-T028) → Release v1.1 with error handling

**Risk Mitigation**:
- Checkpoint after each user story for manual verification
- Early model loading test (T015) to catch faster-whisper issues
- Platform-specific testing in parallel (T020-T022)
- Constitution compliance verified at each checkpoint

**Performance Monitoring**:
- Measure hotkey activation time (target: <1s)
- Measure transcription time per audio length (target: 5-10s for 30s)
- Monitor memory usage (target: <620MB peak)
- Profile typing speed (target: 50-100 chars/sec)

---

## Summary

**Total Tasks**: 28  
**User Story Breakdown**:
- Setup Phase: 6 tasks
- Foundational Phase: 1 task
- User Story 1 (P1 - MVP): 7 tasks
- User Story 2 (P2): 4 tasks
- User Story 3 (P3): 4 tasks
- Polish Phase: 6 tasks

**Parallel Opportunities**: 18 parallelizable tasks (64%)  
**Estimated Completion**: 4 weeks (1 week per phase)  
**MVP Delivery**: End of Week 1 (User Story 1 complete)

**Manual Verification Points**: 3 checkpoints (after each user story)  
**Constitution Compliance**: All tasks align with simplicity, no tests, minimal docs principles

**Next Steps**: Begin with Setup Phase (T001-T006), then deliver MVP (User Story 1) for early feedback.
