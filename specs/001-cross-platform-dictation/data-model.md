# Data Model: Voice Dictation Application

**Feature**: 001-cross-platform-dictation  
**Date**: 2025-10-08

## Overview

This application maintains minimal state in memory only. No persistence layer exists per Constitution Principle III and FR-026/FR-027 (no audio storage).

## Core Entities

### 1. RecordingSession

Represents a single dictation session from hotkey press to text insertion completion.

**Attributes**:

- `session_id: str` - UUID for debugging/logging only
- `start_time: float` - Unix timestamp when recording started
- `stop_time: float | None` - Unix timestamp when recording stopped (None while active)
- `audio_buffer: np.ndarray | None` - NumPy array of audio samples (16kHz mono)
- `sample_rate: int = 16000` - Audio sample rate (fixed, Whisper requirement)
- `target_window: str` - Name/title of previously focused window
- `state: SessionState` - Current session state (enum)

**State Transitions**:

```text
IDLE → RECORDING → TRANSCRIBING → INSERTING → COMPLETED
         ↓                                        ↑
         └──────────── ERROR ────────────────────┘
```

**Lifecycle**:

1. Created when hotkey pressed (state: RECORDING)
2. Audio buffered while recording active
3. User stops recording → state: TRANSCRIBING
4. faster-whisper processes audio → state: INSERTING
5. Text emulated via keyboard → state: COMPLETED
6. Object deleted (GC collects audio buffer)

**Validation Rules**:

- `audio_buffer` must not be None when state is TRANSCRIBING or INSERTING
- `stop_time` must be >= `start_time`
- Audio buffer deleted immediately when state reaches COMPLETED or ERROR

---

### 2. SessionState (Enum)

**Values**:

```python
class SessionState(Enum):
    IDLE = "idle"                    # No active session
    RECORDING = "recording"          # Microphone capturing audio
    TRANSCRIBING = "transcribing"    # faster-whisper processing
    INSERTING = "inserting"          # Keyboard emulation in progress
    COMPLETED = "completed"          # Text inserted successfully
    ERROR = "error"                  # Any failure occurred
```

**State-to-UI Mapping**:

- IDLE: UI hidden
- RECORDING: UI visible, microphone icon, pulsating red border
- TRANSCRIBING: UI visible, processing icon (hourglass/spinner), static border
- INSERTING: UI visible during insertion (or hide immediately for simplicity)
- COMPLETED: UI hidden
- ERROR: UI shows error briefly (2-3s), then hides (FR-016a)

---

### 3. AppConfig

Configuration loaded from `config.yaml` at startup. Immutable during app runtime (restart required for changes).

**Attributes**:

- `primary_language: str` - ISO 639-1 language code (e.g., "uk", "en", "de")
- `hotkey_combo: str` - pynput hotkey format (e.g., "<ctrl>+<alt>+space")
- `model_size: str` - faster-whisper model size ("tiny" | "base" | "small" | "medium" | "large-v3")
- `compute_type: str` - CTranslate2 compute type ("int8" | "float16" | "float32")

**Default Values** (if config.yaml missing or incomplete):

```yaml
primary_language: "en"
hotkey_combo: "<ctrl>+<alt>+space"
model_size: "base"
compute_type: "int8"
```

**Validation Rules**:

- `primary_language` must be valid ISO 639-1 code (2 letters)
- `hotkey_combo` must parse successfully via pynput.keyboard.HotKey.parse()
- `model_size` must be one of faster-whisper supported models
- `compute_type` must be compatible with device (CPU supports int8/float32, GPU supports all)

---

### 4. TranscriptionResult

Output from faster-whisper processing.

**Attributes**:

- `text: str` - Transcribed text (empty string if no speech detected)
- `language: str` - Detected language (may differ from primary_language)
- `confidence: float` - Language detection confidence (0.0-1.0)
- `segments: list[Segment]` - Individual transcription segments (unused in v1, future streaming)
- `processing_time: float` - Transcription duration in seconds

**Validation Rules**:

- `text` may be empty (FR-010b: silent handling of empty results)
- `confidence` between 0.0 and 1.0
- `processing_time` > 0

**Usage**:

```python
result = transcriber.transcribe(audio_buffer, language="uk")
if result.text:
    keyboard_controller.type(result.text)
else:
    # Empty result: hide UI immediately (FR-010b)
    ui_overlay.hide()
```

---

### 5. UIOverlay

Represents the tkinter circular overlay window.

**Attributes**:

- `window: tk.Tk` - Root tkinter window
- `canvas: tk.Canvas` - Canvas for circular drawing
- `circle_id: int` - Canvas item ID for circle outline
- `icon_id: int` - Canvas item ID for icon image
- `current_icon: IconType` - Current displayed icon (enum)
- `position: tuple[int, int]` - Fixed (x, y) screen coordinates (bottom-right)
- `size: int = 80` - Fixed diameter in pixels

**Icon Types**:

```python
class IconType(Enum):
    MICROPHONE = "assets/microphone.png"
    PROCESSING = "assets/processing.png"
    ERROR = "assets/error.png"
```

