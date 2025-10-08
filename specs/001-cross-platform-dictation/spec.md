# Feature Specification: Voice Dictation Application

**Feature Branch**: `001-cross-platform-dictation`  
**Created**: 2025-10-08  
**Status**: Completed  
**Completed**: 2025-10-08  
**Input**: User description: "це кросплатформлена аплікуха для транскрипції та написання тексту у всіх можливих місцях, тобто дає сможливіть надиктовувати текст. Вона має викликатися через гарячу клавішу, після того як юзер напис клавішу, то проводиться пошук мікрофона і починається записування аудіо. Транскрипція має бути потоковою, тобто записав пару слів одразу почав транскрипцію і написання. UI має бути супер простим, це круг з значком мікрофона посередині, при записі має бути анімація пульсації, наприклад, через обводку. UI має зявлятися лише при виклику горячої клавіші. Якщо користувач натисне на значок мікрофона то записування припинеться, те саме можливо при повторному натисканні кнопки запису. UI має бути максимально мінімалістичним."

## Clarifications

### Session 2025-10-08

- Q: Should the application use local (offline) transcription or cloud-based transcription? → A: Local/offline transcription only
- Q: How should the application insert transcribed text into the target application? → A: Keyboard emulation (simulate typing)
- Q: Should the application store recorded audio, and if so, for how long? → A: Never store audio (delete immediately)
- Q: When an error occurs (no microphone, permissions denied, transcription failure), what should happen? → A: Show error briefly, auto-dismiss
- Q: Where should the UI overlay appear on screen? → A: Bottom-right corner, always on top, no manual resize or repositioning
- Q: Should transcription happen during recording (streaming) or after recording completes? → A: After recording completes (simpler first version)
- Q: Which transcription engine should be used? → A: faster-whisper
- Q: What should the UI show during transcription processing? → A: Change icon inside the circle
- Q: What should happen when transcription result is empty? → A: Insert nothing silently, UI disappears immediately

## User Scenarios *(mandatory)*

### User Story 1 - Hotkey-Activated Voice Recording (Priority: P1)

User needs to quickly start voice dictation from any application without switching windows or opening menus. When the user presses the global hotkey, the application activates, detects the microphone, and begins recording immediately.

**Why this priority**: Core functionality - without hotkey activation and recording, there is no product. This is the minimum viable feature.

**Manual Verification**: User presses configured hotkey while in any application (text editor, browser, email client), circular UI appears in bottom-right corner with microphone icon, pulsating animation begins, and audio recording starts.

**Acceptance Scenarios**:

1. **Given** user is working in any application, **When** user presses the global hotkey, **Then** circular UI overlay appears in bottom-right corner with microphone icon and pulsating border animation
2. **Given** UI overlay is visible, **When** microphone is detected, **Then** recording begins automatically without additional user action
3. **Given** recording is active with pulsating animation, **When** user clicks microphone icon, **Then** recording stops and UI disappears
4. **Given** recording is active, **When** user presses hotkey again, **Then** recording stops and UI disappears

---

### User Story 2 - Complete Recording Then Transcription (Priority: P2)

User speaks continuously into the microphone, and when finished, stops the recording. The application then processes the complete audio recording, transcribes it, and inserts the text into the previously focused input field. This sequential approach (record → transcribe → insert) simplifies the first version.

**Why this priority**: Transcription and text insertion are essential, but processing after recording (rather than streaming) simplifies implementation and reduces complexity for the first version.

**Manual Verification**: User activates recording via hotkey, speaks their message, stops recording (click or hotkey), waits for transcription to complete, then observes all transcribed text appearing in the previously focused text field.

**Acceptance Scenarios**:

1. **Given** recording is active, **When** user stops recording (click icon or press hotkey), **Then** UI shows transcription in progress state (icon changes to processing indicator)
2. **Given** transcription is processing, **When** transcription completes successfully, **Then** full transcribed text is inserted into previously focused text input via keyboard emulation
3. **Given** transcription completes with empty result, **When** no speech was detected, **Then** UI disappears immediately without inserting any text or showing error
4. **Given** text insertion begins, **When** insertion completes, **Then** cursor is positioned at the end of inserted text and UI disappears

