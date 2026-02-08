# UI Contracts: Copy & Move Operations

**Feature**: 002-copy-move-dialog
**Date**: 2026-02-08

## Keyboard Shortcuts

| Key | Action | Replaces |
|-----|--------|----------|
| F5 | Copy selected items to opposite panel (with confirmation) | Cmd+C (copy to clipboard) + Cmd+V (paste) |
| F6 | Move selected items to opposite panel (with confirmation) | Cmd+X (cut to clipboard) + Cmd+V (paste) |

### Removed Shortcuts

| Key | Previous Action | Reason |
|-----|-----------------|--------|
| Cmd+C / Ctrl+C | Copy to clipboard | Replaced by F5 direct operation |
| Cmd+X / Ctrl+X | Cut to clipboard | Replaced by F6 direct operation |
| Cmd+V / Ctrl+V | Paste from clipboard | No longer needed (no clipboard) |
| F5 | Refresh | Reassigned to Copy; Refresh keeps Cmd+R |

## Toolbar Buttons

| Button | Label | Shortcut Hint | Callback |
|--------|-------|---------------|----------|
| Copy | Copy (F5) | F5 | `_on_copy()` |
| Move | Move (F6) | F6 | `_on_move()` |
| Delete | Delete (Del) | Del | `_on_delete()` (unchanged) |
| Properties | Properties ({mod}I) | Cmd/Ctrl+I | `_on_properties()` (unchanged) |
| Refresh | Refresh ({mod}R) | Cmd/Ctrl+R | `_on_refresh()` (unchanged) |

## Confirmation Dialog Contract

### Trigger
- F5 pressed OR Copy button clicked → Copy confirmation
- F6 pressed OR Move button clicked → Move confirmation
- Precondition: active panel has selected items (not "..")

### Dialog Specification

- **Type**: Modal (blocks main window)
- **Title**: "Copy" or "Move"
- **Message**: "Are you sure you want to [Copy/Move] these objects to [destination_path]?"
- **Buttons**: OK, Cancel
- **Behavior**:
  - OK → start transfer operation with progress dialog
  - Cancel → close dialog, no action

### Destination Path Format

| Panel Source Type | Destination Path Display |
|-------------------|-------------------------|
| LOCAL | Full directory path (e.g., `/Users/michael/Documents`) |
| GCS_PROJECT | Not applicable (bucket list — no file operations) |
| GCS_BUCKET | `gs://bucket-name/prefix/` or `gs://bucket-name/` |

## Progress Dialog Contract (existing, no changes)

- Shown after user confirms Copy/Move
- Displays: current file, progress bar, file count
- Cancel button available
- Auto-closes on completion
