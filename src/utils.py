"""Shared utilities, exceptions, and data models for Whisper Typer UI."""

from dataclasses import dataclass
from enum import Enum
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


class IconType(Enum):
    """UI overlay icon types."""
    MICROPHONE = "assets/microphone.png"
    PROCESSING = "assets/processing.png"
    ERROR = "assets/error.png"


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

