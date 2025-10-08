# Tasks: Streaming Audio Transcription

**Input**: Design documents from `/specs/002-streaming-transcription/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/internal-api.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and manual verification of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/` at repository root (this project structure)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

**Status**: ✅ Already complete (feature 001 infrastructure exists)

- [x] T001 Python 3.11+ environment with existing dependencies (faster-whisper, tkinter, pynput, sounddevice, numpy)
- [x] T002 Project structure: `src/`, `config.yaml`, build configuration
- [x] T003 [P] Linting/formatting tools configured

**Note**: No new dependencies required for this feature (Constitution compliance)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures and configuration that MUST be complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Add `chunk_duration: int` field to `AppConfig` class in `src/config.py` with validation method `_validate_chunk_duration()` (default: 30 seconds, must be positive integer)
- [ ] T005 [P] Update `config.yaml` to include `chunk_duration: 30` parameter with inline comment
- [ ] T006 [P] Create `AudioChunk` dataclass in `src/audio_recorder.py` with fields: sequence, audio_buffer, duration, start_offset
- [ ] T007 [P] Create `ChunkTranscriptionResult` dataclass in `src/utils.py` with fields: sequence, text, processing_time
- [ ] T008 Add `chunk_start_time: float | None` and `current_sequence: int` attributes to `AudioRecorder.__init__()` in `src/audio_recorder.py`
- [ ] T009 Modify `AudioRecorder.start_recording()` in `src/audio_recorder.py` to initialize `chunk_start_time = time.time()` and `current_sequence = 0`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Long-Form Dictation with Streaming Transcription (Priority: P1) 🎯 MVP

**Goal**: Enable chunked streaming transcription for long recordings (10+ minutes) to eliminate post-recording wait time. User sees text appearing incrementally as chunks complete transcription.

**Manual Verification**: 
1. Start recording, speak for 90 seconds, continue recording → first chunk text appears within ~35 seconds (30s recording + 5s transcription)
2. Record for 3 minutes → verify 3 chunks created and all text inserted in correct order
3. Press hotkey while previous chunks transcribing → verify hotkey ignored until all chunks complete
4. Record for 45 seconds (1.5 chunks), stop → verify partial final chunk (15s) is transcribed and inserted
5. Trigger transcription error in chunk 2 → verify all chunks cancelled, error shown, no partial text inserted

### Chunking Infrastructure (Extends AudioRecorder)

- [ ] T010 [US1] Implement `AudioRecorder.get_chunk_if_ready(chunk_duration_sec: int) -> AudioChunk | None` method in `src/audio_recorder.py` that checks elapsed time, creates chunk if >= threshold, clears buffer, resets timer, increments sequence
- [ ] T011 [US1] Implement `AudioRecorder.get_final_chunk() -> AudioChunk | None` method in `src/audio_recorder.py` that extracts remaining audio as final chunk after stop_recording() called, sets chunk_start_time = None

### Streaming Session Management (New Module)

- [ ] T012 [US1] Create `src/streaming_session.py` file with imports: queue, ThreadPoolExecutor, Future, dataclasses
- [ ] T013 [US1] Implement `StreamingSession.__init__(chunk_duration, transcriber, text_inserter, ui_overlay)` in `src/streaming_session.py` initializing: chunk_queue (queue.Queue), executor (ThreadPoolExecutor max_workers=3), pending_futures (dict), completed_chunks (dict), next_sequence_to_insert (int=0), total_chunks_created (int=0)
- [ ] T014 [US1] Implement `StreamingSession.submit_chunk(chunk: AudioChunk)` method in `src/streaming_session.py` that submits `_transcribe_chunk_worker()` to executor, stores Future in pending_futures, increments total_chunks_created, registers callback
- [ ] T015 [US1] Implement `StreamingSession._transcribe_chunk_worker(chunk: AudioChunk) -> ChunkTranscriptionResult` private method in `src/streaming_session.py` that calls transcriber.transcribe(), wraps in try/except for error handling
- [ ] T016 [US1] Implement `StreamingSession._on_chunk_complete(sequence: int, text: str)` callback method in `src/streaming_session.py` that stores result in completed_chunks, triggers ordered insertion loop (while next_sequence_to_insert exists: insert text, increment counter, delete from buffer)
- [ ] T017 [US1] Implement `StreamingSession.wait_for_completion()` method in `src/streaming_session.py` that blocks until all pending_futures resolve, handles any exceptions (fail-fast), shuts down executor
- [ ] T018 [US1] Implement `StreamingSession.cancel_all()` method in `src/streaming_session.py` that cancels all pending futures, clears queues/buffers, shuts down executor (error handling path)

### Main Application Integration