---

### User Story 3 - Cross-Platform Compatibility (Priority: P3)

User works on multiple operating systems (Windows, macOS, Linux) and expects the same dictation experience regardless of platform. The application runs natively on each platform with consistent behavior.

**Why this priority**: Cross-platform support expands user base, but core functionality (P1, P2) must work first on at least one platform for MVP.

**Manual Verification**: User installs application on Windows, macOS, and Linux systems, activates hotkey on each platform, and verifies identical behavior (UI appearance, recording, transcription, text insertion).

**Acceptance Scenarios**:

1. **Given** application is installed on Windows, **When** user activates hotkey, **Then** behavior matches specification (UI, recording, transcription)
2. **Given** application is installed on macOS, **When** user activates hotkey, **Then** behavior matches specification identically to Windows
3. **Given** application is installed on Linux, **When** user activates hotkey, **Then** behavior matches specification identically to other platforms

---

### Edge Cases

- What happens when no microphone is detected after hotkey activation?
- What happens when user switches to a non-text input field during transcription?
- What happens when user switches to a non-text input field after recording but before transcription completes?
- What happens when microphone permissions are denied?
- What happens when user activates hotkey while UI is already visible?
- What happens when transcription engine fails during processing?
- **FR-010b**: System MUST insert nothing and hide UI immediately if transcription result is empty (no error shown)
- What happens when user speaks in a language different from configured primary language?
- What happens when multiple applications compete for microphone access?
- What happens when user changes primary language while recording is in progress?
- What happens when configured primary language is not supported by transcription engine?
- What happens if system crashes during recording (is audio data recoverable or lost)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST register a global hotkey that works across all applications regardless of which window has focus
- **FR-002**: System MUST detect available microphone devices when hotkey is pressed
- **FR-003**: System MUST begin audio recording immediately after microphone detection without additional user confirmation
- **FR-004**: System MUST display a circular UI overlay with microphone icon in the bottom-right corner of screen when recording starts
- **FR-004a**: UI overlay MUST be fixed size with no user ability to resize or reposition
- **FR-005**: System MUST animate the UI with a pulsating border/outline effect during active recording
- **FR-006**: System MUST hide the UI overlay when recording stops (via click or hotkey)
- **FR-007**: System MUST stop recording when user clicks the microphone icon in the UI
- **FR-008**: System MUST stop recording when user presses the activation hotkey a second time
- **FR-008a**: System MUST show transcription-in-progress state in UI after recording stops
- **FR-008b**: System MUST change the icon inside the circle to indicate transcription processing (e.g., hourglass, spinner, or processing symbol)
- **FR-009**: System MUST perform transcription after recording completes (not during recording)
- **FR-009a**: System MUST use local/offline transcription engine (no internet connection required)
- **FR-009b**: System MUST use faster-whisper as the transcription engine
- **FR-010**: System MUST insert complete transcribed text into the previously focused text input field after transcription finishes
- **FR-010a**: System MUST use clipboard paste method for text insertion (faster and more reliable than keyboard emulation, especially for Unicode)
- **FR-010a-1**: On Linux, system MUST use xclip + Ctrl+V for clipboard paste
- **FR-010a-2**: On Windows, system MUST use Win32 API or PowerShell + Ctrl+V for clipboard paste  
- **FR-010a-3**: On macOS, system MUST use pbcopy + Cmd+V for clipboard paste
- **FR-010a-4**: System MUST preserve original clipboard content by saving and restoring it after paste operation
- **FR-010a-5**: System MUST fallback to pynput keyboard emulation if clipboard method fails
- **FR-010b**: System MUST insert nothing and hide UI immediately if transcription result is empty (no error shown)
- **FR-011**: System MUST position cursor at the end of inserted text after insertion completes
- **FR-012**: System MUST hide UI overlay after text insertion completes
- **FR-013**: System MUST run natively on Windows, macOS, and Linux platforms
- **FR-014**: System MUST maintain consistent UI appearance and behavior across all supported platforms
- **FR-015**: System MUST request microphone permissions from the operating system on first use
- **FR-016**: System MUST display error state in UI if microphone is unavailable or permissions denied
- **FR-016a**: Error messages MUST auto-dismiss after brief display (2-3 seconds) without requiring user interaction
- **FR-017**: System MUST gracefully handle transcription engine failures without crashing
- **FR-018**: System MUST allow user to configure the global hotkey combination
- **FR-019**: UI MUST be minimalistic with only a circular shape, microphone icon, and pulsating animation
- **FR-020**: UI MUST appear as an overlay above all other windows
- **FR-020a**: UI position and size MUST be fixed (bottom-right corner, no user customization)
- **FR-021**: System MUST support transcription in all languages supported by faster-whisper (99 languages)
- **FR-022**: System MUST allow user to configure a primary language for improved transcription accuracy
- **FR-023**: System MUST use the configured primary language as a hint to faster-whisper
- **FR-024**: Primary language configuration MUST be achievable through the simplest possible method (configuration file, command-line parameter, or environment variable)
- **FR-025**: System MUST NOT require a dedicated UI for language selection (simple configuration method sufficient)
- **FR-026**: System MUST delete audio data immediately after transcription processing
- **FR-027**: System MUST NOT store, cache, or persist recorded audio to disk or memory beyond active processing

