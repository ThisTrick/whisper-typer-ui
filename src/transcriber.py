"""Transcription module using faster-whisper."""

import time

import numpy as np
from faster_whisper import WhisperModel

from utils import TranscriptionResult, TranscriptionError, ModelLoadError


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
            print(f"Loading whisper model '{model_size}' ({compute_type} on {device})...")
            self.model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type
            )
            print(f"Model loaded successfully")
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
            
            print(f"Starting transcription of {audio_length:.2f}s audio...")
            
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
            
            print(f"Transcription model finished, collecting segments...")
            
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
            
            print(f"Transcription completed in {processing_time:.2f}s")
            print(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")
            if result.text:
                print(f"Transcribed text: {result.text}")
            else:
                print("No speech detected (empty result)")
            
            return result
            
        except Exception as e:
            raise TranscriptionError(e, audio_length)
