# Feature Specification: Streaming Audio Transcription

**Feature Branch**: `002-streaming-transcription`  
**Created**: 2025-10-08  
**Status**: Draft  
**Input**: User description: "Need a new feature that will split the audio that a person records every 30 seconds, or like, take it every 30 seconds, do transcription in a parallel stream and insert it where needed. Why is this needed? This is needed so that when a person records very long audio recordings, we can efficiently process them, without the person having to wait another 20 minutes after a 10-minute recording for the model to process their recording. Configuration should probably be done through a config file. I specifically mean configuring the length of this batch."

## Overview

This feature extends the existing whisper-typer-ui voice dictation application (feature 001) to support **chunked streaming transcription** for long-form dictation. Instead of waiting until the user stops recording and then transcribing the entire audio buffer at once, the system will automatically split the recording into fixed-duration chunks (configurable, default 30 seconds) and transcribe each chunk in parallel worker threads during the recording session.

### Problem Statement

Current implementation (feature 001) blocks on transcription after recording completes:
- User records 10-minute dictation → stops recording → waits 20 minutes for transcription to complete
- Poor user experience for long recordings
- No incremental feedback during transcription

### Proposed Solution

- Split audio recording into configurable chunks (e.g., 30-second batches)
- Transcribe each chunk in parallel worker threads as they become available
- Insert transcribed text incrementally into the target application as chunks complete
- Continue recording in the main thread without blocking

### Benefits

- **Reduced Perceived Latency**: User sees text appearing during or shortly after speaking, rather than waiting for entire recording to finish
- **Better UX for Long Dictation**: 10-minute recording produces text incrementally instead of blocking for 20+ minutes
- **Configurable Performance**: Users can tune chunk duration to balance latency vs. transcription accuracy

## Clarifications

### Session 2025-10-08

- Q: When multiple chunks finish transcription out of order (e.g., chunk 3 completes before chunk 2), how should the system insert text? → A: Buffer completed chunks and insert only in sequence order (wait for chunk 2 before inserting chunk 3)
- Q: What should happen if one chunk transcription fails (model error, timeout)? → A: Stop all transcription, show error, discard all chunks
- Q: What is the maximum number of parallel workers (transcription threads) the system should support simultaneously? → A: 3 workers (balance between speed and resources)
- Q: What should happen when user stops recording mid-chunk (e.g., at 45 seconds with 30-second chunks)? → A: Transcribe partial chunk (last 15 seconds) and insert its text
- Q: What should happen when user starts a new recording (presses hotkey) while previous chunks are still transcribing? → A: Ignore hotkey (do not react) while previous chunks are being processed
- Q: What happens when chunk duration is very small and transcription takes longer than chunk duration? → A: Chunks queue up in the ThreadPoolExecutor queue (max 3 concurrent). No special handling needed - system continues recording and transcribing available chunks. Queue backlog clears as workers complete.
- Q: What happens when user switches to a non-text field while chunks are still being transcribed? → A: Transcription continues in background. When chunks complete, text insertion attempts but may fail silently if target is not text-compatible. User can switch back to text field if needed. (Acceptable behavior - no blocking required)

## User Scenarios *(mandatory)*

### User Story 1 - Long-Form Dictation with Streaming Transcription (Priority: P1)

User needs to dictate a long document (e.g., 10+ minutes) without waiting for the entire transcription to complete after stopping recording. As the user speaks, the system automatically splits the audio into chunks, transcribes them in parallel, and inserts text incrementally.

**Why this priority**: Core functionality of this feature - without chunked streaming, there is no improvement over the existing implementation.

**Expected Behavior**:

1. Recording is active for more than the configured chunk duration (e.g., 30 seconds) → system splits audio into a new chunk and begins transcribing the previous chunk in a background worker
2. A chunk finishes transcription → transcribed text is inserted into the target application immediately
3. User continues recording beyond multiple chunk boundaries → multiple chunks are transcribed concurrently without blocking the recording thread
4. User stops recording mid-chunk (e.g., at 45 seconds with 30-second chunks) → the partial final chunk is transcribed and inserted

---

### User Story 2 - Configurable Chunk Duration (Priority: P2)

