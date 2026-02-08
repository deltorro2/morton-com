# Quickstart: New Folder Dialog

**Feature**: 003-new-folder-dialog
**Branch**: `003-new-folder-dialog`

## Overview

Adds a "New Folder (F7)" button to the toolbar and F7 keyboard shortcut. Shows a modal dialog for entering a folder name, then creates the folder in the active panel's current directory (local filesystem) or bucket prefix (GCS). Supports multi-level paths like "a/b/c".

## Files to Change

### New Files
1. **`src/ui/dialogs/new_folder.py`** — Modal dialog with text entry for folder name

### Modified Files
1. **`src/services/local_filesystem.py`** — Add `create_directory(path)` method
2. **`src/services/gcs_client.py`** — Add `create_folder(bucket_name, prefix)` method
3. **`src/ui/toolbar.py`** — Add "New Folder (F7)" button + `on_new_folder` callback
4. **`src/ui/app.py`** — Add F7 binding, `_on_new_folder()` handler, toolbar wiring

## Implementation Steps

### Step 1: Add `create_directory` to LocalFilesystem

- Add method `create_directory(self, path: Path) -> None`
- Use `path.mkdir(parents=True, exist_ok=False)`
- Wrap errors in `FileSystemError` with user-friendly messages
- Handle: `FileExistsError`, `PermissionError`, `OSError`

### Step 2: Add `create_folder` to GCSClient

- Add method `create_folder(self, bucket_name: str, prefix: str) -> None`
- Upload zero-byte blob with name = prefix (ensure trailing "/")
- Wrap errors via existing `_map_exception` pattern

### Step 3: Create NewFolderDialog

- Follow existing `ConflictDialog` pattern: `tk.Toplevel`, `transient()`, `grab_set()`, `wait_window()`
- Layout: Label + Entry + OK/Cancel buttons
- Store result in `self.folder_name` (str or None)
- Bind Enter → OK, Escape → Cancel
- Focus entry on open

### Step 4: Add toolbar button

- Add `on_new_folder` parameter to `Toolbar.__init__`
- Add `("new_folder", "New Folder (F7)", "new_folder")` to `btn_defs`
- Note: New Folder should NOT be in the `set_actions_enabled` group (it doesn't depend on selection)

### Step 5: Wire up in App

- Add `on_new_folder=self._on_new_folder` to Toolbar constructor
- Add `self._root.bind("<F7>", lambda e: self._on_new_folder())` in `_bind_shortcuts`
- Implement `_on_new_folder()`:
  1. Check active panel source_type is not GCS_PROJECT
  2. Show `NewFolderDialog`
  3. If folder_name is not None:
     - LOCAL: call `local_fs.create_directory(Path(location) / folder_name)`
     - GCS_BUCKET: call `gcs_client.create_folder(bucket_name, prefix + folder_name)`
  4. On success: refresh active panel
  5. On error: show `messagebox.showerror`

## Testing

```bash
# Run existing tests to verify no regressions
source venv/bin/activate
pytest tests/

# Manual testing
python -m src
# 1. In local panel, press F7 → dialog appears
# 2. Enter "TestFolder" → click OK → folder appears in listing
# 3. Press F7 → enter "A/B/C" → click OK → folder hierarchy created
# 4. Press F7 → enter "TestFolder" → click OK → error: already exists
# 5. Press F7 → click Cancel → nothing happens
# 6. Press F7 → enter empty name → click OK → nothing happens
# 7. Switch to GCS bucket, press F7 → enter "test-prefix" → click OK → prefix created
# 8. Switch to GCS project listing → F7 does nothing, button disabled
# 9. Click "New Folder (F7)" toolbar button → same behavior as F7
```

## Key Design Decisions

- **Custom dialog over `simpledialog.askstring`**: Need control over layout, validation, and Enter/Escape bindings. Consistent with existing dialog patterns.
- **`parents=True` for local mkdir**: Supports multi-level paths in one call. Single-level paths work the same way.
- **Zero-byte blob for GCS folders**: Standard GCS convention. Folder appears immediately in listing.
- **Button always enabled (except GCS_PROJECT)**: New Folder doesn't require items to be selected — it creates in the current directory.
