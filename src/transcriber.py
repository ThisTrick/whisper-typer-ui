"""Transcription module using faster-whisper."""

import importlib
import logging
import os
import time
from typing import Any

import numpy as np
from faster_whisper import WhisperModel

from audio_recorder import AudioChunk
from utils import TranscriptionResult, TranscriptionError, ModelLoadError, ChunkTranscriptionResult


logger = logging.getLogger(__name__)


class Transcriber:
    """Wrapper around faster-whisper for audio transcription."""
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en",
        beam_size: int = 5,
        vad_filter: bool = True,
        cpu_workers: str | int = "auto",
    ):
        """Initialize transcriber and load model.
        
        Args:
            model_size: Model name ("tiny" | "base" | "small" | "medium" | "large-v3")
            device: "cpu" or "cuda"
            compute_type: "int8" | "float16" | "float32"
            language: ISO 639-1 primary language code
            beam_size: Beam size for transcription (lower = faster)
            vad_filter: Whether to use VAD filter to skip silence
            
        Raises:
            ModelLoadError: If model download/loading fails
        """
        self.model_size = model_size
        self.device = self._resolve_device(device)
        self.compute_type = self._resolve_compute_type(compute_type, self.device)
        self.language = language
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self.num_workers = self._resolve_workers(cpu_workers)

        # Load model
        try:
            logger.info(
                "Loading whisper model '%s' (compute=%s, device=%s, workers=%s)...",
                model_size,
                self.compute_type,
                self.device,
                self.num_workers if self.num_workers else "default",
            )
            self.model = WhisperModel(
                model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info("Model loaded successfully")
        except Exception as e:
            raise ModelLoadError(model_size, self.device, str(e))

    @staticmethod
    def _resolve_device(device: str) -> str:
        """Resolve user-requested device, auto-detecting GPU if available."""
        if device != "auto":
            return device

        # Try PyTorch if available for robust CUDA detection
        torch_spec = importlib.util.find_spec("torch")
        if torch_spec is not None:
            try:
                torch = importlib.import_module("torch")
                if hasattr(torch, "cuda") and torch.cuda.is_available():
                    return "cuda"
            except Exception:
                logger.debug("PyTorch CUDA detection failed; falling back to CPU", exc_info=True)

        # Fallback detection based on CUDA_VISIBLE_DEVICES
        cuda_env = os.environ.get("CUDA_VISIBLE_DEVICES", "")
        if cuda_env not in ("", "-1"):
            return "cuda"

        return "cpu"

    @staticmethod
    def _resolve_compute_type(compute_type: str, device: str) -> str:
        """Select compute precision based on device when auto is requested."""
        if compute_type != "auto":
            return compute_type

        if device == "cuda":
            return "float16"

        return "int8"

    @staticmethod
    def _resolve_workers(cpu_workers: str | int) -> int | None:
        """Determine CPU worker threads for the decoder."""
        if isinstance(cpu_workers, int):
            return max(cpu_workers, 1)

        if cpu_workers != "auto":
            logger.warning("Unrecognized cpu_workers setting '%s'; using library default", cpu_workers)
            return None

        # Auto-tune workers: reserve one core for UI/main thread when possible
        cpu_count = os.cpu_count() or 1
        if cpu_count <= 2:
            return 1
        return cpu_count - 1
    
    def transcribe(self, audio_buffer: np.ndarray) -> TranscriptionResult:
        """Transcribe audio buffer to text.
        
        Args:
            audio_buffer: Audio samples, shape (n_samples,), dtype float32
            
        Returns:
            TranscriptionResult with transcribed text and metadata
            
        Raises:
            TranscriptionError: If transcription fails
        """
        # Calculate audio length
        audio_length = len(audio_buffer) / 16000.0  # Assuming 16kHz sample rate
        
        try:
            start_time = time.time()
            
            logger.info(f"Starting transcription of {audio_length:.2f}s audio...")
            
            # Transcribe with language hint
            # Note: This is the CPU-intensive blocking operation
            transcribe_options: dict[str, Any] = {
                "language": self.language,
                "beam_size": self.beam_size,
                "vad_filter": self.vad_filter,
                "without_timestamps": True,
            }
            if self.num_workers:
                transcribe_options["num_workers"] = self.num_workers

            segments, info = self.model.transcribe(
                audio_buffer,
                **transcribe_options,
            )
            
            logger.info("Transcription model finished, collecting segments...")
            
            # Force completion and collect text
            segments = list(segments)
            full_text = " ".join([seg.text for seg in segments])
            
            processing_time = time.time() - start_time
            
            # Create result
            result = TranscriptionResult(
                text=full_text.strip(),
                language=info.language,
                confidence=info.language_probability,
                processing_time=processing_time
            )
            
            logger.info(f"Transcription completed in {processing_time:.2f}s")
            logger.info(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")
            if result.text:
                logger.info(f"Transcribed text: {result.text}")
            else:
                logger.info("No speech detected (empty result)")
            
            return result
            
        except Exception as e:
            raise TranscriptionError(e, audio_length)
    
    def transcribe_chunk(self, chunk: AudioChunk) -> ChunkTranscriptionResult:
        """Transcribe a single audio chunk for streaming mode.
        
        Args:
            chunk: AudioChunk with data, sequence, and start_time
            
        Returns:
            ChunkTranscriptionResult with sequence, text, and optional error
        """
        try:
            # Transcribe chunk audio
            transcribe_options: dict[str, Any] = {
                "language": self.language,
                "beam_size": self.beam_size,
                "vad_filter": self.vad_filter,
                "without_timestamps": True,
            }
            if self.num_workers:
                transcribe_options["num_workers"] = self.num_workers

            segments, info = self.model.transcribe(
                chunk.data,
                **transcribe_options,
            )
            
            # Collect transcribed text
            segments = list(segments)
            text = " ".join([seg.text for seg in segments]).strip()
            
            return ChunkTranscriptionResult(
                sequence=chunk.sequence,
                text=text,
                error=None
            )
            
        except Exception as e:
            # Return error result instead of raising
            return ChunkTranscriptionResult(
                sequence=chunk.sequence,
                text="",
                error=str(e)
            )

