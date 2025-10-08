# Requirements Checklist - Streaming Audio Transcription

## Functional Requirements

- [ ] FR-001: Split audio into fixed-duration chunks based on chunk_duration config
- [ ] FR-002: Begin transcribing chunks as soon as they reach configured duration (non-blocking)
- [ ] FR-003: Transcribe chunks in parallel worker threads without blocking recording
- [ ] FR-004: Insert transcribed text incrementally as chunks finish
- [ ] FR-005: Handle final partial chunk when user stops recording mid-chunk
- [ ] FR-006: Support chunk_duration parameter in config.yaml (default: 30 seconds)
- [ ] FR-007: Validate chunk_duration is positive integer; use default if invalid
- [ ] FR-008: Insert chunks in recording order (buffer out-of-order chunks)
- [ ] FR-009: Continue recording without interruption during background transcription
- [ ] FR-010: Limit concurrent workers to exactly 3
- [ ] FR-011: Stop all transcription and show error if any chunk fails (discard all)
- [ ] FR-012: Ignore hotkey while previous chunks are still transcribing
