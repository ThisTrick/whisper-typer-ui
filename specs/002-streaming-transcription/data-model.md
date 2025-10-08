# Data Model: Streaming Audio Transcription

**Feature**: 002-streaming-transcription  
**Date**: 2025-10-08

## Overview

This feature extends the data model from feature 001 (Voice Dictation Application) to support chunked streaming transcription. All entities remain in-memory only (no persistence).

## New Entities

### 1. AudioChunk

Represents a fixed-duration segment of recorded audio queued for transcription.

**Attributes**:

- `sequence: int` - Sequential chunk number (0-indexed, determines insertion order)
- `audio_buffer: np.ndarray` - NumPy array of audio samples for this chunk (16kHz mono float32)
- `duration: float` - Actual duration in seconds (typically 30s, final chunk may be shorter)
- `start_offset: float` - Time offset from recording start (for debugging/logging)

**Lifecycle**:

1. Created when chunk duration threshold reached in AudioRecorder
2. Placed in chunk_queue (thread-safe queue.Queue)
3. Worker thread picks up chunk from queue
4. Worker transcribes chunk → produces ChunkTranscriptionResult
5. AudioChunk deleted after transcription completes (GC frees buffer)

**Validation Rules**:

- `sequence` must be non-negative and monotonically increasing
- `audio_buffer.shape` must be 1-dimensional (mono audio)
- `duration > 0`
- `audio_buffer` freed immediately after transcription

**Memory Management**:

- Maximum ~3 chunks in memory simultaneously (one per worker thread)
- Each 30-second chunk at 16kHz = 30 * 16000 * 4 bytes = ~1.9 MB
- Peak memory: ~6 MB for 3 concurrent chunks (negligible)

---

### 2. ChunkTranscriptionResult

Output from transcribing a single AudioChunk.

**Attributes**:

- `sequence: int` - Original chunk sequence number (for ordered insertion)
- `text: str` - Transcribed text from this chunk (may be empty if silent)
- `processing_time: float` - Transcription duration for this chunk (seconds)

**Usage**:

```python
# Worker thread
def transcribe_chunk(chunk: AudioChunk) -> ChunkTranscriptionResult:
    result = transcriber.transcribe(chunk.audio_buffer)
    return ChunkTranscriptionResult(
        sequence=chunk.sequence,
        text=result.text,
        processing_time=result.processing_time
    )
```

**Validation Rules**:

- `sequence` must match original AudioChunk sequence
- `text` may be empty (silent chunk is valid)
- `processing_time > 0`

---

### 3. StreamingSession

Extends RecordingSession (from feature 001) to manage chunked streaming transcription.

**Additional Attributes** (beyond RecordingSession):

- `chunk_duration: int` - Configured chunk duration in seconds (default 30)
- `chunk_queue: queue.Queue[AudioChunk]` - Thread-safe queue of chunks awaiting transcription
- `executor: ThreadPoolExecutor` - Worker pool (max_workers=3) for parallel transcription
- `pending_futures: dict[int, Future[ChunkTranscriptionResult]]` - Map sequence → Future for tracking
- `completed_chunks: dict[int, str]` - Buffer for out-of-order completed chunks (sequence → text)
- `next_sequence_to_insert: int` - Next chunk sequence expected for insertion (monotonic counter)
- `total_chunks_created: int` - Total chunks queued (for progress tracking/debugging)

**State Extensions**:

Reuses existing SessionState enum from feature 001, but internal sub-states:

- RECORDING: chunks are created and queued continuously
- TRANSCRIBING: recording stopped, waiting for all pending futures to complete
- INSERTING: all chunks transcribed, inserting buffered text in sequence order

**Lifecycle**:

1. User presses hotkey → StreamingSession created (state: RECORDING)
2. Every `chunk_duration` seconds:
   - AudioRecorder produces AudioChunk
   - Chunk added to chunk_queue
   - Executor picks up chunk (if worker available) → Future created
   - Future completion triggers on_chunk_complete()
3. User stops recording → state: TRANSCRIBING
   - Final partial chunk queued
   - Wait for all pending_futures to resolve
4. All chunks complete → state: INSERTING
   - Insert buffered text in sequence order (0, 1, 2, ...)
5. All text inserted → state: COMPLETED
6. StreamingSession deleted (GC frees all buffers)

**Invariants**:

