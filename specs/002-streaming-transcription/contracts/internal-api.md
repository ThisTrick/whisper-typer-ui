# Internal API Contracts: Streaming Audio Transcription

**Feature**: 002-streaming-transcription  
**Date**: 2025-10-08

## Overview

This document defines the internal Python API contracts (function signatures, class interfaces) for streaming transcription. All APIs are internal (no external HTTP/REST endpoints).

---

## 1. AudioRecorder API Extensions

### 1.1 get_chunk_if_ready

Extract audio chunk when duration threshold is reached.

**Signature**:

```python
def get_chunk_if_ready(self, chunk_duration_sec: int) -> AudioChunk | None
```

**Parameters**:

- `chunk_duration_sec: int` - Chunk duration threshold in seconds (from config)

**Returns**:

- `AudioChunk` - Chunk object with sequence number and audio buffer, if duration reached
- `None` - If chunk duration threshold not yet reached

**Side Effects**:

- Clears internal `self._recording` buffer when chunk returned
- Resets `self.chunk_start_time` to current time
- Increments `self.current_sequence` counter

**Preconditions**:

- `start_recording()` must have been called
- `chunk_duration_sec > 0`

**Example Usage**:

```python
# In main loop (called every 100ms)
chunk = audio_recorder.get_chunk_if_ready(chunk_duration=30)
if chunk is not None:
    chunk_queue.put(chunk)
```

---

### 1.2 get_final_chunk

Extract remaining audio as final chunk when recording stops.

**Signature**:

```python
def get_final_chunk(self) -> AudioChunk | None
```

**Returns**:

- `AudioChunk` - Final chunk with remaining audio (may be shorter than normal chunk_duration)
- `None` - If no audio remaining in buffer

**Side Effects**:

- Clears `self._recording` buffer
- Sets `self.chunk_start_time = None`
- Does NOT stop the stream (call `stop_recording()` first)

**Preconditions**:

- `stop_recording()` must be called first to stop the audio stream
- Recording was previously active

**Example**:

```python
# User stopped recording  
audio_recorder.stop_recording()  # Stops stream (existing method)
final_chunk = audio_recorder.get_final_chunk()  # NEW: Extract partial chunk
if final_chunk is not None:
    session.submit_chunk(final_chunk)
```

---

## 2. StreamingSession API

### 2.1 Constructor

**Signature**:

```python
def __init__(
    self,
    chunk_duration: int,
    transcriber: Transcriber,
    text_inserter: TextInserter,
    ui_overlay: UIOverlay
)
```

**Parameters**:

- `chunk_duration: int` - Seconds per chunk (from AppConfig.chunk_duration)
- `transcriber: Transcriber` - Shared transcriber instance (from main app)
- `text_inserter: TextInserter` - Shared text inserter (from main app)
- `ui_overlay: UIOverlay` - Shared UI instance (from main app)

**Initializes**:

- `chunk_queue: queue.Queue[AudioChunk]` - Empty queue
- `executor: ThreadPoolExecutor(max_workers=3)` - Worker pool
- `pending_futures: dict[int, Future]` - Empty dict
- `completed_chunks: dict[int, str]` - Empty dict
- `next_sequence_to_insert: int = 0` - Start from sequence 0
- `total_chunks_created: int = 0` - No chunks yet

---

### 2.2 submit_chunk

Queue audio chunk for transcription.

**Signature**:

```python
def submit_chunk(self, chunk: AudioChunk) -> None
```

**Parameters**:

- `chunk: AudioChunk` - Chunk to transcribe

**Side Effects**:

- Submits `_transcribe_chunk_worker()` to executor
- Stores Future in `pending_futures[chunk.sequence]`
- Increments `total_chunks_created`
- Registers Future callback for `_on_chunk_complete()`

**Raises**:

- No exceptions (executor handles worker errors via Future)

**Example Usage**:

```python
chunk = audio_recorder.get_chunk_if_ready(30)
if chunk is not None:
    session.submit_chunk(chunk)
```

---

### 2.3 _transcribe_chunk_worker (private)

Worker function executed in thread pool.

**Signature**:

```python
def _transcribe_chunk_worker(self, chunk: AudioChunk) -> ChunkTranscriptionResult
```

**Parameters**:

- `chunk: AudioChunk` - Chunk to transcribe

**Returns**:

- `ChunkTranscriptionResult` - Result with sequence, text, processing_time

**Raises**:

- `TranscriptionError` - If faster-whisper fails (caught by executor, propagates to Future)

**Concurrency**:

- Executed in worker thread (not main thread)
- Up to 3 concurrent executions

**Example Implementation**:

```python
def _transcribe_chunk_worker(self, chunk: AudioChunk) -> ChunkTranscriptionResult:
    try:
        result = self.transcriber.transcribe(chunk.audio_buffer)
        return ChunkTranscriptionResult(
            sequence=chunk.sequence,
            text=result.text,
            processing_time=result.processing_time
        )
    except Exception as e:
        raise TranscriptionError(f"Chunk {chunk.sequence} failed: {e}")
```

---

### 2.4 _on_chunk_complete (private)

Callback when chunk transcription Future completes.

**Signature**:

```python
def _on_chunk_complete(self, future: Future[ChunkTranscriptionResult]) -> None
```

**Parameters**:

- `future: Future[ChunkTranscriptionResult]` - Completed future from executor

**Side Effects**:

- If successful:
  - Stores text in `completed_chunks[result.sequence]`
  - Calls `_try_insert_ordered()` to insert buffered chunks
  - Removes future from `pending_futures`
- If failed (exception):
  - Cancels all pending futures
  - Clears queues and buffers
  - Shows error in UI
  - Sets state to ERROR

**Concurrency**:

- Callback executed on main thread (executor ensures this)

---

### 2.5 _try_insert_ordered (private)

Insert all sequential completed chunks starting from next expected sequence.

**Signature**:

```python
def _try_insert_ordered(self) -> None
```

**Side Effects**:

- While `next_sequence_to_insert` exists in `completed_chunks`:
  - Extract text for `next_sequence_to_insert`
  - Call `self.text_inserter.insert_text(text)`
  - Delete entry from `completed_chunks`
  - Increment `next_sequence_to_insert`

**Invariant**:

Maintains ordered text insertion: chunk 0, then 1, then 2, etc.

**Example Logic**:

```python
def _try_insert_ordered(self) -> None:
    while self.next_sequence_to_insert in self.completed_chunks:
        text = self.completed_chunks[self.next_sequence_to_insert]
        if text:  # Skip empty (silent) chunks
            self.text_inserter.type_text(text)  # Use existing method name
        
        del self.completed_chunks[self.next_sequence_to_insert]
        self.next_sequence_to_insert += 1
```

---

### 2.6 wait_for_completion

Block until all chunks transcribed and inserted.

**Signature**:

```python
def wait_for_completion(self) -> None
```

**Side Effects**:

- Waits for all `pending_futures` to complete
- Ensures all buffered chunks inserted via `_try_insert_ordered()`
- Shuts down executor

**Raises**:

- `TranscriptionError` - If any chunk failed

**Example Usage**:

```python
# User stopped recording
final_chunk = audio_recorder.get_final_chunk()
if final_chunk is not None:
    session.submit_chunk(final_chunk)

session.wait_for_completion()  # Block until all done
ui_overlay.hide()
```

---

## 3. AppConfig API Extension

### 3.1 chunk_duration property

**Type**: `int`  
**Default**: `30` (seconds)  
**Validation**: Must be positive integer, otherwise defaults to 30 with warning log

**Example config.yaml**:

```yaml
chunk_duration: 30
```

**Access**:

```python
config = AppConfig(config_path="config.yaml")
chunk_duration = config.chunk_duration  # int, validated
```

---

## 4. DictationApp API Extensions

### 4.1 on_hotkey_pressed (modified)

**Changes**:

- Check `self.is_processing` flag before starting new session
- If `is_processing == True`, ignore hotkey (return early)
- Set `is_processing = True` when starting session
- Keep `is_processing = True` until `wait_for_completion()` finishes

**Updated Signature** (internal method):

```python
def on_hotkey_press(self) -> None  # Existing method name
```

**Example Logic**:

