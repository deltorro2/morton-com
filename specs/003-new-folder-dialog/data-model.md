# Data Model: New Folder Dialog

**Feature**: 003-new-folder-dialog
**Date**: 2026-02-08

## Entities

This feature does not introduce new persistent entities. It reuses existing models:

### Existing Entities (no changes)

- **PanelState**: Panel's current view state (source_type, location, bucket_name, project_id) — used to determine where to create the folder.
- **SourceType**: Enum (LOCAL, GCS_PROJECT, GCS_BUCKET) — determines which service to use for folder creation.

### New Service Methods

- **LocalFilesystem.create_directory(path: Path)**: Creates a directory (with parents for multi-level paths). Raises `FileSystemError` on failure.
- **GCSClient.create_folder(bucket_name: str, prefix: str)**: Creates a zero-byte object with trailing "/" to represent a folder in GCS.

### Dialog State (transient, not persisted)

- **NewFolderDialog.folder_name**: The user-entered folder name, or `None` if cancelled. Only exists during dialog lifetime.

## State Transitions

### New Folder Operation Flow

```
IDLE → [F7 pressed / button clicked] → DIALOG_SHOWN
  → [Cancel / empty name] → IDLE
  → [OK with valid name] → CREATING_FOLDER
    → [Success] → PANEL_REFRESHED → IDLE
    → [Error] → ERROR_SHOWN → DIALOG_SHOWN (retry)
```
