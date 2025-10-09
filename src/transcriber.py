"""Transcription module using faster-whisper."""

import logging
import time

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
        vad_filter: bool = True
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
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        
        # Load model
        try:
            logger.info(f"Loading whisper model '{model_size}' ({compute_type} on {device})...")
            self.model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type
            )
            logger.info("Model loaded successfully")
        except Exception as e:
            raise ModelLoadError(model_size, device, str(e))
    
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
            segments, info = self.model.transcribe(
                audio_buffer,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                # These settings can help reduce CPU blocking:
                without_timestamps=True,  # Faster processing
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
            segments, info = self.model.transcribe(
                chunk.data,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                without_timestamps=True
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

