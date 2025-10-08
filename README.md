# Whisper Typer UI

Voice dictation application for Windows, macOS, and Linux.

## Features

- **Global Hotkey Activation**: Press Ctrl+Alt+Space to start/stop recording from anywhere
- **Local Processing**: All transcription happens on your device - no internet required
- **Multi-Language Support**: Supports 99 languages via faster-whisper
- **Simple UI**: Circular overlay in bottom-right corner with visual feedback
- **Cross-Platform**: Works on Windows 10+, macOS 11+, and Linux (Ubuntu 20.04+)

## Installation

### From Source (Development)

1. **Prerequisites**:
   - Python 3.11 or higher
   - uv package manager: https://github.com/astral-sh/uv
   - Microphone access

2. **Clone and Install**:
   ```bash
   git clone <repository-url>
   cd whisper-typer-ui
   uv sync
   ```

3. **Run**:
   ```bash
   uv run python src/whisper-typer-ui.py
   ```

### From Executable (Coming Soon)

1. Download `WhisperTyper` executable for your platform
2. Run the executable
3. Grant microphone permissions when prompted

## Usage

1. **Start the Application**: Run `whisper-typer-ui.py` or the executable
2. **Start Recording**: Press `Ctrl+Alt+Space` (or your configured hotkey)
3. **Speak Your Message**: A circular UI appears in the bottom-right corner
4. **Stop Recording**: Press `Ctrl+Alt+Space` again or click the microphone icon
5. **Text Appears**: Transcribed text is inserted into your focused text field

## Configuration

Edit `config.yaml` to customize:

```yaml
# Primary language for transcription (ISO 639-1 code)
primary_language: "en"

# Global hotkey combination (pynput format)
hotkey: "<ctrl>+<alt>+<space>"

# Model configuration
model_size: "tiny"  # tiny, base, small, medium, large-v3
compute_type: "int8"  # int8, float16, float32
device: "cpu"  # cpu or cuda (NVIDIA GPU)

# Performance tuning
beam_size: 1  # Lower = faster, higher = more accurate (default: 5)
vad_filter: true  # Skip silent parts (faster)
```

**Supported Languages**: Any ISO 639-1 code (e.g., "en", "uk", "de", "fr", "es", "ja", "zh")

**Model Sizes**:

- `tiny` (39MB): **Fastest** - great for real-time dictation
- `base` (74MB): Good balance of speed and accuracy
- `small` (244MB): Better accuracy, slower
- `medium` (769MB): High accuracy
- `large-v3` (~3GB): Best accuracy, very slow

**Performance Optimization**:

- **For speed**: `tiny` model + `beam_size: 1` + `vad_filter: true`
- **For accuracy**: `base`/`small` model + `beam_size: 5`
- **GPU boost**: Set `device: "cuda"` (requires NVIDIA GPU, 5-10x faster!)

## Troubleshooting

### Microphone Not Working

- **Check permissions**: Ensure microphone access is granted
- **Check connection**: Verify microphone is connected and working
- **Test in other apps**: Confirm microphone works elsewhere

### Hotkey Not Working

- **Check conflicts**: Try a different hotkey combination in `config.yaml`
- **Platform-specific**:
  - **Linux Wayland**: May have limited global hotkey support
  - **macOS**: Grant Accessibility permissions when prompted

### Slow Transcription

**Quick fixes** (try these first):

1. Use `tiny` model: `model_size: "tiny"` in config.yaml
2. Lower beam size: `beam_size: 1`
3. Enable VAD filter: `vad_filter: true`

**Advanced optimization**:

- **GPU acceleration**: Set `device: "cuda"` (requires NVIDIA GPU + CUDA)
- **Expected speeds** (on modern CPU):
  - `tiny` + beam_size 1: ~2-3 seconds for 30s audio
  - `base` + beam_size 5: ~5-10 seconds for 30s audio
  - With CUDA GPU: 5-10x faster!

### Empty Results (No Text Inserted)

- **Speak clearly**: Ensure speech is audible
- **Check microphone**: Verify recording actually captured audio
- **Try different language**: Verify `primary_language` in config matches your speech

## Technical Details

- **Transcription Engine**: faster-whisper (CTranslate2-optimized Whisper)
- **Audio Capture**: sounddevice
- **Keyboard Emulation**: pynput
- **UI Framework**: tkinter
- **No Data Storage**: Audio is never saved to disk (privacy-focused)

## Development

```bash
# Install dependencies
uv sync

# Run application
uv run python src/whisper-typer-ui.py

# Build executable
uv add pyinstaller
uv run python build.py linux
```

## License

See LICENSE file for details.

## Privacy

- All processing happens locally on your device
- No internet connection required
- Audio is never saved to disk
- No telemetry or data collection
