#!/usr/bin/env python3
"""Whisper Typer UI - Cross-platform voice dictation application."""

import logging
import sys
import threading
import time
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import AppConfig, ConfigError
from hotkey_manager import HotkeyManager
from audio_recorder import AudioRecorder
from ui_overlay import UIOverlay, IconType
from utils import SessionState, MicrophoneError, TranscriptionError, ModelLoadError
from transcriber import Transcriber
from text_inserter import TextInserter
from streaming_session import StreamingSession


logger = logging.getLogger(__name__)


class WhisperTyperApp:
    """Main application controller."""
    
    def __init__(self):
        """Initialize application."""
        logger.info("Initializing Whisper Typer UI...")
        
        # Load configuration
        try:
            self.config = AppConfig()
            logger.info("Loaded configuration:")
            logger.info(f"  - Config file: {self.config.config_path}")
            logger.info(f"  - Language: {self.config.primary_language}")
            logger.info(f"  - Hotkey: {self.config.hotkey_combo}")
            logger.info(f"  - Model: {self.config.model_size} ({self.config.compute_type})")
        except ConfigError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        
        # Initialize components
        self.session_state = SessionState.IDLE
        self.audio_buffer = None
        
        # Streaming session management
        self.streaming_session: StreamingSession | None = None
        self.is_processing = False  # Flag to prevent overlapping sessions
        self._pending_insertions = 0  # Track pending text insertions
        self._insertion_lock = threading.Lock()
        
        # Initialize UI in main thread (tkinter requirement)
        self.ui = UIOverlay()
        
        # Initialize audio recorder
        try:
            self.recorder = AudioRecorder()
            logger.info("Microphone initialized successfully")
        except MicrophoneError as e:
            logger.error(f"Microphone error: {e}")
            sys.exit(1)
        
        # Initialize transcriber
        try:
            self.transcriber = Transcriber(
                model_size=self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
                language=self.config.primary_language,
                beam_size=self.config.beam_size,
                vad_filter=self.config.vad_filter
            )
        except ModelLoadError as e:
            logger.error(f"Model loading error: {e}")
            sys.exit(1)
        
        # Initialize text inserter
        self.text_inserter = TextInserter()
        
        # Initialize hotkey manager
        try:
            self.hotkey_mgr = HotkeyManager(self.config.hotkey_combo)
            self.hotkey_mgr.register(self.on_hotkey_press)
            logger.info(f"Hotkey registered: {self.config.hotkey_combo}")
        except ValueError as e:
            logger.error(f"Hotkey registration error: {e}")
            sys.exit(1)
        
        # Set click callback for UI
        self.ui.set_click_callback(self.on_ui_click)
        
        logger.info("Application ready!")
        logger.info(f"Press {self.config.hotkey_combo} to start recording")
    
    def on_hotkey_press(self) -> None:
        """Handle hotkey press event."""
        if self.session_state == SessionState.IDLE and not self.is_processing:
            # Start recording with streaming transcription
            self.start_streaming_recording()
        elif self.session_state == SessionState.RECORDING:
            # Stop recording and finalize streaming transcription
            self.stop_streaming_recording()
        elif self.session_state == SessionState.TRANSCRIBING:
            # Ignore - transcription in progress
            return
    
    def on_ui_click(self) -> None:
        """Handle UI click event."""
        if self.session_state == SessionState.RECORDING:
            # Click to stop recording
            self.stop_streaming_recording()
    
    def start_streaming_recording(self) -> None:
        """Start streaming recording session with parallel transcription."""
        try:
            logger.info("[STREAMING RECORDING STARTED]")
            self.session_state = SessionState.RECORDING
            self.is_processing = True
            
            # Initialize streaming session with thread-safe text insertion wrapper
            self.streaming_session = StreamingSession(
                transcribe_fn=self.transcriber.transcribe_chunk,
                insert_text_fn=self.insert_text_safe,  # Use thread-safe wrapper
                on_error=self.on_streaming_error
            )
            
            # Start audio recording
            self.recorder.start_recording()
            
            # Show UI with microphone icon and pulsation
            self.ui.show()
            self.ui.set_border_color('#ff4444')  # Bright red
            self.ui.set_icon(IconType.MICROPHONE)
            self.ui.start_pulsation()
            
            logger.info(f"Recording... (Press {self.config.hotkey_combo} or click to stop)")
            logger.info(f"Chunks will be transcribed every {self.config.chunk_duration} seconds")
            
            # Start chunk extraction loop in background thread
            chunk_thread = threading.Thread(
                target=self.chunk_extraction_loop,
                daemon=True
            )
            chunk_thread.start()
            
        except MicrophoneError as e:
            logger.error(f"Error starting recording: {e}")
            self.ui.show_error(f"Microphone error: {e.error_code}", duration=2.5)
            self.session_state = SessionState.ERROR
            self.is_processing = False
    
    def chunk_extraction_loop(self) -> None:
        """Continuously extract and submit chunks during recording."""
        try:
            while self.session_state == SessionState.RECORDING:
                # Wait for chunk duration
                time.sleep(self.config.chunk_duration)
                
                # Check if still recording
                if self.session_state != SessionState.RECORDING:
                    break
                
                # Extract chunk from recorder
                chunk = self.recorder.extract_chunk()
                
                logger.info(f"[CHUNK {chunk.sequence}] Extracted {len(chunk.data) / self.recorder.sample_rate:.2f}s audio, submitting for transcription")
                
                # Submit to streaming session
                if self.streaming_session:
                    self.streaming_session.submit_chunk(chunk)
                    
        except Exception as e:
            logger.error(f"Error in chunk extraction loop: {e}")
            self.on_streaming_error(e)
    
    def insert_text_safe(self, text: str) -> None:
        """Thread-safe wrapper for text insertion.
        
        Schedules text insertion in main thread via tkinter.
        This is required because text_inserter uses clipboard/keyboard
        which may not be thread-safe when called from worker threads.
        
        Args:
            text: Text to insert
        """
        # Increment pending insertions counter
        with self._insertion_lock:
            self._pending_insertions += 1
        
        # Schedule insertion in main thread
        def do_insert():
            try:
                self.text_inserter.type_text(text)
            finally:
                # Decrement counter when done
                with self._insertion_lock:
                    self._pending_insertions -= 1
        
        self.ui.window.after(0, do_insert)
    
    def stop_streaming_recording(self) -> None:
        """Stop streaming recording and finalize transcription."""
        logger.info("[STREAMING RECORDING STOPPED]")
        
        # Change state immediately to stop chunk extraction loop
        self.session_state = SessionState.TRANSCRIBING
        
        # Extract final chunk BEFORE stopping the stream
        # (stop_recording clears the buffer, so we need to extract first)
        final_chunk = self.recorder.extract_chunk()
        
        # Now stop audio recording (closes stream and clears buffer)
        self.recorder.stop_recording()
        
        # Stop pulsation, start rotation
        self.ui.stop_pulsation()
        self.ui.set_icon(IconType.PROCESSING)
        self.ui.set_border_color('#4488ff')  # Bright blue
        self.ui.start_rotation()
        
        logger.info(f"[FINAL CHUNK {final_chunk.sequence}] Extracted {len(final_chunk.data) / self.recorder.sample_rate:.2f}s audio")
        
        # Submit final chunk if it has audio
        if self.streaming_session and len(final_chunk.data) > 0:
            self.streaming_session.submit_chunk(final_chunk)
        
        # Finalize in background thread
        finalize_thread = threading.Thread(
            target=self.finalize_streaming_session,
            daemon=True
        )
        finalize_thread.start()
    
    def finalize_streaming_session(self) -> None:
        """Wait for all chunks to complete and insert remaining text."""
        try:
            logger.info("[FINALIZING STREAMING SESSION]")
            
            if self.streaming_session:
                # This blocks until all chunks complete
                self.streaming_session.finalize_and_insert()
                self.streaming_session = None
            
            # Wait for all pending text insertions to complete
            logger.info("[FINALIZE] Waiting for pending text insertions...")
            max_wait = 50  # Wait up to 5 seconds (50 * 100ms)
            wait_count = 0
            while wait_count < max_wait:
                with self._insertion_lock:
                    if self._pending_insertions == 0:
                        break
                    pending = self._pending_insertions
                logger.info(f"[FINALIZE] {pending} insertions pending, waiting...")
                time.sleep(0.1)
                wait_count += 1
            
            with self._insertion_lock:
                if self._pending_insertions > 0:
                    logger.warning(f"[FINALIZE] WARNING: {self._pending_insertions} insertions still pending after timeout")
                else:
                    logger.info("[FINALIZE] All text insertions completed")
            
            logger.info("[STREAMING SESSION COMPLETED]")
            
            # Schedule UI hide after short delay
            self.ui.window.after(300, self.ui.hide)
            
        except Exception as e:
            logger.error(f"Error finalizing streaming session: {e}")
            self.ui.show_error("Finalization failed", duration=2.5)
        finally:
            # Stop rotation
            self.ui.stop_rotation()
            # Reset state
            self.session_state = SessionState.IDLE
            self.is_processing = False
            logger.info("Ready for next recording")
    
    def on_streaming_error(self, error: Exception) -> None:
        """Handle errors during streaming transcription."""
        logger.error(f"Streaming error: {error}")
        
        # Stop UI animations
        self.ui.stop_rotation()
        self.ui.stop_pulsation()
        
        # Show error to user
        self.ui.show_error("Transcription failed", duration=2.5)
        
        # Clean up session
        self.streaming_session = None
        self.session_state = SessionState.ERROR
        self.is_processing = False
        
        # Schedule state reset
        def reset_to_idle():
            self.session_state = SessionState.IDLE
            logger.info("Ready for next recording")
        
        self.ui.window.after(2500, reset_to_idle)
    
    def start_recording(self) -> None:
        """Start recording session."""
        try:
            logger.info("[RECORDING STARTED]")
            self.session_state = SessionState.RECORDING
            
            # Start audio recording
            self.recorder.start_recording()
            
            # Show UI with microphone icon and pulsation
            self.ui.show()
            self.ui.set_border_color('#ff4444')  # Bright red
            self.ui.set_icon(IconType.MICROPHONE)
            self.ui.start_pulsation()
            
            logger.info(f"Recording... (Press {self.config.hotkey_combo} or click to stop)")
            
        except MicrophoneError as e:
            logger.error(f"Error starting recording: {e}")
            self.ui.show_error(f"Microphone error: {e.error_code}", duration=2.5)
            self.session_state = SessionState.ERROR
    
    def stop_recording(self) -> None:
        """Stop recording session."""
        logger.info("[RECORDING STOPPED]")
        
        # Stop audio recording
        self.audio_buffer = self.recorder.stop_recording()
        
        # Stop pulsation
        self.ui.stop_pulsation()
        
        # Change state to transcribing
        self.session_state = SessionState.TRANSCRIBING
        
        audio_length = len(self.audio_buffer) / self.recorder.sample_rate
        logger.info(f"Recorded {audio_length:.2f} seconds of audio")
        
        # Change UI to processing icon (without pulsation - static border)
        self.ui.set_icon(IconType.PROCESSING)
        self.ui.set_border_color('#4488ff')  # Bright blue
        self.ui.start_rotation()  # Start rotating the processing icon
        
        # Process transcription in worker thread
        transcription_thread = threading.Thread(
            target=self.process_transcription,
            daemon=True
        )
        transcription_thread.start()
    
    def process_transcription(self) -> None:
        """Process transcription and insert text."""
        try:
            # Transcribe audio
            logger.info("[TRANSCRIPTION STARTED]")
            
            # Force UI update before starting heavy computation
            self.ui.window.update_idletasks()
            
            result = self.transcriber.transcribe(self.audio_buffer)
            logger.info("[TRANSCRIPTION COMPLETED]")
            
            # Force UI update after transcription
            self.ui.window.update_idletasks()
            
            # Clean up audio buffer immediately (FR-026, FR-027)
            self.audio_buffer = None
            
            # Insert text if not empty
            if result.text:
                logger.info("[TEXT INSERTION STARTED]")
                self.session_state = SessionState.INSERTING
                
                # Type text in worker thread (it's already in worker thread)
                self.text_inserter.type_text(result.text)
                
                logger.info("[TEXT INSERTION COMPLETED]")
                self.session_state = SessionState.COMPLETED
                
                # Schedule UI hide after short delay
                self.ui.window.after(300, self.ui.hide)
            else:
                logger.info("Empty transcription - no text to insert")
                self.session_state = SessionState.COMPLETED
                self.ui.hide()
            
        except TranscriptionError as e:
            logger.error(f"Transcription error: {e}")
            self.ui.stop_rotation()
            self.ui.show_error("Transcription failed", duration=2.5)
            self.session_state = SessionState.ERROR
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.ui.stop_rotation()
            self.ui.show_error("Error occurred", duration=2.5)
            self.session_state = SessionState.ERROR
        finally:
            # Ensure rotation is stopped
            self.ui.stop_rotation()
            # Ensure audio buffer is cleaned up
            self.audio_buffer = None
            # Return to idle state
            self.session_state = SessionState.IDLE
            logger.info("Ready for next recording")
    
    def run(self) -> None:
        """Run the application."""
        # Start hotkey listener in background thread
        hotkey_thread = threading.Thread(target=self.hotkey_mgr.start, daemon=True)
        hotkey_thread.start()
        
        # Run tkinter main loop in main thread (required)
        try:
            self.ui.run()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.hotkey_mgr.stop()
            sys.exit(0)


def main():
    """Application entry point."""
    app = WhisperTyperApp()
    app.run()


if __name__ == "__main__":
    main()
