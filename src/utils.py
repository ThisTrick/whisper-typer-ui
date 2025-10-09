"""Shared utilities, exceptions, and data models for Whisper Typer UI."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np


# ============================================================================
# Custom Exceptions (T005)
# ============================================================================

class MicrophoneError(Exception):
    """Microphone access or operation error."""
    
    def __init__(self, device_name: Optional[str], error_code: str):
        """
        Args:
            device_name: Name of the microphone device (None if unavailable)
            error_code: Error type - "NO_DEVICE" | "PERMISSION_DENIED" | "DEVICE_BUSY"
        """
        self.device_name = device_name
        self.error_code = error_code
        super().__init__(f"Microphone error [{error_code}]: device={device_name}")


class TranscriptionError(Exception):
    """Transcription processing error."""
    
    def __init__(self, original_exception: Exception, audio_length: float):
        """
        Args:
            original_exception: The underlying exception from faster-whisper
            audio_length: Length of audio buffer in seconds
        """
        self.original_exception = original_exception
        self.audio_length = audio_length
        super().__init__(f"Transcription failed for {audio_length:.2f}s audio: {original_exception}")


class ConfigError(Exception):
    """Configuration loading or validation error."""
    
    def __init__(self, config_key: str, message: str = ""):
        """
        Args:
            config_key: The configuration key that caused the error
            message: Additional error details
        """
        self.config_key = config_key
        super().__init__(f"Configuration error for '{config_key}': {message}")


class ModelLoadError(Exception):
    """Model loading error for faster-whisper."""
    
    def __init__(self, model_size: str, device: str, message: str = ""):
        """
        Args:
            model_size: The model size that failed to load
            device: The device (cpu/cuda) attempted
            message: Additional error details
        """
        self.model_size = model_size
        self.device = device
        super().__init__(f"Failed to load model '{model_size}' on {device}: {message}")


# ============================================================================
# Data Models and Enums (T007)
# ============================================================================

class SessionState(Enum):
    """Current state of a recording session."""
    IDLE = "idle"                    # No active session
    RECORDING = "recording"          # Microphone capturing audio
    TRANSCRIBING = "transcribing"    # faster-whisper processing
    INSERTING = "inserting"          # Keyboard emulation in progress
    COMPLETED = "completed"          # Text inserted successfully
    ERROR = "error"                  # Any failure occurred


_DEFAULT_ASSET_DIR = Path(__file__).resolve().parent / "assets"
_ALT_ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"


def resolve_asset_path(name: str) -> Path:
    """Resolve an asset name to an on-disk path, supporting editable installs."""
    for base in (_DEFAULT_ASSET_DIR, _ALT_ASSET_DIR):
        candidate = base / name
        if candidate.exists():
            return candidate
    # Return the default location even if missing so callers can emit a warning.
    return _DEFAULT_ASSET_DIR / name


class IconType(Enum):
    """UI overlay icon types."""

    MICROPHONE = "microphone.png"
    PROCESSING = "processing.png"
    ERROR = "error.png"

    @property
    def path(self) -> Path:
        """Resolved filesystem path for the icon asset."""
        return resolve_asset_path(self.value)


@dataclass
class TranscriptionResult:
    """Output from faster-whisper transcription."""
    text: str                # Transcribed text (empty string if no speech detected)
    language: str            # Detected language (may differ from primary_language)
    confidence: float        # Language detection confidence (0.0-1.0)
    processing_time: float   # Transcription duration in seconds
    
    def __post_init__(self):
        """Validate transcription result."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        if self.processing_time < 0:
            raise ValueError(f"Processing time must be positive, got {self.processing_time}")


@dataclass
class ChunkTranscriptionResult:
    """Result from transcribing a single audio chunk.
    
    Attributes:
        sequence: Sequential chunk number matching the input AudioChunk
        text: Transcribed text content
        error: Optional error message if transcription failed
    """
    sequence: int
    text: str
    error: Optional[str] = None

