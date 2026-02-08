# UI Contracts: New Folder Dialog

**Feature**: 003-new-folder-dialog
**Date**: 2026-02-08

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F7 | Open "New Folder" dialog for active panel |

## Toolbar Button

| Button | Label | Shortcut Hint | Callback | Enable Condition |
|--------|-------|---------------|----------|-----------------|
| New Folder | New Folder (F7) | F7 | `_on_new_folder()` | Active panel is LOCAL or GCS_BUCKET (not GCS_PROJECT) |

### Button Placement

Insert after "Refresh" in the toolbar button definitions:
```
Copy (F5) | Move (F6) | Delete (Del) | Properties (Cmd+I) | Refresh (Cmd+R) | New Folder (F7)
```

## New Folder Dialog Contract

### Trigger
- F7 pressed OR "New Folder" button clicked
- Precondition: active panel source_type is LOCAL or GCS_BUCKET

### Dialog Specification

- **Type**: Modal (blocks main window, `grab_set` + `wait_window`)
- **Title**: "New Folder"
- **Layout**:
  - Label: "Enter folder name:"
  - Text entry field (focused on open, empty by default)
  - OK button (creates folder)
  - Cancel button (closes dialog)
- **Behavior**:
  - OK → validate name → create folder → refresh panel → close dialog
  - Cancel → close dialog, no action
  - Enter key → same as OK
  - Escape key → same as Cancel
  - Empty/whitespace name → do nothing (button press ignored)

### Input Validation

| Input | Behavior |
|-------|----------|
| Empty or whitespace-only | OK button does nothing |
| Valid single name (e.g., "docs") | Create single folder |
| Multi-level path (e.g., "a/b/c") | Create all intermediate folders |
| Name with invalid chars (null bytes, etc.) | Error shown after creation attempt |
| Name that already exists (local) | Error messagebox shown, dialog stays open |

### Folder Creation by Panel Type

| Panel Source Type | Creation Method |
|-------------------|-----------------|
| LOCAL | `local_fs.create_directory(current_path / folder_name)` with `parents=True` |
| GCS_BUCKET | `gcs_client.create_folder(bucket_name, current_prefix + folder_name + "/")` |
| GCS_PROJECT | Operation not available (F7 ignored, button disabled) |
