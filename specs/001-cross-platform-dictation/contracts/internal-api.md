# Internal API Contracts

**Feature**: 001-cross-platform-dictation  
**Date**: 2025-10-08

## Overview

This document defines the internal Python API contracts between modules. No external HTTP/REST APIs exist (desktop application).

---

## 1. HotkeyManager

**Module**: `src/hotkey_manager.py`  
**Purpose**: Register and manage global hotkey listener

### Class: HotkeyManager

#### Constructor

```python
def __init__(self, hotkey_combination: str)
```

**Parameters**:

- `hotkey_combination` (str): pynput format string (e.g., "`<ctrl>+<alt>+space`")

**Raises**:

- `ValueError`: If hotkey_combination cannot be parsed

**Example**:

```python
manager = HotkeyManager("<ctrl>+<alt>+space")
```

#### Methods

##### register(callback: Callable[[], None]) → None

Register callback function to be invoked when hotkey pressed.

**Parameters**:

- `callback`: Function with no parameters, no return value

**Example**:

```python
def on_hotkey_pressed():
    print("Hotkey activated!")

manager.register(on_hotkey_pressed)
```

##### start() → None

Start listening for hotkey presses (blocking call).

**Blocks**: Yes - runs until application exit

**Example**:

```python
manager.start()  # Runs forever
```

##### stop() → None

Stop hotkey listener (called from signal handler).

---

## 2. AudioRecorder

**Module**: `src/audio_recorder.py`  
**Purpose**: Capture microphone audio into NumPy buffer

### Class: AudioRecorder

#### Constructor

```python
def __init__(self, sample_rate: int = 16000, channels: int = 1)
```

**Parameters**:

- `sample_rate` (int): Audio sample rate in Hz (default 16000 for Whisper)
- `channels` (int): Number of audio channels (default 1 = mono)

**Raises**:

- `MicrophoneError`: If no microphone detected

#### Methods

##### start_recording() → None

Begin capturing audio into internal buffer.

**Raises**:

- `MicrophoneError`: If microphone busy or permissions denied

**Example**:

```python
recorder = AudioRecorder()
recorder.start_recording()
```

##### stop_recording() → np.ndarray

Stop recording and return captured audio buffer.

**Returns**:

- `np.ndarray`: Audio samples as float32 array, shape (n_samples,)

**Side Effects**:

- Internal buffer cleared after return

**Example**:

```python
audio_buffer = recorder.stop_recording()
print(f"Captured {len(audio_buffer)} samples")
```

##### is_recording() → bool

Check if currently recording.

**Returns**:

- `bool`: True if recording active, False otherwise

---

## 3. Transcriber

**Module**: `src/transcriber.py`  
**Purpose**: Wrapper around faster-whisper for audio transcription

### Class: Transcriber

#### Constructor

```python
def __init__(
    self,
    model_size: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    language: str = "en"
)
```

**Parameters**:

- `model_size` (str): Model name ("tiny" | "base" | "small" | "medium" | "large-v3")
- `device` (str): "cpu" or "cuda"
- `compute_type` (str): "int8" | "float16" | "float32"
- `language` (str): ISO 639-1 primary language code

**Raises**:

- `ModelLoadError`: If model download/loading fails

**Side Effects**:

- Downloads model to ~/.cache/huggingface/hub/ (first time only)
- Loads model into memory (~500MB for large-v3 INT8)

**Example**:

```python
transcriber = Transcriber(
    model_size="base",
    device="cpu",
    compute_type="int8",
    language="uk"
)
```

#### Methods

##### transcribe(audio_buffer: np.ndarray) → TranscriptionResult

Transcribe audio buffer to text.

**Parameters**:

- `audio_buffer` (np.ndarray): Audio samples, shape (n_samples,), dtype float32

**Returns**:

- `TranscriptionResult`: Object with `text`, `language`, `confidence`, `processing_time`

**Raises**:

- `TranscriptionError`: If faster-whisper processing fails

**Side Effects**:

- None (audio_buffer not modified, no disk I/O)

**Example**:

```python
result = transcriber.transcribe(audio_buffer)
if result.text:
    print(f"Transcribed: {result.text}")
else:
    print("No speech detected")
```

### Dataclass: TranscriptionResult

```python
@dataclass
class TranscriptionResult:
    text: str                # Transcribed text (may be empty)
    language: str            # Detected language (ISO 639-1)
    confidence: float        # Language detection confidence (0.0-1.0)
    processing_time: float   # Transcription duration in seconds
```

---

## 4. TextInserter

**Module**: `src/text_inserter.py`  
**Purpose**: Insert text into focused application via clipboard paste (cross-platform)

### Class: TextInserter

#### Constructor

```python
def __init__(self, typing_speed: int = 100)
```

**Parameters**:

- `typing_speed` (int): Unused (kept for compatibility), clipboard paste is instant

#### Methods

##### type_text(text: str) → None

Insert text into currently focused application via clipboard paste.

**Parameters**:

- `text` (str): Text to insert

**Side Effects**:

- Saves current clipboard content
- Sets clipboard to new text
- Simulates Ctrl+V (Linux/Windows) or Cmd+V (macOS) keypress
- Restores original clipboard content

**Platform-specific behavior**:

- **Linux**: Uses `xclip` + `Ctrl+V`
- **Windows**: Uses `win32clipboard` or PowerShell + `Ctrl+V`
- **macOS**: Uses `pbcopy` + `Cmd+V`
- **Fallback**: Uses pynput keyboard emulation if clipboard fails