- `next_sequence_to_insert` ≤ `total_chunks_created` (can't insert future chunks)
- `len(pending_futures) ≤ 3` (max 3 concurrent workers)
- `completed_chunks` only contains sequences ≥ `next_sequence_to_insert` (earlier ones already inserted)

**Error Handling**:

- If any Future raises exception → state: ERROR
- All pending Futures cancelled
- chunk_queue cleared
- completed_chunks cleared
- Show error in UI (reuse feature 001 error display)

---

## Modified Entities (from feature 001)

### AppConfig (Extended)

**New Attribute**:

- `chunk_duration: int = 30` - Duration of each audio chunk in seconds

**Validation** (added):

```python
def _validate_chunk_duration(self, value: Any) -> int:
    if not isinstance(value, int) or value <= 0:
        print(f"WARNING: Invalid chunk_duration {value}, using default 30")
        return 30
    return value
```

**Updated config.yaml schema**:

```yaml
# Existing from feature 001
primary_language: "uk"
hotkey: "<ctrl>+<alt>+<space>"
model_size: "medium"
compute_type: "int8"
device: "cpu"
beam_size: 5
vad_filter: true

# NEW: Streaming transcription
chunk_duration: 30  # seconds per chunk (default: 30)
```

---

### AudioRecorder (Extended)

**New Attributes**:

- `chunk_start_time: float | None` - Timestamp when current chunk started recording (None when not recording)
- `current_sequence: int` - Next chunk sequence number to assign

**New Methods**:

```python
def get_chunk_if_ready(self, chunk_duration_sec: int) -> AudioChunk | None:
    """Extract chunk if duration threshold reached.
    
    Returns:
        AudioChunk if ready, None otherwise
        
    Side Effects:
        Clears internal buffer and resets chunk_start_time if chunk returned
    """
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
        
        # Reset for next chunk
        self._recording.clear()
        self.chunk_start_time = time.time()
        self.current_sequence += 1
        
        return chunk
    return None

def get_final_chunk(self) -> AudioChunk | None:
    """Extract any remaining audio as final chunk when recording stops.
    
    Returns:
        AudioChunk with remaining audio, or None if buffer empty
    """
    if not self._recording:
        return None
    
    chunk_audio = np.concatenate(self._recording, axis=0).flatten()
    elapsed = time.time() - self.chunk_start_time
    
    chunk = AudioChunk(
        sequence=self.current_sequence,
        audio_buffer=chunk_audio,
        duration=elapsed,
        start_offset=(self.current_sequence * self.chunk_duration)
    )
    
    self._recording.clear()
    self.chunk_start_time = None
    
    return chunk
```

**Modified Behavior**:

- `start_recording()`: Initialize `chunk_start_time = time.time()`, `current_sequence = 0`
- `stop_recording()`: Keep existing signature (returns np.ndarray), used for non-streaming mode
- Add `get_final_chunk()`: New method to extract partial chunk for streaming mode

---

### DictationApp (Main Application State)

**New Attributes**:

- `is_processing: bool` - True while chunks are being transcribed/inserted (blocks new hotkey presses)
- `current_session: StreamingSession | None` - Active streaming session (None when idle)

**Modified Hotkey Handler** (preserves existing session_state logic):

```python
def on_hotkey_press(self):
    # NEW: Block hotkey during streaming processing
    if self.is_processing:
        return  # Ignore hotkey (FR-012: prevent overlapping sessions)
    
    # EXISTING: Use session_state enum
    if self.session_state == SessionState.IDLE:
        # Start new streaming recording session
        self.is_processing = True
        self.current_session = StreamingSession(...)
        self.start_recording()
    elif self.session_state == SessionState.RECORDING:
        # Stop current session
        self.stop_recording()
        # is_processing remains True until all chunks inserted
```

**Note**: Both `session_state` (existing) and `is_processing` (new) are maintained for compatibility.

---

## Relationships

```text
DictationApp
    └── current_session: StreamingSession
            ├── chunk_queue: Queue[AudioChunk]
            ├── executor: ThreadPoolExecutor
            ├── pending_futures: dict[int, Future[ChunkTranscriptionResult]]
            └── completed_chunks: dict[int, str]

AudioRecorder (singleton)
    └── produces: AudioChunk (every chunk_duration seconds)

ThreadPoolExecutor (3 workers)
    └── consumes: AudioChunk (from chunk_queue)
    └── produces: ChunkTranscriptionResult (via Future)

TextInserter (singleton, reused from feature 001)
    └── consumes: str (from completed_chunks in sequence order)
```

---

## Concurrency Model

**Thread Roles**:

1. **Main Thread**:
   - Runs tkinter event loop (UI)
   - Handles hotkey events
   - Manages AudioRecorder (calls `get_chunk_if_ready()` periodically)
   - Submits chunks to executor
   - Monitors Future completions
   - Performs ordered text insertion

2. **Recording Thread** (from sounddevice):
   - Captures audio samples from microphone
   - Appends to AudioRecorder._recording buffer
   - No access to queue or executor

3. **Worker Threads** (3x from ThreadPoolExecutor):
   - Pick up AudioChunk from queue (via executor.submit)
   - Call transcriber.transcribe(chunk.audio_buffer)
   - Return ChunkTranscriptionResult
   - No UI interaction, no state mutation

**Thread Safety**:

- `queue.Queue`: Built-in thread-safe (no locks needed)
- `ThreadPoolExecutor`: Manages its own internal synchronization
- `pending_futures` dict: Only accessed from main thread (no locks needed)
- `completed_chunks` dict: Only accessed from main thread (via Future callbacks on main thread)
- `is_processing` flag: Only modified from main thread

**No explicit locks required**: Single-writer (main thread) for all shared state except queue (which is thread-safe).

---

## Memory Profile

**Per 10-minute recording (30-second chunks)**:

- Total chunks: 20 chunks (10 * 60 / 30)
- Peak concurrent chunks in memory: 3 (one per worker)
- Chunk size: ~1.9 MB each (30s * 16kHz * 4 bytes)
- Peak memory for chunks: ~6 MB (3 chunks)
- completed_chunks buffer: ~20 KB max (text only, worst case all chunks complete out-of-order)

**Total memory overhead**: < 10 MB (negligible compared to model size ~500 MB)

---

## Summary

**New Entities**: AudioChunk, ChunkTranscriptionResult, StreamingSession  
**Modified Entities**: AppConfig, AudioRecorder, DictationApp  
**No persistence**: All entities in-memory, deleted after session completes  
**Thread-safe**: Uses stdlib thread-safe primitives (Queue, ThreadPoolExecutor)  
**Simple concurrency**: Single-writer main thread, no explicit locks
