"""Audio recorder module for Whisper Typer UI."""

import numpy as np
import sounddevice as sd

from utils import MicrophoneError


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
    
    def is_recording(self) -> bool:
        """Check if currently recording.
        
        Returns:
            True if recording active, False otherwise
        """
        return self._stream is not None and self._stream.active