### Key Entities

- **Recording Session**: Represents a single voice dictation session from hotkey press to recording stop, containing complete audio recording, transcription state, and target text field reference
- **Audio Recording**: Complete audio captured from start to stop of recording session
- **Transcription Result**: Text output from processing the complete audio recording, ready for insertion into target application
- **UI Overlay**: Circular floating window with microphone icon and pulsating animation, appearing only during active recording
- **Hotkey Configuration**: User-defined keyboard shortcut for activating/deactivating recording
- **Language Configuration**: User's primary language preference used to improve transcription accuracy

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can activate dictation within 1 second of pressing hotkey (microphone detection + UI appearance)
- **SC-002**: Transcription completes within reasonable time based on recording length (e.g., 5-10 seconds for 30 second recording)
- **SC-003**: Application successfully captures and transcribes dictation in 95% of attempts (excluding user errors like no microphone)
- **SC-004**: UI overlay is visible and responsive on all three platforms (Windows, macOS, Linux)
- **SC-005**: Dictated text inserts correctly into the focused application 90% of the time
- **SC-006**: Application can be installed and running within 5 minutes on any supported platform
- **SC-007**: Transcription processing provides visual feedback (icon changes to processing indicator)
- **SC-008**: UI remains minimalistic with single circular element and no additional buttons or controls
- **SC-009**: Hotkey responds globally regardless of which application has focus
- **SC-010**: Recording stops immediately (within 0.5 seconds) when user clicks icon or presses hotkey again
- **SC-011**: Application supports transcription in 99 languages via faster-whisper
- **SC-012**: Primary language can be configured without launching a graphical interface (simple config file or command-line)
- **SC-013**: Audio data is deleted immediately after transcription with no persistent storage
- **SC-014**: Error messages display for 2-3 seconds and auto-dismiss without user interaction
- **SC-015**: UI overlay appears in bottom-right corner with fixed size and position (no user customization)
- **SC-016**: Empty transcription results (no speech detected) cause UI to disappear immediately without error messages

### Assumptions

- Users have a working microphone connected or built into their device
- Users grant microphone permissions when prompted by the operating system
- Users can configure primary language through simple methods (config file, environment variable, or command-line)
- Target applications accept simulated keyboard input events
- No internet connection required (local transcription engine)
- Default hotkey can be changed by user to avoid conflicts with other applications
- If no primary language is configured, system uses automatic language detection or a sensible default (e.g., system locale)

