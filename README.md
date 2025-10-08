# Whisper Typer UI

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/ThisTrick/whisper-typer-ui)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)](https://github.com/ThisTrick/whisper-typer-ui)

**Fast, privacy-focused voice dictation for your desktop**

Whisper Typer UI transforms your speech into text instantly using OpenAI's Whisper model running entirely on your machine. No internet required, no data sent to servers — your voice stays private.

---

## ✨ Features

- 🎤 **Press-to-record** — Hold hotkey, speak, release to transcribe
- ⚡ **Lightning fast** — ~1 second transcription for 10 seconds of speech (tiny model)
- 🔒 **100% private** — Everything runs locally, audio never saved to disk
- 🌍 **99+ languages** — English, Ukrainian, Chinese, Arabic, and more
- 💻 **Cross-platform** — Windows, macOS, Linux
- 🎨 **Minimal overlay** — Sleek circular indicator with smooth animations
- ⌨️ **Auto-paste** — Text instantly appears in your active application
- 🚀 **GPU accelerated** — CUDA support for 5-10x faster transcription

---

## 📦 Installation

### Linux (Ubuntu/Debian)

```bash
# Install system dependencies
sudo apt install xclip python3.11

# Clone and install
git clone https://github.com/ThisTrick/whisper-typer-ui.git
cd whisper-typer-ui

# Install with uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# Run
uv run python src/whisper-typer-ui.py
```

### Windows

```powershell
# Clone repository
git clone https://github.com/ThisTrick/whisper-typer-ui.git
cd whisper-typer-ui

# Install with uv
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
uv sync

# Run
uv run python src/whisper-typer-ui.py
```

### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Clone and install
git clone https://github.com/ThisTrick/whisper-typer-ui.git
cd whisper-typer-ui
brew install python@3.11
uv sync

# Run
uv run python src/whisper-typer-ui.py
```

> **First run**: The application will download the Whisper model (~75MB for `tiny`, ~3GB for `large-v3`). This only happens once.

---

## 🚀 Quick Start

1. **Launch the app**
   ```bash
   uv run python src/whisper-typer-ui.py
   ```

2. **Press the hotkey** (default: `Ctrl+Alt+Space`)
   - A circular overlay appears

3. **Speak your message**
   - Red pulsing circle = recording

4. **Release the hotkey**
   - Blue rotating circle = transcribing

5. **Text appears automatically**
   - Pasted into your active application

That's it! 🎉

---

## ⚙️ Configuration

Edit `config.yaml` to customize settings:

```yaml
# Language (ISO 639-1 code: en, uk, de, fr, es, ja, zh, etc.)
primary_language: "en"

# Hotkey (pynput format)
hotkey: "<ctrl>+<alt>+<space>"

# Model (tiny=fastest, large-v3=most accurate)
model_size: "tiny"

# Performance tuning
beam_size: 1        # 1=fastest, 5=most accurate
vad_filter: true    # Skip silence (recommended)
device: "cpu"       # "cuda" for GPU acceleration
compute_type: "int8"  # int8=fastest, float32=highest quality
```

### Model Comparison

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| `tiny` | 75MB | ⚡⚡⚡ | ⭐⭐ | Real-time dictation |
| `base` | 140MB | ⚡⚡ | ⭐⭐⭐ | Balanced usage |
| `small` | 460MB | ⚡ | ⭐⭐⭐⭐ | High accuracy |
| `large-v3` | 3GB | 🐌 | ⭐⭐⭐⭐⭐ | Professional transcription |

**Recommendation**: Start with `tiny` for speed, upgrade to `base` if accuracy is insufficient.

---

## 🎯 Performance Tips

### For Maximum Speed

```yaml
model_size: "tiny"
beam_size: 1
vad_filter: true
device: "cpu"  # or "cuda" if you have NVIDIA GPU
```

**Expected speed**: ~1 second for 10s audio on modern CPU

### For Maximum Accuracy

```yaml
model_size: "small"
beam_size: 5
vad_filter: false
```

**Expected speed**: ~5-10 seconds for 30s audio

### GPU Acceleration

If you have an NVIDIA GPU:

```yaml
device: "cuda"
```

Install CUDA toolkit first:
- [CUDA Downloads](https://developer.nvidia.com/cuda-downloads)

**Speed boost**: 5-10x faster transcription! 🚀

---

## 🔧 Troubleshooting

<details>
<summary><b>Microphone not detected</b></summary>

**Linux**:
```bash
# Check microphone devices
arecord -l

# Test recording
arecord -d 3 test.wav && aplay test.wav
```

**Windows**: Check Sound Settings → Input devices

**macOS**: System Preferences → Security & Privacy → Microphone
</details>

<details>
<summary><b>Hotkey not working</b></summary>

- **Check conflicts**: Another app might use the same hotkey
- **Try different combo**: Edit `hotkey` in `config.yaml`
- **Linux Wayland**: Global hotkeys have limited support
- **macOS**: Grant Accessibility permissions when prompted
</details>

<details>
<summary><b>Text not pasting (Linux)</b></summary>

```bash
# Install clipboard tool
sudo apt install xclip

# Verify it works
echo "test" | xclip -selection clipboard
xclip -selection clipboard -o
```
</details>

<details>
<summary><b>Slow transcription</b></summary>

1. Switch to faster model:
   ```yaml
   model_size: "tiny"
   beam_size: 1
   ```

2. Enable VAD filter:
   ```yaml
   vad_filter: true
   ```

3. Use GPU (NVIDIA only):
   ```yaml
   device: "cuda"
   ```
</details>

<details>
<summary><b>Empty results / no text inserted</b></summary>

- **Speak louder**: Ensure microphone picks up your voice
- **Check recording**: Look at console output for audio length
- **Verify language**: Set `primary_language` to match your speech
- **Reduce noise**: Try quieter environment
</details>

---

## 🛠️ Technical Details

| Component | Technology |
|-----------|-----------|
| Transcription | [faster-whisper](https://github.com/guillaumekln/faster-whisper) (CTranslate2) |
| Audio Capture | [sounddevice](https://python-sounddevice.readthedocs.io/) |
| Text Insertion | Clipboard paste (xclip/win32clipboard/pbcopy) |
| Hotkey Detection | [pynput](https://github.com/moses-palmer/pynput) |
| UI | tkinter (native) |
| Privacy | ✅ No network, no storage, no telemetry |

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) — Amazing speech recognition model
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) — Blazing fast implementation
- [pynput](https://github.com/moses-palmer/pynput) — Reliable keyboard control

---

**Built with ❤️ for privacy and productivity**
