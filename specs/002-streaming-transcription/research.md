# Research: Streaming Audio Transcription

**Feature**: 002-streaming-transcription  
**Date**: 2025-10-08  
**Status**: Complete

## Overview

This document resolves technical unknowns for implementing chunked streaming transcription. All decisions prioritize **simplicity** and **existing tech stack compatibility**.

---

## 1. Chunking Strategy

### Decision: Time-based fixed-duration chunking with manual buffer slicing

**Implementation**:
- Main recording thread tracks elapsed time
- Every 30 seconds (configurable), slice current audio buffer
- Create AudioChunk object with sequence number and buffer copy
- Put chunk in queue.Queue (thread-safe, built-in Python)

**Rationale**:
- Simplest approach: no complex audio segmentation logic
- `queue.Queue` is thread-safe and built into Python stdlib
- NumPy array slicing is trivial: `audio_buffer[start:end].copy()`
- Time-based chunking aligns with user expectations

**Alternatives Considered**:
- **Voice Activity Detection (VAD) boundaries**: More complex, requires additional processing, may not align with 30s target
- **Sliding window with overlap**: Adds complexity, harder to maintain insertion order
- **Dynamic chunk sizing**: Unpredictable latency, violates simplicity principle

**Code Pattern**:
```python
# In AudioRecorder class
def get_chunk_if_ready(self, chunk_duration_sec: int) -> np.ndarray | None:
    elapsed = time.time() - self.chunk_start_time
    if elapsed >= chunk_duration_sec:
        chunk = np.concatenate(self._recording, axis=0).flatten()
        self._recording.clear()
        self.chunk_start_time = time.time()
        return chunk
    return None
```

---

## 2. Parallel Transcription Architecture

### Decision: ThreadPoolExecutor with fixed worker pool (3 threads)

**Implementation**:
- Use `concurrent.futures.ThreadPoolExecutor(max_workers=3)`
- Submit chunks to executor as they become available
- Each worker runs `transcriber.transcribe(chunk_audio)`
- Workers return (sequence_number, TranscriptionResult) tuple

**Rationale**:
- Built-in Python stdlib, no external dependencies
- Thread pool prevents resource exhaustion (max 3 concurrent transcriptions)
- Simple submit/future pattern, no async/await complexity
- faster-whisper releases GIL during model inference (threading is effective)

**Alternatives Considered**:
- **multiprocessing.Pool**: Heavier (process overhead), model must reload in each process
- **asyncio**: Unnecessary complexity, faster-whisper is blocking anyway
- **Manual threading with Thread class**: Requires manual worker lifecycle management

**Code Pattern**:
```python
from concurrent.futures import ThreadPoolExecutor, Future

executor = ThreadPoolExecutor(max_workers=3)

def transcribe_chunk(seq: int, audio: np.ndarray) -> tuple[int, TranscriptionResult]:
    result = transcriber.transcribe(audio)
    return (seq, result)

# Submit chunk
future: Future = executor.submit(transcribe_chunk, chunk.sequence, chunk.audio)
futures[chunk.sequence] = future
```

---

## 3. Ordered Text Insertion

### Decision: Buffer completed chunks in dict, insert only when all prior chunks ready

**Implementation**:
- Maintain `completed_chunks: dict[int, TranscriptionResult]` (sequence → result)
- Track `next_sequence_to_insert: int` (starts at 0)
- When chunk N completes:
  - Store in `completed_chunks[N]`
  - While `next_sequence_to_insert` exists in `completed_chunks`:
    - Insert text from `completed_chunks[next_sequence_to_insert]`
    - Increment `next_sequence_to_insert`
    - Delete from `completed_chunks` (free memory)

**Rationale**:
- Simplest in-order delivery: dictionary lookup O(1)
- No sorting required, just sequential check
- Memory efficient: only buffers out-of-order chunks
- Clear invariant: always insert sequence 0, 1, 2, 3...

**Alternatives Considered**:
- **Priority queue (heapq)**: Overkill, we only need sequential delivery
- **Lock-based sequential insertion**: Blocks workers, reduces parallelism
- **Insert immediately (out of order)**: Violates clarification answer #1

**Code Pattern**:
```python
completed_chunks: dict[int, str] = {}
next_to_insert = 0

def on_chunk_complete(seq: int, text: str):
    completed_chunks[seq] = text
    
    while next_to_insert in completed_chunks:
        insert_text(completed_chunks[next_to_insert])
        del completed_chunks[next_to_insert]
        next_to_insert += 1
```

---

## 4. Error Handling Strategy

### Decision: Fail-fast on any chunk transcription error

**Implementation**:
- Wrap `transcriber.transcribe()` in try/except
- On exception:
  - Cancel all pending futures in executor
  - Clear chunk queue
  - Show error in UI (existing error handling from feature 001)
  - Discard all completed but not-yet-inserted chunks

**Rationale**:
- Simplest error model: all-or-nothing
- Matches clarification answer #2 (stop all, show error, discard)
- No complex retry logic or partial result handling
- User gets clear feedback: "transcription failed, try again"

**Alternatives Considered**:
- **Retry failed chunk**: Adds complexity, may fail again
- **Skip failed chunk, continue**: Violates clarification, produces incomplete text
- **Insert partial results**: Confusing UX (text stops mid-sentence)

