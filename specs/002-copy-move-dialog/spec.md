# Feature Specification: Copy & Move Operations with Confirmation Dialog

**Feature Branch**: `002-copy-move-dialog`
**Created**: 2026-02-08
**Status**: Draft
**Input**: User description: "Operations copy and move should work different: F5 for Copy, F6 for Move, confirmation dialog before operation, progress screen during operation, destination is the opposite panel."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Copy Files to Opposite Panel (Priority: P1)

A user selects one or more files in the left panel and presses F5 (or clicks the Copy toolbar button). A confirmation dialog appears showing "Are you sure you want to Copy these objects to [destination path]?" with OK and Cancel buttons. After clicking OK, a progress indicator appears while the files are copied to the directory shown in the right panel. The same works in reverse (right panel to left panel).

**Why this priority**: Copy is the most fundamental file operation and the core of this feature. Users need a reliable, predictable way to copy files between panels with visual confirmation and feedback.

**Independent Test**: Can be fully tested by selecting files in one panel, pressing F5, confirming the dialog, and verifying files appear in the opposite panel.

**Acceptance Scenarios**:

1. **Given** one or more files are selected in the active panel, **When** user presses F5 or clicks Copy, **Then** a confirmation dialog appears showing the operation type ("Copy") and the destination path from the opposite panel.
2. **Given** the confirmation dialog is shown, **When** user clicks OK, **Then** a progress screen appears and the selected files are copied to the opposite panel's current location.
3. **Given** the confirmation dialog is shown, **When** user clicks Cancel, **Then** the dialog closes and no files are copied.
4. **Given** copy operation completes successfully, **When** progress finishes, **Then** both panels refresh to reflect the new state.

---

### User Story 2 - Move Files to Opposite Panel (Priority: P1)

A user selects one or more files in the left panel and presses F6 (or clicks the Move toolbar button). A confirmation dialog appears showing "Are you sure you want to Move these objects to [destination path]?" with OK and Cancel buttons. After clicking OK, a progress indicator appears while the files are moved. The files disappear from the source panel and appear in the destination panel.

**Why this priority**: Move is equally critical as copy for daily file management workflows. It shares the same confirmation and progress flow, making it a paired P1 alongside copy.

**Independent Test**: Can be fully tested by selecting files in one panel, pressing F6, confirming, and verifying files are removed from source and appear in destination.

**Acceptance Scenarios**:

1. **Given** one or more files are selected in the active panel, **When** user presses F6 or clicks Move, **Then** a confirmation dialog appears showing the operation type ("Move") and the destination path from the opposite panel.
2. **Given** the confirmation dialog is shown, **When** user clicks OK, **Then** a progress screen appears and the selected files are moved to the opposite panel's current location.
3. **Given** move operation completes successfully, **When** progress finishes, **Then** files no longer exist at the source and both panels refresh.

---

### User Story 3 - Keyboard Shortcut Changes (Priority: P1)

The existing Cmd+C/Cmd+X shortcuts for Copy/Move are replaced with F5/F6 respectively, matching the Norton Commander / Total Commander convention that the application follows.

**Why this priority**: The keyboard shortcuts are the primary user interface for these operations and must be correct for the feature to be usable.

**Independent Test**: Can be tested by pressing F5 and F6 with files selected and verifying the correct operation is triggered.

**Acceptance Scenarios**:

1. **Given** files are selected in the active panel, **When** user presses F5, **Then** the Copy confirmation dialog appears.
2. **Given** files are selected in the active panel, **When** user presses F6, **Then** the Move confirmation dialog appears.
3. **Given** the toolbar is visible, **When** user clicks the Copy button, **Then** the Copy confirmation dialog appears (same as F5).
4. **Given** the toolbar is visible, **When** user clicks the Move button, **Then** the Move confirmation dialog appears (same as F6).

---

### User Story 4 - Progress Feedback During Operations (Priority: P2)

During a copy or move operation, the user sees a progress screen indicating the operation is in progress. The progress screen prevents the user from initiating another operation until the current one completes.

**Why this priority**: Progress feedback is essential for good user experience, but the core copy/move functionality must work first.

**Independent Test**: Can be tested by copying a large file and verifying the progress indicator is visible during the operation.

**Acceptance Scenarios**:

1. **Given** user confirmed a copy or move operation, **When** the operation is in progress, **Then** a progress screen is displayed showing the operation is running.
2. **Given** the operation completes, **When** all files are processed, **Then** the progress screen closes and both panels refresh.
3. **Given** an error occurs during the operation, **When** a file cannot be copied or moved, **Then** the user is notified of the error with a meaningful message.

---

### Edge Cases

- What happens when no files are selected and user presses F5/F6? The system does nothing (no dialog shown).
- What happens when the opposite panel shows a GCS bucket location? The copy/move works across local-to-GCS, GCS-to-local, and GCS-to-GCS boundaries using the same confirmation flow.
- What happens when a file with the same name already exists at the destination? The system handles conflicts using the existing conflict resolution mechanism (overwrite, skip, or prompt).
- What happens when the source and destination are the same directory? The system warns the user or prevents the operation.
- What happens when the user lacks write permission at the destination? The system shows a meaningful error message.
- What happens when the operation involves directories (folders)? The system recursively copies/moves the entire directory tree.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST trigger the Copy operation when the user presses F5 or clicks the Copy toolbar button.
- **FR-002**: System MUST trigger the Move operation when the user presses F6 or clicks the Move toolbar button.
- **FR-003**: System MUST display a modal confirmation dialog before starting any Copy or Move operation.
- **FR-004**: The confirmation dialog MUST show the operation type ("Copy" or "Move") and the full destination path from the opposite panel.
- **FR-005**: The confirmation dialog MUST have exactly two buttons: "OK" and "Cancel".
- **FR-006**: System MUST NOT perform any file operation if the user clicks Cancel.
- **FR-007**: System MUST use the opposite panel's current location as the destination for the operation.
- **FR-008**: System MUST display a progress indicator while the operation is in progress.
- **FR-009**: System MUST refresh both panels after a successful operation completes.
- **FR-010**: System MUST handle errors during operations and display a user-friendly error message.
- **FR-011**: System MUST do nothing if F5/F6 is pressed or Copy/Move is clicked when no files are selected.
- **FR-012**: The previous Cmd+C (Copy) and Cmd+X (Move) shortcuts MUST be removed or reassigned to not trigger file copy/move operations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can copy files between panels in 3 interactions or fewer (select, press F5, confirm).
- **SC-002**: Users can move files between panels in 3 interactions or fewer (select, press F6, confirm).
- **SC-003**: The confirmation dialog appears within 1 second of pressing F5/F6 or clicking the button.
- **SC-004**: Both panels reflect the correct state within 2 seconds after the operation completes.
- **SC-005**: 100% of copy/move operations show a progress indicator for the duration of the operation.
- **SC-006**: Error messages are displayed for all failed operations, providing enough context for the user to understand and resolve the issue.

## Assumptions

- The existing transfer manager and progress dialog infrastructure will be reused for executing the actual file operations.
- The Cmd+V (Paste) shortcut is no longer needed since operations go directly to the opposite panel upon confirmation.
- The confirmation dialog text uses "objects" as a general term covering both files and directories.
- Cross-source operations (local-to-GCS, GCS-to-local) use the same confirmation and progress flow.