User wants to tune the chunk duration to balance transcription latency and accuracy. Shorter chunks (e.g., 15 seconds) provide faster feedback (text appears within ~20 seconds of speaking) but may reduce accuracy at chunk boundaries due to context truncation; longer chunks (e.g., 60 seconds) improve accuracy by preserving more context but delay feedback (text appears ~65+ seconds after speaking start).

**Why this priority**: Configurability allows users to optimize for their specific use case (fast feedback with 15-30s chunks vs. maximum accuracy with 45-60s chunks).

**Performance Expectations**:
- Chunk transcription time: typically <5 seconds per 30-second chunk on modern hardware (depends on model_size and compute_type settings)
- Target latency: chunk_duration + ~5s processing time = total time until text appears
- Example: 30s chunks → first text within ~35 seconds of recording start

**Expected Behavior**:

1. chunk_duration is set to 30 in config.yaml → user records for 90 seconds → system creates 3 chunks (0-30s, 30-60s, 60-90s)
2. chunk_duration is changed to 60 in config.yaml and application is restarted → user records for 90 seconds → system creates 2 chunks (0-60s, 60-90s)
3. chunk_duration is set to an invalid value (e.g., 0 or negative) → application starts → system uses a default safe value (e.g., 30 seconds) and logs a warning

---

### Edge Cases

- **Clarified**: Chunk duration very small and transcription takes longer → chunks queue up in ThreadPoolExecutor, system continues recording, backlog clears as workers complete
- **Clarified**: User switches to non-text field while chunks transcribing → transcription continues, text insertion may fail silently if target incompatible
- **Clarified**: Multiple chunks finish out of order → buffer completed chunks and insert only in sequence order (wait for chunk 2 before inserting chunk 3)
- **Clarified**: Chunk transcription fails → stop all transcription, show error, discard all chunks
- **Clarified**: User stops recording mid-chunk → transcribe partial chunk and insert its text
- **Clarified**: User starts new recording while previous chunks are transcribing → ignore hotkey (do not react) until all previous chunks are processed

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST split continuous audio recording into fixed-duration chunks based on configured chunk_duration parameter
- **FR-002**: System MUST begin transcribing a chunk as soon as it reaches the configured duration (non-blocking)
- **FR-003**: System MUST transcribe chunks in parallel worker threads without blocking the main recording thread
- **FR-004**: System MUST insert transcribed text from completed chunks into the target application incrementally as they finish
- **FR-005**: System MUST handle the final partial chunk (when user stops recording mid-chunk) by transcribing and inserting it
- **FR-006**: System MUST support configurable chunk_duration parameter in config.yaml (default: 30 seconds)
- **FR-007**: System MUST validate chunk_duration is a positive integer; if invalid, use default (30 seconds)
- **FR-008**: System MUST insert transcribed chunks in recording order (chunk 1 before chunk 2, even if chunk 2 finishes first)
- **FR-009**: System MUST continue recording without interruption while chunks are being transcribed
- **FR-010**: System MUST limit concurrent transcription workers to exactly 3 (balance between speed and resource usage)
- **FR-011**: System MUST stop all transcription and show error if any chunk transcription fails (discard all chunks, do not insert partial results)
- **FR-012**: System MUST ignore hotkey activation while previous recording's chunks are still being transcribed (prevent overlapping sessions)

### Key Entities

- **Audio Chunk**: Fixed-duration segment of recorded audio (e.g., 30 seconds) with sequence number
- **Transcription Worker**: Background thread transcribing a single audio chunk
- **Chunk Queue**: Ordered collection of chunks waiting for transcription

## Implementation Notes

**Simplicity First**:
- Use simple threading (not complex async/await patterns)
- Queue-based approach: record → queue chunk → worker picks up → transcribe → insert
- Minimal configuration: just chunk_duration in config.yaml
- No fancy UI updates during streaming (keep existing UI from feature 001)
- No complex error recovery (just log and continue)

**Core Flow**:

1. Main thread: record audio, split into 30s chunks, put in queue
2. Worker threads (pool of exactly 3): take chunk from queue → transcribe → insert text
3. Maintain insertion order using sequence numbers

## Success Criteria

- First chunk's text appears within ~35 seconds of recording start (30s recording + ~5s transcription)
- 10-minute recording produces incremental text output (not 20-minute wait at the end)
- chunk_duration configuration works correctly
- Recording continues smoothly while chunks transcribe in background
