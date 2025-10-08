# Implementation Plan: Streaming Audio Transcription

**Branch**: `002-streaming-transcription` | **Date**: 2025-10-08 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/002-streaming-transcription/spec.md`

## Summary

Extend the existing voice dictation application (feature 001) to support **chunked streaming transcription** for long-form dictation. Instead of transcribing the entire recording after it completes, the system will:

- Split audio into configurable chunks (default 30 seconds)
- Transcribe chunks in parallel using 3 worker threads (ThreadPoolExecutor)
- Insert transcribed text incrementally in recording order
- Reduce perceived latency for long recordings (10-minute recording produces incremental output instead of 20-minute wait)

**Technical Approach**: Simple threading model using Python stdlib (queue.Queue, ThreadPoolExecutor), extending existing modules (AudioRecorder, Transcriber, TextInserter) without adding external dependencies.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: faster-whisper, tkinter, pynput, sounddevice, numpy (all existing from feature 001)  
**Storage**: N/A (in-memory only, no persistence)  
**Testing**: Manual verification only (per Constitution)  
**Target Platform**: Cross-platform (Windows, macOS, Linux)  
**Project Type**: Single desktop application  
**Performance Goals**: First chunk text appears within ~35 seconds (30s recording + 5s transcription)  
**Constraints**: Max 3 concurrent transcriptions, ordered text insertion, fail-fast on any chunk error  
**Scale/Scope**: Small desktop utility, single user, ~500 additional LOC

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Simplicity First**: Uses stdlib only (queue.Queue, ThreadPoolExecutor), no async/await, straightforward chunking logic
- [x] **User Installation Priority**: No new dependencies, existing installation process unchanged
- [x] **No Automated Testing**: Manual verification scenarios defined in quickstart.md
- [x] **Minimal Documentation**: One new config parameter (chunk_duration) documented in existing config.yaml comments
- [x] **Dependency Minimization**: Zero new external dependencies (uses Python 3.11 stdlib)
- [x] **Cross-Platform**: Extends existing cross-platform implementation, no platform-specific code

**Status**: ✅ All constitution checks passed

## Project Structure

### Documentation (this feature)

```
specs/002-streaming-transcription/
├── plan.md              # This file
├── spec.md              # Feature specification (with clarifications)
├── research.md          # Phase 0 output (technical decisions)
├── data-model.md        # Phase 1 output (entities and relationships)
├── quickstart.md        # Phase 1 output (implementation guide)
├── contracts/
│   └── internal-api.md  # Phase 1 output (API contracts)
└── checklists/
    └── requirements.md  # Requirements tracking
```

### Source Code (repository root)

```
src/
├── audio_recorder.py         # MODIFIED: Add get_chunk_if_ready(), get_final_chunk()
├── transcriber.py            # NO CHANGE (already supports variable-length audio)
├── text_inserter.py          # NO CHANGE (already supports incremental insertion)
├── config.py                 # MODIFIED: Add chunk_duration field
├── utils.py                  # MODIFIED: Add ChunkTranscriptionResult dataclass
├── streaming_session.py      # NEW: StreamingSession class (chunk management)
└── whisper-typer-ui.py       # MODIFIED: Integrate StreamingSession, add polling

config.yaml                   # MODIFIED: Add chunk_duration parameter

assets/                       # NO CHANGE
build.py                      # NO CHANGE
```

**Structure Decision**: Single project structure (Option 1) maintained. All new code in `src/` directory, extending existing modules. One new file (`streaming_session.py`) to encapsulate chunk management logic.

## Complexity Tracking

*No constitution violations requiring justification.*

All design decisions prioritize simplicity:
- Stdlib primitives (no new frameworks)
- Single-writer concurrency pattern (no locks)
- Fail-fast error handling (no retry logic)
- Minimal configuration (one parameter)

---

## Implementation Summary

### Phase 0: Research (Complete)

**Output**: [research.md](./research.md)

**Key Decisions**:
1. **Chunking**: Time-based fixed 30s duration, NumPy array slicing
2. **Parallelism**: ThreadPoolExecutor with 3 workers (stdlib)
3. **Ordering**: Dictionary buffer for out-of-order chunks, sequential insertion
4. **Error Handling**: Fail-fast (stop all on any chunk error)
5. **Partial Chunks**: Treated as regular shorter chunks
6. **Session Overlap**: Block hotkey with `is_processing` flag
7. **Configuration**: Single `chunk_duration` parameter in config.yaml
8. **Stack**: Zero new dependencies, extends existing modules

### Phase 1: Design (Complete)

**Outputs**:
- [data-model.md](./data-model.md) - Entity definitions (AudioChunk, ChunkTranscriptionResult, StreamingSession)
- [contracts/internal-api.md](./contracts/internal-api.md) - Python API signatures
- [quickstart.md](./quickstart.md) - Step-by-step implementation guide
- [.github/copilot-instructions.md](../../.github/copilot-instructions.md) - Updated agent context

**New Entities**:
- `AudioChunk`: Chunk sequence number + audio buffer
- `ChunkTranscriptionResult`: Sequence + transcribed text
- `StreamingSession`: Manages queue, executor, ordering

**Modified Entities**:
- `AppConfig`: +chunk_duration field
- `AudioRecorder`: +get_chunk_if_ready(), +get_final_chunk()
- `DictationApp`: +is_processing flag, +chunk polling

### Phase 2: Implementation Tasks

**Status**: Not started (use `/speckit.tasks` to generate)

**Estimated Effort**: 4-6 hours (see quickstart.md breakdown)

**Implementation Order**:
1. Config extension (chunk_duration)
2. Data classes (AudioChunk, ChunkTranscriptionResult)
3. AudioRecorder chunking methods
4. StreamingSession class (core logic)
5. Main app integration (polling, session management)
6. Manual verification (5 test scenarios)

---

## Artifacts Generated

- ✅ `specs/002-streaming-transcription/spec.md` - Feature specification with clarifications
- ✅ `specs/002-streaming-transcription/research.md` - Technical decisions
- ✅ `specs/002-streaming-transcription/data-model.md` - Entity definitions
- ✅ `specs/002-streaming-transcription/contracts/internal-api.md` - API contracts
- ✅ `specs/002-streaming-transcription/quickstart.md` - Implementation guide
- ✅ `specs/002-streaming-transcription/checklists/requirements.md` - Requirements tracking
- ✅ `specs/002-streaming-transcription/plan.md` - This file
- ⏭️ `specs/002-streaming-transcription/tasks.md` - Implementation tasks (next: `/speckit.tasks`)

---

## Next Steps

1. **Review this plan** - Ensure technical approach aligns with expectations
2. **Run `/speckit.tasks`** - Generate detailed implementation task breakdown
3. **Begin implementation** - Follow quickstart.md step-by-step guide
4. **Manual verification** - Test 5 scenarios from quickstart.md
5. **Update README** - Document streaming transcription feature
6. **Commit changes** - Merge to main branch when complete

---

**Planning Complete**: 2025-10-08  
**Ready for Implementation**: ✅ Yes
