#!/usr/bin/env python3
"""Build script for creating cross-platform executables."""

import sys
import PyInstaller.__main__

# Determine platform
platform = sys.argv[1] if len(sys.argv) > 1 else "linux"

# Icon file based on platform
icon_file = {
    "windows": "assets/microphone.ico",
    "macos": "assets/microphone.png",
    "linux": "assets/microphone.png"
}.get(platform, "assets/microphone.png")

print(f"Building for platform: {platform}")

# Run PyInstaller
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
    '--hidden-import=numpy',
    '--hidden-import=yaml',
    '--hidden-import=PIL',
    f'--icon={icon_file}',
    '--clean',
])

print(f"\nBuild complete! Executable located in dist/")