- [ ] T019 [US1] Add `is_processing: bool = False` flag to `DictationApp` class in `src/whisper-typer-ui.py` to track streaming session state
- [ ] T020 [US1] Modify `DictationApp.on_hotkey_press()` in `src/whisper-typer-ui.py` to check `if self.is_processing: return` (ignore hotkey during chunk processing)
- [ ] T021 [US1] Modify `DictationApp.on_hotkey_press()` in `src/whisper-typer-ui.py` RECORDING → TRANSCRIBING path to create `StreamingSession` instance, start chunk polling loop (every 100ms call `get_chunk_if_ready()`)
- [ ] T022 [US1] Implement chunk polling logic in `src/whisper-typer-ui.py` main loop: while RECORDING, call `audio_recorder.get_chunk_if_ready(config.chunk_duration)` every 100ms, if chunk returned call `session.submit_chunk(chunk)`
- [ ] T023 [US1] Modify `DictationApp.on_hotkey_press()` TRANSCRIBING → COMPLETED path in `src/whisper-typer-ui.py` to call `audio_recorder.get_final_chunk()`, submit to session if not None, call `session.wait_for_completion()`, set `is_processing = False`
- [ ] T024 [US1] Add error handling in `src/whisper-typer-ui.py`: wrap `session.wait_for_completion()` in try/except, on exception call `session.cancel_all()`, show error via `ui_overlay.set_icon('error')`, set `is_processing = False`

**Checkpoint**: At this point, User Story 1 should be fully functional and manually verifiable using the 5 test scenarios above

---

## Phase 4: User Story 2 - Configurable Chunk Duration (Priority: P2)

**Goal**: Allow users to tune chunk duration via config file to balance transcription latency and accuracy (shorter chunks = faster feedback, longer chunks = better accuracy at boundaries)

**Manual Verification**:
1. Set `chunk_duration: 60` in config.yaml, restart app, record for 120 seconds → verify exactly 2 chunks created (0-60s, 60-120s)
2. Set `chunk_duration: 15` in config.yaml, restart app, record for 60 seconds → verify exactly 4 chunks created
3. Set `chunk_duration: 0` in config.yaml, restart app → verify app uses default 30 seconds and logs warning
4. Set `chunk_duration: -10` in config.yaml, restart app → verify app uses default 30 seconds and logs warning

### Configuration Extension

**Status**: ✅ Already complete in Phase 2 (T004, T005)

- [x] T004 (from Phase 2) Already implemented chunk_duration configuration with validation

### Integration Validation

- [ ] T025 [US2] Add startup logging in `src/config.py` to print `f"Using chunk_duration: {self.chunk_duration}s"` after validation
- [ ] T026 [US2] Verify in `src/whisper-typer-ui.py` that `config.chunk_duration` is passed to all `get_chunk_if_ready()` calls consistently
- [ ] T027 [US2] Add inline documentation in `config.yaml` explaining chunk_duration tuning tradeoffs (shorter = faster feedback but possible boundary accuracy loss, longer = better accuracy but delayed feedback)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T028 [P] Update `README.md` to document streaming transcription feature (FR-001 to FR-012), chunk_duration configuration, performance benefits (10-minute recording now shows incremental text vs 20-minute wait)
- [ ] T029 [P] Update `.github/copilot-instructions.md` to mark feature 002 status as "Completed" (currently shows Active Technologies from 002)
- [ ] T030 Code review: verify all Constitution checks pass (simplicity, no new deps, no tests, minimal docs, cross-platform)
- [ ] T031 Run all 5 manual verification scenarios from User Story 1 + all 4 scenarios from User Story 2
- [ ] T032 Performance validation: record 10-minute dictation, verify first chunk text appears within 35 seconds, verify all chunks complete successfully, verify ThreadPoolExecutor max_workers=3 (check logs or add debug print)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: ✅ Already complete - no action needed
- **Foundational (Phase 2)**: Can start immediately - BLOCKS all user stories (T004-T009 must complete first)
- **User Story 1 (Phase 3)**: Depends on Foundational Phase 2 completion (requires AudioChunk, ChunkTranscriptionResult, AudioRecorder extensions)
- **User Story 2 (Phase 4)**: Depends on Foundational Phase 2 completion (chunk_duration config already implemented in T004, just needs validation/docs)
- **Polish (Phase 5)**: Depends on both User Stories 1 and 2 being complete

### User Story Dependencies

