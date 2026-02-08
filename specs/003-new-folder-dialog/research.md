# Research: New Folder Dialog

**Feature**: 003-new-folder-dialog
**Date**: 2026-02-08

## Decision 1: Dialog Implementation Approach

**Decision**: Create a custom `tk.Toplevel` modal dialog with a text entry field, following the existing `ConflictDialog` pattern.

**Rationale**: The dialog needs a text input field (not just buttons), so `messagebox` is insufficient. The codebase already has modal dialogs (`ConflictDialog`, `ProgressDialog`, `SignInDialog`) that use `tk.Toplevel` with `transient()`, `grab_set()`, `wait_window()`, and `_center_on_parent()`. Following the same pattern ensures consistency.

**Alternatives considered**:
- `simpledialog.askstring()`: Provides a basic text input dialog but offers no control over layout, validation, or button labels. Rejected for lack of customization.
- Custom `ttk.Toplevel`: Same as chosen approach. `tk.Toplevel` vs `ttk.Toplevel` — no difference since ttk doesn't have its own Toplevel.

## Decision 2: Local Filesystem Folder Creation

**Decision**: Add a `create_directory(path: Path)` method to `LocalFilesystem` that uses `Path.mkdir(parents=True)` to support multi-level paths like "a/b/c".

**Rationale**: The `LocalFilesystem` service already handles file/directory operations (`copy_directory`, `delete_directory`, `list_directory`). Adding `create_directory` keeps the service as the single interface for local filesystem operations. Using `parents=True` handles multi-level paths in a single call.

**Alternatives considered**:
- Calling `Path.mkdir()` directly from the UI layer: Violates the service separation pattern used throughout the codebase. Rejected.
- Using `os.makedirs()`: Functionally equivalent but `pathlib` is the standard used in this codebase. Rejected for consistency.

## Decision 3: GCS Folder Creation

**Decision**: Add a `create_folder(bucket_name: str, prefix: str)` method to `GCSClient` that uploads a zero-byte blob with a trailing slash.

**Rationale**: GCS doesn't have real directories — folders are represented by zero-byte objects ending in "/". This is the standard GCS convention used by the Google Cloud Console and gsutil. The `GCSClient` already handles all GCS operations, so adding `create_folder` maintains the pattern.

**Alternatives considered**:
- No method needed (folders appear implicitly when objects are created under a prefix): While true for listing, explicit folder creation provides immediate visual feedback. Users expect to see the folder immediately after creation. Rejected.
- Reuse `upload_file` with empty content: Semantically confusing. A dedicated method is clearer. Rejected.

## Decision 4: Toolbar Button Placement and Enable/Disable

**Decision**: Add "New Folder (F7)" button to the toolbar between "Refresh" and the existing action buttons. The button is always enabled except when the panel shows a GCS project listing (bucket list).

**Rationale**: New Folder doesn't depend on having items selected — it creates a folder in the current directory regardless of selection. So it should NOT be disabled when nothing is selected (unlike Copy/Move/Delete). It only needs to be disabled on GCS project listing where folder creation makes no sense.

**Alternatives considered**:
- Always enabled: Would allow clicking when on GCS project listing, requiring error handling. Slightly worse UX. Rejected.
- Disabled when no items exist: Unnecessary — empty directories are valid targets for folder creation. Rejected.

## Decision 5: Error Handling for Existing Folders

**Decision**: Show an error via `messagebox.showerror` if the folder already exists (local) or if the GCS upload fails, and keep the dialog open for retry.

**Rationale**: Users should be able to correct their input without reopening the dialog. The error appears as a separate messagebox, and the New Folder dialog remains open for editing.

**Alternatives considered**:
- Close dialog and show error: Forces user to reopen dialog and retype. Poor UX. Rejected.
- Inline validation in dialog: More complex UI with error labels. Over-engineering for this use case. Rejected.