**Code Pattern**:
```python
try:
    result = self.transcriber.transcribe(audio)
except Exception as e:
    # Cancel all pending work
    for future in pending_futures:
        future.cancel()
    chunk_queue.clear()
    completed_chunks.clear()
    raise TranscriptionError(f"Chunk {seq} failed: {e}")
```

---

## 5. Partial Chunk Handling

### Decision: Treat partial chunk as regular chunk with shorter duration

**Implementation**:
- When user stops recording mid-chunk:
  - Take whatever audio is in current buffer
  - Create final chunk with actual duration (e.g., 15 seconds instead of 30)
  - Submit to executor with next sequence number
  - Wait for all chunks (including partial) before finishing

**Rationale**:
- No special case logic needed: partial chunk is just shorter
- faster-whisper handles variable-length audio naturally
- Matches clarification answer #4 (transcribe and insert partial chunk)

**Alternatives Considered**:
- **Discard partial chunk**: Loses last 15 seconds of dictation (bad UX)
- **Merge with previous chunk**: Requires re-transcription, complex timing

**Code Pattern**:
```python
def stop_recording(self) -> None:
    # Flush any remaining audio as final chunk
    if self._recording:
        final_chunk = np.concatenate(self._recording, axis=0).flatten()
        if len(final_chunk) > 0:
            self.queue_chunk(final_chunk)
    self._recording.clear()
```

---

## 6. Session Overlap Prevention

### Decision: Block hotkey until all chunks from previous session are processed

**Implementation**:
- Add `is_processing: bool` flag to main app state
- Set `is_processing = True` when recording starts
- Hotkey handler checks flag: if True, ignore keypress
- Set `is_processing = False` only when:
  - All chunks transcribed AND
  - All text inserted AND
  - Executor shutdown complete

**Rationale**:
- Simplest concurrency control: single boolean flag
- Matches clarification answer #5 (ignore hotkey while processing)
- Prevents resource conflicts (executor, transcriber model)
- No complex queuing of multiple sessions

**Alternatives Considered**:
- **Queue new sessions**: Complex state machine, unclear UX
- **Cancel previous session**: Loses user's dictation (bad UX)
- **Allow overlap with separate executors**: Potential out-of-memory, model contention

**Code Pattern**:
```python
class DictationApp:
    def __init__(self):
        self.is_processing = False
    
    def on_hotkey(self):
        if self.is_processing:
            return  # Ignore keypress
        
        self.is_processing = True
        # ... start recording and transcription
    
    def on_all_chunks_inserted(self):
        self.executor.shutdown(wait=False)
        self.is_processing = False
```

---

## 7. Configuration Extension

### Decision: Add single config parameter `chunk_duration` with validation

**Implementation**:
- Add to `config.yaml`: `chunk_duration: 30` (seconds)
- Load in `AppConfig` class (existing from feature 001)
- Validate: must be positive integer
- Default: 30 seconds if missing or invalid
- Log warning if invalid value provided

**Rationale**:
- Minimal configuration surface: one new parameter
- Reuses existing config loading infrastructure
- Simple validation: `if chunk_duration <= 0: use default`

**Alternatives Considered**:
- **Add max_workers config**: Over-configuration, 3 is reasonable default
- **Add buffer_size config**: Implementation detail, not user-facing concern

**Code Pattern**:
```python
# In config.py
class AppConfig:
    def __init__(self, config_path: str):
        # ... existing config loading ...
        self.chunk_duration = self._validate_chunk_duration(
            config_data.get('chunk_duration', 30)
        )
    
    def _validate_chunk_duration(self, value: int) -> int:
        if not isinstance(value, int) or value <= 0:
            print(f"WARNING: Invalid chunk_duration {value}, using default 30")
            return 30
        return value
```

---

## 8. Existing Stack Compatibility

### Decision: Extend existing modules, no new dependencies

**Modifications Required**:

1. **audio_recorder.py**:
   - Add `get_chunk_if_ready()` method
   - Track `chunk_start_time` internally
   - Support partial chunk extraction on stop

2. **transcriber.py**:
   - No changes needed (already supports variable-length audio)

3. **text_inserter.py**:
   - No changes needed (already supports incremental insertion)

4. **whisper-typer-ui.py** (main):
   - Add ThreadPoolExecutor setup
   - Add chunk queue management
   - Add ordered insertion logic
   - Add session overlap flag

5. **config.py**:
   - Add `chunk_duration` field to AppConfig

**New Dependencies**: None (uses only Python stdlib)

**Rationale**:
- Minimizes changes to existing, working code
- No new external dependencies (Constitution compliance)
- Existing abstractions (AudioRecorder, Transcriber) already well-suited

---

## Summary

All technical decisions prioritize:
- ✅ **Simplicity**: stdlib only, no async, straightforward logic
- ✅ **Existing stack**: Extends current Python/faster-whisper/tkinter implementation
- ✅ **Constitution compliance**: No tests, no new deps, minimal config
- ✅ **Clarification answers**: All 5 answers directly addressed in design

**Next Phase**: Data model and API contracts