- **User Story 1 (P1 - MVP)**: Can start after Foundational (Phase 2) - No dependencies on User Story 2
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of User Story 1 (just validates config that's already used)

### Within Each User Story

**User Story 1 Flow**:
1. T010, T011 (AudioRecorder methods) - blocking prerequisites for session
2. T012, T013 (StreamingSession init) - blocking prerequisite for worker methods
3. T014, T015, T016, T017, T018 (StreamingSession methods) - can proceed sequentially after T013
4. T019, T020 (DictationApp flags) - blocking prerequisites for main loop integration
5. T021, T022, T023, T024 (main app integration) - final integration after all components ready

**User Story 2 Flow**:
1. T004 (already done in Phase 2) - blocking prerequisite
2. T025, T026, T027 (validation/docs) - can proceed in any order after T004

### Parallel Opportunities

**Phase 2 (Foundational)**: All tasks can run in parallel except:
- T008, T009 require T006 (AudioChunk dataclass must exist first)

**User Story 1**: Limited parallelism due to dependencies:
- T010, T011 can run in parallel (both extend AudioRecorder)
- T012, T013 can run after dataclasses ready (T006, T007)
- T014-T018 are sequential (each builds on StreamingSession class)
- T019, T020 can run in parallel (both modify DictationApp)

**User Story 2**: 
- T025, T026, T027 can all run in parallel (different files/concerns)

**Cross-Story Parallelism**:
- User Story 1 and User Story 2 can be worked on in parallel by different developers after Phase 2 completes

---

## Parallel Example: Foundational Phase

```bash
# Launch foundational tasks in parallel:
Developer A: "T004 - Add chunk_duration to AppConfig"
Developer B: "T005 - Update config.yaml"
Developer C: "T006 - Create AudioChunk dataclass"
Developer D: "T007 - Create ChunkTranscriptionResult dataclass"
# Then synchronize before T008, T009
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. ✅ Complete Phase 1: Setup (already done)
2. Complete Phase 2: Foundational (T004-T009) - **CRITICAL BLOCKING PHASE**
3. Complete Phase 3: User Story 1 (T010-T024)
4. **STOP and VALIDATE**: Run 5 manual test scenarios from User Story 1
5. If validated → MVP is ready for use (streaming transcription works!)

### Full Feature Delivery

1. Complete MVP (Phase 1-3) → Validate User Story 1
2. Complete Phase 4: User Story 2 (T025-T027) → Validate configurable chunk duration
3. Complete Phase 5: Polish (T028-T032) → Final validation and documentation
4. **Feature Complete**: All 12 functional requirements (FR-001 to FR-012) implemented

### Parallel Team Strategy

With 2 developers:

1. Both complete Phase 2: Foundational together (fast - 9 simple tasks)
2. After Phase 2 done:
   - Developer A: User Story 1 (T010-T024) - core streaming implementation
   - Developer B: User Story 2 (T025-T027) - config validation/docs (lightweight)
3. Both collaborate on Phase 5: Polish

---

## Task Summary

**Total Tasks**: 32 tasks

### By Phase:
- Phase 1 (Setup): 3 tasks (✅ complete)
- Phase 2 (Foundational): 6 tasks (blocking prerequisites)
- Phase 3 (User Story 1 - P1 MVP): 15 tasks (core streaming)
- Phase 4 (User Story 2 - P2): 3 tasks (config validation)
- Phase 5 (Polish): 5 tasks (docs, validation)

### By User Story:
- **Setup/Foundational**: 9 tasks (infrastructure)
- **User Story 1 (P1)**: 15 tasks (streaming transcription)
- **User Story 2 (P2)**: 3 tasks (configurable chunk duration)
- **Polish**: 5 tasks (cross-cutting)

### Parallel Opportunities:
- Phase 2: 4 tasks can run in parallel (T004, T005, T006, T007)
- User Story 1: 2-3 parallel opportunities at component boundaries
- User Story 2: 3 tasks can run in parallel
- **Cross-story**: US1 and US2 can be developed in parallel after Phase 2

### Estimated Effort:
- **Phase 2 (Foundational)**: 1.5 hours (simple config/dataclass additions)
- **Phase 3 (User Story 1)**: 3.5 hours (core complexity: StreamingSession, main app integration)
- **Phase 4 (User Story 2)**: 0.5 hours (lightweight validation/docs)
- **Phase 5 (Polish)**: 1 hour (documentation, manual testing)
- **Total**: 6.5 hours (aligns with quickstart.md estimate of 4-6 hours for core implementation + validation)

### MVP Scope Suggestion:
- **Minimum Viable Product**: Phase 1 + Phase 2 + Phase 3 (User Story 1 only)
- **Delivers**: Streaming transcription for long recordings (core value proposition)
- **Effort**: ~5 hours
- **Omits**: Configurable chunk duration (uses hardcoded default 30s)
- **Recommendation**: Ship MVP first, validate with users, then add P2 configurability based on feedback

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story (US1, US2)
- Each user story independently completable and manually verifiable
- Commit after each task or logical group (e.g., after completing StreamingSession class)
- Stop at any checkpoint to validate story independently
- Constitution compliance: Zero new dependencies, stdlib only (queue.Queue, ThreadPoolExecutor)
- All design decisions documented in research.md (8 technical decisions)
- All API contracts defined in contracts/internal-api.md (12 signatures)
