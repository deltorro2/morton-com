# Research: Copy & Move Operations with Confirmation Dialog

**Feature**: 002-copy-move-dialog
**Date**: 2026-02-08

## Decision 1: Confirmation Dialog Approach

**Decision**: Use a custom `ttk.Toplevel` modal dialog instead of `tkinter.messagebox`.

**Rationale**: The standard `messagebox.askyesno` only supports Yes/No buttons. The spec requires OK/Cancel buttons and a specific message format ("Are you sure you want to [Copy/Move] these objects to [path]?"). A custom dialog also allows future extension (e.g., editable destination path, file count display).

**Alternatives considered**:
- `messagebox.askokcancel()`: Provides OK/Cancel buttons but the message is plain text with no control over layout. Viable but limits future extensibility. Could work as a simple first implementation.
- Custom `ttk.Toplevel`: Full control over message, button labels, and layout. Consistent with the existing `ProgressDialog` and `ConflictDialog` patterns in the codebase.

**Final choice**: Use `messagebox.askokcancel()` for initial implementation — it meets all current requirements with zero new code. If richer formatting is needed later, upgrade to custom dialog.

## Decision 2: Removing Clipboard Model

**Decision**: Replace the clipboard-based copy/move (Cmd+C/X → Cmd+V) with direct F5/F6 operations that immediately show the confirmation dialog.

**Rationale**: The clipboard model requires three steps (select → copy/cut → paste) while the spec requires two steps (select → F5/F6 → confirm). The `_clipboard`, `_clipboard_is_cut`, and `_clipboard_source_panel` state variables become unnecessary.

**Alternatives considered**:
- Keep clipboard alongside F5/F6: Adds complexity with two ways to do the same thing. Rejected for simplicity.
- Keep Cmd+C/V for clipboard, F5/F6 for direct: Confusing UX with two different workflows. Rejected per FR-012.

## Decision 3: Keyboard Shortcut Mapping

**Decision**: F5 → Copy, F6 → Move. Remove Cmd+C, Cmd+X, Cmd+V bindings for file operations.

**Rationale**: Matches Total Commander / Norton Commander convention that the application follows. F5 is currently bound to `_on_refresh` which conflicts — F5 must be reassigned to Copy. Refresh keeps Cmd+R binding.

**Alternatives considered**:
- Keep F5 as Refresh, use different keys for Copy/Move: Breaks Total Commander convention. Rejected.
- Bind F5/F6 alongside existing Cmd shortcuts: FR-012 requires removing old shortcuts. Rejected.

## Decision 4: Toolbar Button Labels

**Decision**: Update toolbar button labels from "Copy (Cmd+C)" to "Copy (F5)" and "Move (Cmd+X)" to "Move (F6)".

**Rationale**: Button labels should reflect the actual shortcut. Since the modifier symbol comes from `platform.get_modifier_symbol()`, the F5/F6 labels are platform-agnostic and simpler.

**Alternatives considered**:
- Remove shortcut hints from labels: Users lose discoverability. Rejected.

## Decision 5: Destination Path Display

**Decision**: Show the opposite panel's full location path in the confirmation dialog. For local: the directory path. For GCS: `gs://bucket-name/prefix/`.

**Rationale**: Users need to know exactly where files will go before confirming. The opposite panel's `state.location` and `state.bucket_name` already provide this information.

**Alternatives considered**:
- Show only the last directory name: Ambiguous if multiple directories have the same name. Rejected.
- Allow editing the destination in the dialog: Out of scope for this feature. Can be added later.
