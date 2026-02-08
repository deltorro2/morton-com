# Tasks: Copy & Move Operations with Confirmation Dialog

**Feature**: 002-copy-move-dialog
**Date**: 2026-02-08

## Phase 1: Core Changes

- [x] **T1**: Update toolbar button labels to show F5/F6 shortcuts
  - File: `src/ui/toolbar.py`
  - Change "Copy ({mod}C)" → "Copy (F5)", "Move ({mod}X)" → "Move (F6)"

- [x] **T2**: Update keyboard shortcuts in app.py
  - File: `src/ui/app.py`
  - Remove: Cmd+C, Cmd+X, Cmd+V bindings
  - Remove: F5 → refresh binding
  - Add: F5 → `_on_copy()`, F6 → `_on_move()`

- [x] **T3**: Remove clipboard state and _on_paste from app.py
  - File: `src/ui/app.py`
  - Remove: `_clipboard`, `_clipboard_is_cut`, `_clipboard_source_panel`
  - Remove: `_on_paste()` method

- [x] **T4**: Rewrite _on_copy to show confirmation and execute transfer
  - File: `src/ui/app.py`
  - Get selected items → build destination path string → show askokcancel → execute copy → show progress

- [x] **T5**: Rewrite _on_move to show confirmation and execute transfer
  - File: `src/ui/app.py`
  - Same as T4 but for move operation

## Phase 2: Validation

- [x] **T6**: Run existing tests to verify no regressions (422 passed)
- [ ] **T7**: Manual smoke test verification
