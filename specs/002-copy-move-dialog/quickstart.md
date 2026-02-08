# Quickstart: Copy & Move Operations with Confirmation Dialog

**Feature**: 002-copy-move-dialog
**Branch**: `002-copy-move-dialog`

## Overview

This feature replaces the clipboard-based copy/move (Cmd+C → Cmd+V) with a direct F5/F6 confirmation flow matching Total Commander. Selecting files and pressing F5 (Copy) or F6 (Move) shows a confirmation dialog, then executes the transfer to the opposite panel with progress feedback.

## Files to Change

### New Files
1. **`src/ui/dialogs/confirm_transfer.py`** — Confirmation dialog (or use `messagebox.askokcancel`)

### Modified Files
1. **`src/ui/app.py`** — Rewrite `_on_copy`/`_on_move`, remove `_on_paste`, change shortcuts
2. **`src/ui/toolbar.py`** — Update button labels from "Cmd+C/X" to "F5/F6"

## Implementation Steps

### Step 1: Update Keyboard Shortcuts (app.py)
- Remove: Cmd+C, Cmd+X, Cmd+V bindings
- Remove: F5 → refresh binding
- Add: F5 → `_on_copy()`, F6 → `_on_move()`
- Keep: Cmd+R and BackSpace for refresh/navigate

### Step 2: Rewrite _on_copy and _on_move (app.py)
- Remove clipboard state (`_clipboard`, `_clipboard_is_cut`, `_clipboard_source_panel`)
- New `_on_copy()`: get selected items → show confirmation → execute copy to opposite panel
- New `_on_move()`: get selected items → show confirmation → execute move to opposite panel
- Remove `_on_paste()` entirely

### Step 3: Update Toolbar Labels (toolbar.py)
- Change "Copy ({mod}C)" → "Copy (F5)"
- Change "Move ({mod}X)" → "Move (F6)"

### Step 4: Create Confirmation Dialog
- Use `messagebox.askokcancel(title, message, parent=root)` for simplicity
- Message format: "Are you sure you want to [Copy/Move] these objects to [path]?"

## Testing

```bash
# Run existing tests to verify no regressions
source venv/bin/activate
pytest tests/

# Manual testing
python -m src
# 1. Select files in left panel
# 2. Press F5 → verify confirmation dialog with correct destination
# 3. Click OK → verify progress and files copied to right panel
# 4. Select files in right panel
# 5. Press F6 → verify confirmation dialog
# 6. Click OK → verify files moved to left panel
# 7. Press F5 with no selection → verify nothing happens
# 8. Press Cancel on dialog → verify no operation
```

## Key Design Decisions

- **`messagebox.askokcancel` over custom dialog**: Meets all requirements with zero new widget code. Upgrade to custom dialog if richer UI needed later.
- **No clipboard state**: Eliminated entirely. Operations are direct (select → confirm → execute).
- **F5 reassigned from Refresh**: Refresh keeps Cmd+R. F5 becomes Copy per Total Commander convention.