```python
def on_hotkey_press(self) -> None:  # Keep existing name
    if self.is_processing:
        return  # Ignore (FR-012)
    
    if self.session_state == SessionState.IDLE:  # Use existing state
        # Start recording
        self.is_processing = True
        self.current_session = StreamingSession(...)
        self.audio_recorder.start_recording()
        self._start_chunk_polling()  # Begin periodic chunk extraction
    elif self.session_state == SessionState.RECORDING:  # Use existing state
        # Stop recording
        self.audio_recorder.stop_recording()
        final_chunk = self.audio_recorder.get_final_chunk()
        if final_chunk:
            self.current_session.submit_chunk(final_chunk)
        
        # Wait for all chunks (blocks main thread briefly)
        self.current_session.wait_for_completion()
        self.current_session = None
        self.is_processing = False
        self.ui_overlay.hide()
```

---

### 4.2 _start_chunk_polling (new private method)

Start periodic polling to extract chunks during recording.

**Signature**:

```python
def _start_chunk_polling(self) -> None
```

**Side Effects**:

- Schedules `_poll_chunk()` to run every 100ms via tkinter.after()

**Example**:

```python
def _start_chunk_polling(self) -> None:
    self._poll_chunk()

def _poll_chunk(self) -> None:
    if self.current_session is None:
        return  # Recording stopped
    
    chunk = self.audio_recorder.get_chunk_if_ready(
        self.config.chunk_duration
    )
    if chunk is not None:
        self.current_session.submit_chunk(chunk)
    
    # Schedule next poll
    self.window.after(100, self._poll_chunk)  # 100ms polling
```

---

## 5. Error Handling Contracts

### 5.1 TranscriptionError

**Raised When**:

- Any chunk transcription fails in worker thread
- faster-whisper raises exception

**Handling**:

- Caught in `_on_chunk_complete()` callback
- Cancels all pending futures
- Clears chunk_queue and completed_chunks
- Shows error in UI (reuse feature 001 error display)
- Sets session state to ERROR

**Example**:

```python
try:
    result = self.transcriber.transcribe(audio)
except Exception as e:
    raise TranscriptionError(f"Chunk {seq} failed: {e}")
```

---

## 6. Concurrency Contracts

### 6.1 Thread-Safety Guarantees

**Thread-Safe Components** (no locks needed):

- `queue.Queue[AudioChunk]` - Built-in thread-safe
- `ThreadPoolExecutor` - Internal synchronization
- `Future` objects - Thread-safe

**Single-Writer Components** (main thread only, no locks needed):

- `pending_futures` dict
- `completed_chunks` dict
- `next_sequence_to_insert` counter
- `is_processing` flag

**Read-Only in Workers** (safe):

- `Transcriber` instance (model is read-only during inference)

### 6.2 Executor Contract

**Configuration**:

```python
executor = ThreadPoolExecutor(max_workers=3)
```

**Guarantees**:

- Maximum 3 concurrent `_transcribe_chunk_worker()` executions
- Futures complete on main thread (callbacks run on main thread)
- Graceful shutdown via `executor.shutdown(wait=True)`

---

## 7. Data Flow Summary

```text
Main Thread:
  [AudioRecorder] --get_chunk_if_ready()--> [AudioChunk]
       |
       v
  [chunk_queue.put(chunk)]
       |
       v
  [StreamingSession.submit_chunk(chunk)]
       |
       v
  [executor.submit(_transcribe_chunk_worker, chunk)] --> Future
       |
       v
  [Future.add_done_callback(_on_chunk_complete)]

Worker Thread (3x):
  [_transcribe_chunk_worker(chunk)]
       |
       v
  [transcriber.transcribe(chunk.audio_buffer)]
       |
       v
  [return ChunkTranscriptionResult]
       |
       v
  [Future resolves] --callback--> Main Thread

Main Thread (callback):
  [_on_chunk_complete(future)]
       |
       v
  [completed_chunks[seq] = text]
       |
       v
  [_try_insert_ordered()]
       |
       v
  [text_inserter.insert_text(text)] for seq 0, 1, 2, ...
```

---

## Summary

**New APIs**: 6 new methods, 1 new class (StreamingSession)  
**Modified APIs**: 3 extended classes (AudioRecorder, AppConfig, DictationApp)  
**Thread Model**: Main thread + 3 worker threads (via executor)  
**Thread Safety**: stdlib primitives (Queue, Executor), single-writer pattern  
**Error Handling**: Fail-fast on any chunk error, graceful cleanup
