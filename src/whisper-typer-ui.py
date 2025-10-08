#!/usr/bin/env python3
"""Whisper Typer UI - Cross-platform voice dictation application."""

import sys
import threading
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


class WhisperTyperApp:
    """Main application controller."""
    
    def __init__(self):
        """Initialize application."""
        print("Initializing Whisper Typer UI...")
        
        # Load configuration
        try:
            self.config = AppConfig("config.yaml")
            print(f"Loaded configuration:")
            print(f"  - Language: {self.config.primary_language}")
            print(f"  - Hotkey: {self.config.hotkey_combo}")
            print(f"  - Model: {self.config.model_size} ({self.config.compute_type})")
        except ConfigError as e:
            print(f"Configuration error: {e}")
            sys.exit(1)
        
        # Initialize components
        self.session_state = SessionState.IDLE
        self.audio_buffer = None
        
        # Initialize UI in main thread (tkinter requirement)
        self.ui = UIOverlay()
        
        # Initialize audio recorder
        try:
            self.recorder = AudioRecorder()
            print("Microphone initialized successfully")
        except MicrophoneError as e:
            print(f"Microphone error: {e}")
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
            print(f"Model loading error: {e}")
            sys.exit(1)
        
        # Initialize text inserter
        self.text_inserter = TextInserter()
        
        # Initialize hotkey manager
        try:
            self.hotkey_mgr = HotkeyManager(self.config.hotkey_combo)
            self.hotkey_mgr.register(self.on_hotkey_press)
            print(f"Hotkey registered: {self.config.hotkey_combo}")
        except ValueError as e:
            print(f"Hotkey registration error: {e}")
            sys.exit(1)
        
        # Set click callback for UI
        self.ui.set_click_callback(self.on_ui_click)
        
        print("\nApplication ready!")
        print(f"Press {self.config.hotkey_combo} to start recording")
    
    def on_hotkey_press(self) -> None:
        """Handle hotkey press event."""
        if self.session_state == SessionState.IDLE:
            # Start recording
            self.start_recording()
        elif self.session_state == SessionState.RECORDING:
            # Stop recording
            self.stop_recording()
        elif self.session_state == SessionState.TRANSCRIBING:
            # Ignore - transcription in progress
            return
    
    def on_ui_click(self) -> None:
        """Handle UI click event."""
        if self.session_state == SessionState.RECORDING:
            # Click to stop recording
            self.stop_recording()
    
    def start_recording(self) -> None:
        """Start recording session."""
        try:
            print("\n[RECORDING STARTED]")
            self.session_state = SessionState.RECORDING
            
            # Start audio recording
            self.recorder.start_recording()
            
            # Show UI with microphone icon and pulsation
            self.ui.show()
            self.ui.set_border_color('#ff4444')  # Bright red
            self.ui.set_icon(IconType.MICROPHONE)
            self.ui.start_pulsation()
            
            print(f"Recording... (Press {self.config.hotkey_combo} or click to stop)")
            
        except MicrophoneError as e:
            print(f"Error starting recording: {e}")
            self.ui.show_error(f"Microphone error: {e.error_code}", duration=2.5)
            self.session_state = SessionState.ERROR
    
    def stop_recording(self) -> None:
        """Stop recording session."""
        print("[RECORDING STOPPED]")
        
        # Stop audio recording
        self.audio_buffer = self.recorder.stop_recording()
        
        # Stop pulsation
        self.ui.stop_pulsation()
        
        # Change state to transcribing
        self.session_state = SessionState.TRANSCRIBING
        
        audio_length = len(self.audio_buffer) / self.recorder.sample_rate
        print(f"Recorded {audio_length:.2f} seconds of audio")
        
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
            print("[TRANSCRIPTION STARTED]")
            
            # Force UI update before starting heavy computation
            self.ui.window.update_idletasks()
            
            result = self.transcriber.transcribe(self.audio_buffer)
            print("[TRANSCRIPTION COMPLETED]")
            
            # Force UI update after transcription
            self.ui.window.update_idletasks()
            
            # Clean up audio buffer immediately (FR-026, FR-027)
            self.audio_buffer = None
            
            # Insert text if not empty
            if result.text:
                print("[TEXT INSERTION STARTED]")
                self.session_state = SessionState.INSERTING
                
                # Type text in worker thread (it's already in worker thread)
                self.text_inserter.type_text(result.text)
                
                print("[TEXT INSERTION COMPLETED]")
                self.session_state = SessionState.COMPLETED
                
                # Schedule UI hide after short delay
                self.ui.window.after(300, self.ui.hide)
            else:
                print("Empty transcription - no text to insert")
                self.session_state = SessionState.COMPLETED
                self.ui.hide()
            
        except TranscriptionError as e:
            print(f"Transcription error: {e}")
            self.ui.stop_rotation()
            self.ui.show_error("Transcription failed", duration=2.5)
            self.session_state = SessionState.ERROR
        except Exception as e:
            print(f"Unexpected error: {e}")
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
            print("Ready for next recording\n")
    
    def run(self) -> None:
        """Run the application."""
        # Start hotkey listener in background thread
        hotkey_thread = threading.Thread(target=self.hotkey_mgr.start, daemon=True)
        hotkey_thread.start()
        
        # Run tkinter main loop in main thread (required)
        try:
            self.ui.run()
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.hotkey_mgr.stop()
            sys.exit(0)


def main():
    """Application entry point."""
    app = WhisperTyperApp()
    app.run()


if __name__ == "__main__":
    main()
