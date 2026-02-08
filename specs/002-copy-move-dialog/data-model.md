# Data Model: Copy & Move Operations with Confirmation Dialog

**Feature**: 002-copy-move-dialog
**Date**: 2026-02-08

## Entities

This feature does not introduce new entities. It reuses existing models:

### Existing Entities (no changes)

- **TransferOperation**: Tracks a copy/move operation lifecycle (id, type, status, progress, items, destination)
- **TransferDestination**: Describes where files go (type, path, bucket_name, project_id)
- **FileItem**: Represents a local file/directory (path, name, size, is_directory, modified_date)
- **GCSObject**: Represents a GCS object (name, bucket_name, size, content_type, is_prefix)
- **PanelState**: Panel's current view state (source_type, location, bucket_name, project_id)

### Removed State

- **Clipboard state** (in App): `_clipboard`, `_clipboard_is_cut`, `_clipboard_source_panel` — removed because operations no longer use a clipboard model.

## State Transitions

### Copy/Move Operation Flow

```
IDLE → [F5/F6 pressed] → CONFIRM_DIALOG_SHOWN
  → [Cancel] → IDLE
  → [OK] → TRANSFER_RUNNING → TRANSFER_COMPLETE → IDLE (both panels refresh)
                             → TRANSFER_FAILED → ERROR_SHOWN → IDLE
```

This maps directly to existing `TransferStatus` enum values: PENDING → RUNNING → COMPLETED/FAILED.