**Timing**:

- Duration ≈ 0.2s (instant paste, regardless of text length)

**Advantages over keyboard emulation**:

- 10-100x faster for long text
- Perfect for Unicode (Cyrillic, Chinese, emoji, etc.)
- No character-by-character delays
- More reliable across all platforms

**Example**:

```python
inserter = TextInserter()
inserter.type_text("Привіт з диктування! 🎤")
# Takes ~0.2s regardless of text length
```

**Requirements**:

- **Linux**: Requires `xclip` package (`sudo apt install xclip`)
- **Windows**: Works natively (optional `pywin32` for better performance)
- **macOS**: Works natively with `pbcopy`/`pbpaste`

---

## 5. UIOverlay

**Module**: `src/ui_overlay.py`  
**Purpose**: Tkinter circular overlay window

### Class: UIOverlay

#### Constructor

```python
def __init__(self, size: int = 80, margin: int = 20)
```

**Parameters**:

- `size` (int): Circle diameter in pixels (default 80)
- `margin` (int): Margin from screen edges in pixels (default 20)

**Side Effects**:

- Creates hidden tkinter window at bottom-right corner

#### Methods

##### show() → None

Make overlay visible.

**Example**:

```python
ui = UIOverlay()
ui.show()
```

##### hide() → None

Hide overlay (window still exists).

**Example**:

```python
ui.hide()
```

##### set_icon(icon_type: IconType) → None

Change displayed icon.

**Parameters**:

- `icon_type` (IconType): MICROPHONE | PROCESSING | ERROR

**Example**:

```python
ui.set_icon(IconType.PROCESSING)
```

##### start_pulsation() → None

Begin pulsating border animation (3px → 6px → 3px loop).

**Side Effects**:

- Starts tkinter timer loop (10 FPS)

##### stop_pulsation() → None

Stop pulsating animation, reset border to 3px.

##### show_error(message: str, duration: float = 2.5) → None

Display error message briefly, then auto-dismiss.

**Parameters**:

- `message` (str): Error text to display
- `duration` (float): Seconds before auto-dismiss (default 2.5)

**Example**:

```python
ui.show_error("Microphone not found", duration=3.0)
```

### Enum: IconType

```python
class IconType(Enum):
    MICROPHONE = "assets/microphone.png"
    PROCESSING = "assets/processing.png"
    ERROR = "assets/error.png"
```

---

## 6. Config

**Module**: `src/config.py`  
**Purpose**: Load and validate configuration from YAML

### Class: AppConfig

#### Constructor

```python
def __init__(self, config_path: str = "config.yaml")
```

**Parameters**:

- `config_path` (str): Path to YAML config file

**Raises**:

- `ConfigError`: If file missing or invalid YAML

**Side Effects**:

- Reads config file from disk
- Applies default values for missing keys

**Example**:

```python
config = AppConfig("config.yaml")
print(config.primary_language)  # "uk"
```

#### Properties

All properties are read-only (no setters).

##### primary_language: str

ISO 639-1 language code (e.g., "uk", "en", "de").

##### hotkey_combo: str

pynput hotkey format (e.g., "`<ctrl>+<alt>+space`").

##### model_size: str

faster-whisper model size ("tiny" | "base" | "small" | "medium" | "large-v3").

##### compute_type: str

CTranslate2 compute type ("int8" | "float16" | "float32").

#### Methods

##### validate() → None

Validate all configuration values.

**Raises**:

- `ConfigError`: If any value invalid (e.g., unknown language code)

**Example**:

```python
config = AppConfig()
config.validate()  # Raises if invalid
```

---

## 7. Exceptions

**Module**: `src/utils.py`

### MicrophoneError

Raised when microphone unavailable or permissions denied.

```python
class MicrophoneError(Exception):
    device_name: str | None
    error_code: str  # "NO_DEVICE" | "PERMISSION_DENIED" | "DEVICE_BUSY"
```

**Usage**:

```python
try:
    recorder.start_recording()
except MicrophoneError as e:
    print(f"Microphone error: {e.error_code}")
```

### TranscriptionError

Raised when faster-whisper processing fails.

```python
class TranscriptionError(Exception):
    original_exception: Exception
    audio_length: float  # For debugging
```

### ConfigError

Raised when configuration file invalid.

```python
class ConfigError(Exception):
    config_key: str  # Which config value failed
```

### ModelLoadError

Raised when faster-whisper model cannot be loaded.

```python
class ModelLoadError(Exception):
    model_size: str
    device: str
```

---

## Contract Validation

All contracts enforced via:

1. **Type hints**: Python 3.11+ type annotations
2. **Runtime validation**: `assert` statements in development mode
3. **Exception handling**: Explicit raises documented above
4. **Manual verification**: No automated tests per Constitution Principle III

---

## Dependency Graph

```text
whisper-typer-ui.py
  ├─> HotkeyManager
  ├─> AudioRecorder
  ├─> Transcriber
  ├─> TextInserter
  ├─> UIOverlay
  └─> AppConfig

HotkeyManager → (no dependencies)
AudioRecorder → sounddevice
Transcriber → faster_whisper, numpy
TextInserter → pynput.keyboard
UIOverlay → tkinter
AppConfig → pyyaml
```

**No circular dependencies**: Linear dependency chain from whisper-typer-ui.py outward.
