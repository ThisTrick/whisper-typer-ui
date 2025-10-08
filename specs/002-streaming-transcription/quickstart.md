# Quickstart: Streaming Audio Transcription Implementation

**Feature**: 002-streaming-transcription  
**Date**: 2025-10-08  
**Est. Time**: 4-6 hours

## Overview

Implement chunked streaming transcription to reduce latency for long-form dictation. This guide provides step-by-step implementation order.

---

## Prerequisites

- Feature 001 (Voice Dictation Application) fully implemented and working
- Existing codebase: `audio_recorder.py`, `transcriber.py`, `text_inserter.py`, `whisper-typer-ui.py`
- Python 3.11+ with existing dependencies (faster-whisper, tkinter, pynput, sounddevice, numpy)

---

## Implementation Steps

### Step 1: Extend AppConfig (15 min)

**File**: `src/config.py`

**Changes**:

1. Add `chunk_duration` field to AppConfig class
2. Add validation method `_validate_chunk_duration()`
3. Update config loading to read `chunk_duration` from YAML

**Code**:

```python
class AppConfig:
    def __init__(self, config_path: str):
        # ... existing config loading ...
        self.chunk_duration = self._validate_chunk_duration(
            config_data.get('chunk_duration', 30)
        )
    
    def _validate_chunk_duration(self, value: Any) -> int:
        if not isinstance(value, int) or value <= 0:
            print(f"WARNING: Invalid chunk_duration {value}, using default 30")
            return 30
        return value
```

**Verification**: Print `config.chunk_duration` during app startup.

---

### Step 2: Update config.yaml (5 min)

**File**: `config.yaml`

**Add**:

```yaml
# Streaming transcription
chunk_duration: 30  # seconds per chunk
```

**Verification**: App loads config without errors.

---

### Step 3: Create AudioChunk Data Class (15 min)

**File**: `src/audio_recorder.py` (add to top of file)

**Code**:

```python
from dataclasses import dataclass
import numpy as np

@dataclass
class AudioChunk:
    """Fixed-duration segment of recorded audio."""
    sequence: int
    audio_buffer: np.ndarray
    duration: float
    start_offset: float
```

**Verification**: Import AudioChunk in Python REPL, create test instance.

---

### Step 4: Extend AudioRecorder (45 min)

**File**: `src/audio_recorder.py`

**Add Attributes** to `__init__`:

```python
self.chunk_start_time: float | None = None
self.current_sequence: int = 0
```

**Modify** `start_recording()`:

```python
def start_recording(self) -> None:
    # ... existing code ...
    self.chunk_start_time = time.time()
    self.current_sequence = 0
```

**Add Methods**:

```python
def get_chunk_if_ready(self, chunk_duration_sec: int) -> AudioChunk | None:
    if self.chunk_start_time is None:
        return None
    
    elapsed = time.time() - self.chunk_start_time
    if elapsed >= chunk_duration_sec:
        chunk_audio = np.concatenate(self._recording, axis=0).flatten()
        chunk = AudioChunk(
            sequence=self.current_sequence,
            audio_buffer=chunk_audio,
            duration=elapsed,
            start_offset=(self.current_sequence * chunk_duration_sec)
        )
        
        self._recording.clear()
        self.chunk_start_time = time.time()
        self.current_sequence += 1
        
        return chunk
    return None

def get_final_chunk(self) -> AudioChunk | None:
    if not self._recording:
        return None
    
    chunk_audio = np.concatenate(self._recording, axis=0).flatten()
    elapsed = time.time() - self.chunk_start_time
    
    chunk = AudioChunk(
        sequence=self.current_sequence,
        audio_buffer=chunk_audio,
        duration=elapsed,
        start_offset=(self.current_sequence * chunk_duration_sec)
    )
    
    self._recording.clear()
    self.chunk_start_time = None
    
    return chunk
```

**Verification**: 
- Start recording, wait 30s, call `get_chunk_if_ready(30)` → should return AudioChunk
- Call again immediately → should return None
- Stop recording, call `get_final_chunk()` → should return partial chunk

---

### Step 5: Create ChunkTranscriptionResult Data Class (10 min)

**File**: `src/utils.py` (or new `src/streaming_types.py`)

**Code**:

```python
@dataclass
class ChunkTranscriptionResult:
    """Result from transcribing a single audio chunk."""
    sequence: int
    text: str
    processing_time: float
```

**Verification**: Import and create test instance.

---

### Step 6: Create StreamingSession Class (90 min)