**Methods**:

- `show()` - Make window visible
- `hide()` - Make window invisible
- `set_icon(icon_type: IconType)` - Change displayed icon
- `start_pulsation()` - Begin pulsating border animation
- `stop_pulsation()` - Stop pulsating border animation
- `show_error(message: str)` - Display error briefly (2-3s auto-dismiss)

**Position Calculation** (FR-020a):

```python
screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()
x = screen_width - size - 20  # 20px margin from right
y = screen_height - size - 20  # 20px margin from bottom
```

---

## Relationships

```text
AppConfig (1) ──── loaded by ───> Application (1)
                                       │
                                       │ manages
                                       ↓
                              RecordingSession (0..1)
                                       │
                                       │ produces
                                       ↓
                             TranscriptionResult (0..1)
                                       
Application (1) ──── controls ───> UIOverlay (1)
```

**Key Points**:

- **1:1 Application:AppConfig** - Single config loaded at startup
- **1:0..1 Application:RecordingSession** - At most one active session (no concurrent recordings)
- **1:1 RecordingSession:TranscriptionResult** - Each session produces exactly one result (may be empty)
- **1:1 Application:UIOverlay** - Single UI window, toggled on/off

---

## Memory Management

### Audio Buffer Lifecycle

```python
# 1. Recording starts
session = RecordingSession()
session.audio_buffer = np.array([], dtype=np.float32)

# 2. Audio chunks accumulated
while recording:
    chunk = microphone.read()
    session.audio_buffer = np.concatenate([session.audio_buffer, chunk])

# 3. Transcription
result = transcriber.transcribe(session.audio_buffer)

# 4. IMMEDIATE deletion (FR-026, FR-027)
session.audio_buffer = None  # GC will collect NumPy array
del session  # Session object deleted after text insertion
```

**Peak Memory Usage**:

- Empty session: ~1KB (object overhead)
- Recording 30s: ~1KB + (30s × 16000 samples × 4 bytes) ≈ 2MB
- Transcribing: +500MB (model loaded in separate object)
- Total: ~502MB during transcription (within <620MB target from research.md)

### Model Caching

```python
# Loaded ONCE at application startup, cached for lifetime
transcriber = WhisperModel("base", device="cpu", compute_type="int8")

# Reused for every transcription (no per-session loading)
for session in sessions:
    result = transcriber.transcribe(session.audio_buffer)
```

---

## No Persistence

**Explicitly NOT Stored**:

- Audio recordings (deleted immediately per FR-026)
- Transcription results (discarded after insertion)
- Session history (no logging to disk)
- User activity (no telemetry)

**Only Persistent Data**:

- `config.yaml` - User-editable configuration (read-only at runtime)

---

## Error States

### MicrophoneError

**When**: No microphone detected or permissions denied

**Data**:

```python
class MicrophoneError(Exception):
    device_name: str | None
    error_code: str  # "NO_DEVICE" | "PERMISSION_DENIED" | "DEVICE_BUSY"
```

**Handling**: Show error message in UI (FR-016), auto-dismiss after 2-3s (FR-016a)

### TranscriptionError

**When**: faster-whisper processing fails

**Data**:

```python
class TranscriptionError(Exception):
    original_exception: Exception
    audio_length: float  # For debugging
```

**Handling**: Show generic error "Transcription failed" in UI, auto-dismiss

### EmptyTranscriptionResult

**Not an error** per FR-010b - handled silently by checking `result.text == ""`

---

## Threading Model

### Main Thread

- tkinter event loop (UI updates)
- Global hotkey listener (pynput)
- Keyboard emulation (pynput Controller)

### Worker Thread

- Audio recording (sounddevice background callback)
- Transcription processing (faster-whisper model.transcribe)

**Synchronization**:

```python
from threading import Thread, Event

transcription_complete = Event()

def transcribe_worker(audio_buffer):
    result = transcriber.transcribe(audio_buffer)
    transcription_complete.set()
    return result

# Start transcription in worker thread
thread = Thread(target=transcribe_worker, args=(session.audio_buffer,))
thread.start()

# Main thread waits for completion, updates UI
transcription_complete.wait()
ui_overlay.set_icon(IconType.PROCESSING)
```

---

## Validation Summary

| Entity | Key Constraints | Enforced By |
|--------|----------------|-------------|
| RecordingSession | audio_buffer not None when transcribing | State machine logic |
| RecordingSession | Audio deleted when state ≥ COMPLETED | Session cleanup method |
| AppConfig | primary_language valid ISO 639-1 | Config loader validation |
| TranscriptionResult | text may be empty (valid) | No validation needed |
| UIOverlay | position fixed, no user control | Constructor sets once |

---

## Future Considerations (Not in v1)

- **Streaming transcription**: RecordingSession.segments would be populated incrementally
- **Session history**: Add SessionHistory entity with 10 most recent (in-memory only, no disk)
- **Multi-language detection**: TranscriptionResult could include per-segment language
- **Performance metrics**: Add timing attributes to RecordingSession for optimization

These are explicitly OUT OF SCOPE for first version per simplification decision (sequential processing).
