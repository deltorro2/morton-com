# Feature Specification: New Folder Dialog

**Feature Branch**: `003-new-folder-dialog`
**Created**: 2026-02-08
**Status**: Draft
**Input**: User description: "Add to the toolbar panel a new button 'New Folder' (F7) which shows a modal dialog allowing the user to define the name of a new folder. Works for both local filesystem and GCS bucket locations. The folder name can include multiple hierarchy levels like 'Folder/subfolder/subsubfolder'. The shortcut is F7."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a New Folder on Local Filesystem (Priority: P1)

A user browsing local files in either panel wants to create a new folder in the currently displayed directory. They press F7 or click the "New Folder" toolbar button. A modal dialog appears with a text field for the folder name. They type a name (e.g., "Documents") and click OK. The folder is created in the current directory and the panel refreshes to show it.

**Why this priority**: Creating folders on the local filesystem is the most common use case and the core value of this feature.

**Independent Test**: Can be fully tested by pressing F7 in a local directory, entering a folder name, and verifying the folder appears in the file listing.

**Acceptance Scenarios**:

1. **Given** the active panel displays a local directory, **When** the user presses F7, enters "NewFolder", and clicks OK, **Then** a folder named "NewFolder" is created in the current directory and the panel refreshes to show it.
2. **Given** the active panel displays a local directory, **When** the user presses F7, enters "Parent/Child/Grandchild", and clicks OK, **Then** the entire folder hierarchy is created and the panel refreshes.
3. **Given** the active panel displays a local directory, **When** the user presses F7 and clicks Cancel, **Then** no folder is created and the panel remains unchanged.

---

### User Story 2 - Create a New Folder in a GCS Bucket (Priority: P2)

A user browsing objects in a GCS bucket wants to create a new "folder" (prefix) at the current location. They press F7 or click "New Folder", enter a name, and click OK. A zero-byte placeholder object is created with a trailing slash to represent the folder, and the panel refreshes.

**Why this priority**: GCS folder creation extends the feature to the second supported storage type, completing the dual-panel functionality.

**Independent Test**: Can be tested by pressing F7 while viewing a GCS bucket, entering a prefix name, and verifying the folder prefix appears in the listing.

**Acceptance Scenarios**:

1. **Given** the active panel displays a GCS bucket, **When** the user presses F7, enters "data-exports", and clicks OK, **Then** a folder prefix "data-exports/" is created in the bucket at the current prefix location and the panel refreshes.
2. **Given** the active panel displays a GCS bucket at prefix "logs/", **When** the user presses F7, enters "2026/january", and clicks OK, **Then** the prefix "logs/2026/january/" is created and the panel refreshes.

---

### User Story 3 - Toolbar Button Access (Priority: P3)

A user who prefers mouse interaction clicks the "New Folder" button in the toolbar to create a folder, rather than using the F7 keyboard shortcut. The same dialog appears and the behavior is identical.

**Why this priority**: Provides an alternative access method for discoverability and mouse-oriented users.

**Independent Test**: Can be tested by clicking the "New Folder" toolbar button and verifying the dialog appears with the same behavior as F7.

**Acceptance Scenarios**:

1. **Given** the toolbar is visible, **When** the user clicks the "New Folder (F7)" button, **Then** the same modal dialog appears as when pressing F7.

---

### Edge Cases

- What happens when the user enters a folder name that already exists? The system shows an error message and the dialog remains open for correction.
- What happens when the user enters an empty name or whitespace-only? The system does not create a folder and shows a validation message.
- What happens when the user enters a name with invalid characters (e.g., null bytes)? The system shows an error message describing the issue.
- What happens when the active panel shows a GCS project listing (bucket list)? The "New Folder" operation is not available (F7 does nothing, button is disabled).
- What happens when the user lacks write permissions to the current directory? The system shows an error message after the creation attempt fails.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a "New Folder (F7)" button in the toolbar.
- **FR-002**: System MUST bind the F7 key to trigger the new folder dialog.
- **FR-003**: System MUST display a modal dialog with a text input field for the folder name and OK/Cancel buttons.
- **FR-004**: System MUST create folders on the local filesystem when the active panel is in local mode.
- **FR-005**: System MUST create folder prefixes (zero-byte objects with trailing slash) in GCS buckets when the active panel is in GCS bucket mode.
- **FR-006**: System MUST support multi-level folder paths (e.g., "a/b/c") creating all intermediate directories.
- **FR-007**: System MUST refresh the active panel after successful folder creation.
- **FR-008**: System MUST show an error message if folder creation fails (permissions, name conflict, network error).
- **FR-009**: System MUST NOT allow folder creation when the active panel shows a GCS project listing (bucket list).
- **FR-010**: System MUST NOT create a folder if the user cancels the dialog or enters an empty name.
- **FR-011**: The dialog title MUST be "New Folder".

### Assumptions

- The dialog uses a simple text input field; no folder browser or autocomplete is needed.
- For GCS, creating a "folder" means creating a zero-byte object with the folder path ending in "/".
- The "New Folder" button appears in the toolbar alongside existing buttons (Copy, Move, Delete, etc.).
- The dialog pre-populates with an empty text field (no default folder name).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a new folder via F7 or toolbar button in under 5 seconds (dialog open to folder visible).
- **SC-002**: Multi-level folder paths (up to 10 levels deep) are created correctly in a single operation.
- **SC-003**: Folder creation works in both local filesystem and GCS bucket contexts without errors.
- **SC-004**: Invalid inputs (empty name, existing folder, permission denied) produce clear, user-readable error messages.