**File**: `src/streaming_session.py` (new file)

**Full Implementation**:

```python
import queue
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from transcriber import Transcriber
    from text_inserter import TextInserter
    from ui_overlay import UIOverlay

from audio_recorder import AudioChunk
from utils import ChunkTranscriptionResult, TranscriptionError


class StreamingSession:
    """Manages chunked streaming transcription for a single recording session."""
    
    def __init__(
        self,
        chunk_duration: int,
        transcriber: 'Transcriber',
        text_inserter: 'TextInserter',
        ui_overlay: 'UIOverlay'
    ):
        self.chunk_duration = chunk_duration
        self.transcriber = transcriber
        self.text_inserter = text_inserter
        self.ui_overlay = ui_overlay
        
        self.chunk_queue: queue.Queue[AudioChunk] = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.pending_futures: dict[int, Future] = {}
        self.completed_chunks: dict[int, str] = {}
        self.next_sequence_to_insert: int = 0
        self.total_chunks_created: int = 0
        self.has_error: bool = False
    
    def submit_chunk(self, chunk: AudioChunk) -> None:
        """Queue chunk for transcription."""
        future = self.executor.submit(self._transcribe_chunk_worker, chunk)
        self.pending_futures[chunk.sequence] = future
        future.add_done_callback(self._on_chunk_complete)
        self.total_chunks_created += 1
    
    def _transcribe_chunk_worker(self, chunk: AudioChunk) -> ChunkTranscriptionResult:
        """Worker function: transcribe chunk in thread pool."""
        try:
            result = self.transcriber.transcribe(chunk.audio_buffer)
            return ChunkTranscriptionResult(
                sequence=chunk.sequence,
                text=result.text,
                processing_time=result.processing_time
            )
        except Exception as e:
            raise TranscriptionError(f"Chunk {chunk.sequence} failed: {e}")
    
    def _on_chunk_complete(self, future: Future[ChunkTranscriptionResult]) -> None:
        """Callback when chunk transcription completes."""
        try:
            result = future.result()  # May raise if worker failed
            
            # Buffer completed chunk
            self.completed_chunks[result.sequence] = result.text
            
            # Remove from pending
            if result.sequence in self.pending_futures:
                del self.pending_futures[result.sequence]
            
            # Try to insert buffered chunks in order
            self._try_insert_ordered()
            
        except Exception as e:
            # Error handling: cancel all work, show error
            self.has_error = True
            for fut in self.pending_futures.values():
                fut.cancel()
            self.pending_futures.clear()
            self.completed_chunks.clear()
            
            print(f"ERROR: Transcription failed: {e}")
            self.ui_overlay.show_error("Transcription failed")
    
    def _try_insert_ordered(self) -> None:
        """Insert completed chunks in sequence order."""
        while self.next_sequence_to_insert in self.completed_chunks:
            text = self.completed_chunks[self.next_sequence_to_insert]
            if text:  # Skip empty chunks
                self.text_inserter.type_text(text)  # Use existing method name
            
            del self.completed_chunks[self.next_sequence_to_insert]
            self.next_sequence_to_insert += 1
    
    def wait_for_completion(self) -> None:
        """Block until all chunks transcribed and inserted."""
        # Wait for all futures
        for future in self.pending_futures.values():
            try:
                future.result()  # Blocks until done
            except Exception:
                pass  # Already handled in callback
        
        # Final ordered insertion (in case any completed after loop)
        self._try_insert_ordered()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        if self.has_error:
            raise TranscriptionError("Session failed due to chunk error")
```

**Verification**:
- Create session, submit test chunk, wait for completion
- Check that text was inserted

---

### Step 7: Integrate Streaming Session into Main App (60 min)

**File**: `src/whisper-typer-ui.py`

**Add Imports**:

```python
from streaming_session import StreamingSession
```

**Add Attributes** to main app class:

```python
self.is_processing: bool = False
self.current_session: StreamingSession | None = None
```

**Modify Hotkey Handler**:

```python
def on_hotkey_press(self):  # Keep existing method name
    if self.is_processing:
        return  # Ignore (FR-012)
    
    if self.session_state == SessionState.IDLE:  # Use existing state enum
        # Start recording
        self.is_processing = True
        self.session_state = SessionState.RECORDING
        self.current_session = StreamingSession(
            chunk_duration=self.config.chunk_duration,
            transcriber=self.transcriber,
            text_inserter=self.text_inserter,
            ui_overlay=self.ui
        )
        self.recorder.start_recording()
        self.ui.show()
        self.ui.set_icon(IconType.MICROPHONE)
        self.ui.start_pulsation()
        self._start_chunk_polling()
        
    elif self.session_state == SessionState.RECORDING:  # Use existing state enum
        # Stop recording
        self.session_state = SessionState.TRANSCRIBING
        self.recorder.stop_recording()
        final_chunk = self.recorder.get_final_chunk()
        if final_chunk:
            self.current_session.submit_chunk(final_chunk)
        
        self.ui.stop_pulsation()
        self.ui.set_icon(IconType.PROCESSING)
        self.ui.start_rotation()
        
        try:
            self.current_session.wait_for_completion()
        except TranscriptionError as e:
            print(f"ERROR: {e}")
            self.ui.show_error("Transcription failed")
        finally:
            self.current_session = None
            self.is_processing = False
            self.session_state = SessionState.IDLE
            self.ui.stop_rotation()
            self.ui.hide()
```

**Add Chunk Polling**:

```python
def _start_chunk_polling(self):
    """Start periodic chunk extraction."""
    self._poll_chunk()

def _poll_chunk(self):
    """Poll for ready chunks (every 100ms)."""
    if self.session_state != SessionState.RECORDING:  # Use existing state
        return
    
    chunk = self.audio_recorder.get_chunk_if_ready(
        self.config.chunk_duration
    )
    if chunk is not None:
        self.current_session.submit_chunk(chunk)
    
    # Schedule next poll
    self.ui.window.after(100, self._poll_chunk)  # Use existing ui reference
```

**Verification**:
- Start app, press hotkey, record for 90 seconds
- Observe chunks being transcribed every 30 seconds
- Text should appear incrementally (not all at once at end)

---

### Step 8: Final Integration Verification (30 min)

**Manual Tests**:

1. **Short recording (< 30s)**:
   - Start recording
   - Speak for 15 seconds
   - Stop recording
   - Verify: text appears immediately

2. **Multi-chunk recording (60s)**:
   - Start recording
   - Speak for 60 seconds continuously
   - Verify: First chunk's text appears around 35s mark
   - Stop recording
   - Verify: Remaining text appears shortly after

3. **Hotkey blocking**:
   - Start recording
   - Record for 30s (chunk in progress)
   - Press hotkey again immediately
   - Verify: Hotkey ignored until all chunks processed

4. **Partial chunk**:
   - Start recording
   - Speak for 45 seconds
   - Stop recording
   - Verify: 2 chunks transcribed (30s + 15s partial)

5. **Empty chunk**:
   - Start recording
   - Stay silent for 30s
   - Speak for 10s
   - Stop recording
   - Verify: No error, only spoken text inserted

---

## Common Issues & Solutions

### Issue: Chunks not being created

**Symptom**: Recording works but no chunks appear  
**Solution**: Check `_poll_chunk()` is being called (add debug print)

### Issue: Text appears out of order

**Symptom**: Chunk 3 text before chunk 2  
**Solution**: Verify `_try_insert_ordered()` logic (should wait for chunk 2)

### Issue: Hotkey not blocked during processing

**Symptom**: Can start new recording while processing  
**Solution**: Ensure `is_processing = True` set before `start_recording()`

### Issue: Final chunk not transcribed

**Symptom**: Last ~15 seconds missing  
**Solution**: Verify `get_final_chunk()` called in stop handler

---

## Performance Notes

- **First chunk latency**: ~35 seconds (30s recording + 5s transcription)
- **Peak memory**: ~6 MB for 3 concurrent chunks (negligible)
- **CPU usage**: Same as feature 001 (model inference dominates)

---

## Next Steps

After implementation complete:

1. Manual verification of all 5 test scenarios above
2. Update README with streaming transcription feature
3. Commit changes: `git commit -m "feat: add streaming transcription (002)"`
4. Optional: Tune `chunk_duration` based on user feedback

---

## Time Breakdown

| Step | Task | Est. Time |
|------|------|-----------|
| 1 | Extend AppConfig | 15 min |
| 2 | Update config.yaml | 5 min |
| 3 | Create AudioChunk | 15 min |
| 4 | Extend AudioRecorder | 45 min |
| 5 | Create ChunkTranscriptionResult | 10 min |
| 6 | Create StreamingSession | 90 min |
| 7 | Integrate into main app | 60 min |
| 8 | Final verification | 30 min |
| **Total** | | **4.5 hours** |

Add 1-2 hours buffer for debugging and refinement.
