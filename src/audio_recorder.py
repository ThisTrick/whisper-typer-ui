"""Audio recorder module for Whisper Typer UI."""

from dataclasses import dataclass
import numpy as np
import sounddevice as sd

from utils import MicrophoneError


@dataclass
class AudioChunk:
    """Represents a chunk of recorded audio with metadata.
    
    Attributes:
        data: NumPy array of audio samples
        sequence: Sequential chunk number (0-indexed)
        start_time: Recording start time in seconds (relative to session start)
    """
    data: np.ndarray
    sequence: int
    start_time: float


class AudioRecorder:
    """Records audio from microphone into NumPy buffer."""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """Initialize audio recorder.
        
        Args:
            sample_rate: Audio sample rate in Hz (default 16000 for Whisper)
            channels: Number of audio channels (default 1 = mono)
            
        Raises:
            MicrophoneError: If no microphone detected
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self._recording: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        
        # Streaming session metadata (initialized in start_recording)
        self.chunk_start_time: float = 0.0
        self.current_sequence: int = 0
        
        # Verify microphone is available
        try:
            devices = sd.query_devices()
            default_input = sd.query_devices(kind='input')
            if default_input is None:
                raise MicrophoneError(None, "NO_DEVICE")
        except Exception as e:
            if isinstance(e, MicrophoneError):
                raise
            raise MicrophoneError(None, "NO_DEVICE")
    
    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Callback function for audio stream.
        
        Args:
            indata: Incoming audio data
            frames: Number of frames
            time_info: Timing information
            status: Stream status
        """
        if status:
            print(f"Audio stream status: {status}")
        # Copy audio data to buffer
        self._recording.append(indata.copy())
    
    def start_recording(self) -> None:
        """Begin capturing audio into internal buffer.
        
        Raises:
            MicrophoneError: If microphone busy or permissions denied
        """
        try:
            # Clear previous recording
            self._recording = []
            
            # Initialize streaming session metadata
            self.chunk_start_time = 0.0
            self.current_sequence = 0
            
            # Start audio stream
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback
            )
            self._stream.start()
            
        except PermissionError:
            raise MicrophoneError(None, "PERMISSION_DENIED")
        except Exception as e:
            raise MicrophoneError(None, "DEVICE_BUSY")
    
    def stop_recording(self) -> np.ndarray:
        """Stop recording and return captured audio buffer.
        
        Returns:
            Audio samples as float32 array, shape (n_samples,)
            
        Side Effects:
            Internal buffer cleared after return
        """
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        # Concatenate all recorded chunks
        if not self._recording:
            return np.array([], dtype=np.float32)
        
        audio_buffer = np.concatenate(self._recording, axis=0)
        
        # Flatten to 1D if stereo (though we use mono)
        if audio_buffer.ndim > 1:
            audio_buffer = audio_buffer.flatten()
        
        # Clear internal buffer
        self._recording = []
        
        return audio_buffer.astype(np.float32)
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since recording started.
        
        Returns:
            Time in seconds since start_recording() was called
        """
        if not self._recording:
            return 0.0
        
        # Calculate total samples recorded
        total_samples = sum(chunk.shape[0] for chunk in self._recording)
        return total_samples / self.sample_rate
    
    def extract_chunk(self) -> AudioChunk:
        """Extract accumulated audio as a chunk with metadata.
        
        Returns:
            AudioChunk with data, sequence number, and start time
            
        Side Effects:
            - Clears internal _recording buffer
            - Increments current_sequence
            - Updates chunk_start_time to current elapsed time
        """
        # Concatenate all recorded chunks
        if not self._recording:
            audio_data = np.array([], dtype=np.float32)
        else:
            audio_data = np.concatenate(self._recording, axis=0)
            # Flatten to 1D if stereo
            if audio_data.ndim > 1:
                audio_data = audio_data.flatten()
            audio_data = audio_data.astype(np.float32)
        
        # Create chunk with current metadata
        chunk = AudioChunk(
            data=audio_data,
            sequence=self.current_sequence,
            start_time=self.chunk_start_time
        )
        
        # Clear buffer and update metadata
        self._recording = []
        self.current_sequence += 1
        self.chunk_start_time = self.get_elapsed_time()
        
        return chunk
    
    def is_recording(self) -> bool:
        """Check if currently recording.
        
        Returns:
            True if recording active, False otherwise
        """
        return self._stream is not None and self._stream.active
