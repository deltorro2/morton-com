# Implementation Plan: New Folder Dialog

**Branch**: `003-new-folder-dialog` | **Date**: 2026-02-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-new-folder-dialog/spec.md`

## Summary

Add a "New Folder (F7)" button to the toolbar and F7 keyboard shortcut that opens a modal dialog for creating folders. Supports local filesystem (via `Path.mkdir`) and GCS buckets (via zero-byte blob upload). Multi-level paths like "a/b/c" are supported.

## Technical Context

**Language/Version**: Python 3.10+ (currently running on 3.13)
**Primary Dependencies**: tkinter/ttk (GUI), google-cloud-storage (GCS API), pathlib (file paths)
**Storage**: Local filesystem + GCS buckets
**Testing**: pytest
**Target Platform**: macOS and Windows (cross-platform via tkinter)
**Project Type**: Single desktop application
**Performance Goals**: Folder creation completes in under 5 seconds
**Constraints**: UI must never block for more than 100ms; GCS operations run in background thread
**Scale/Scope**: Dual-panel file manager with local + GCS support

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Cross-Platform Parity | PASS | F7 key works on both platforms; `pathlib.Path` for local paths |
| II. Native Look & Feel | PASS | Using `ttk` widgets; modal dialog follows existing pattern |
| III. Performance | PASS | Local mkdir is instant; GCS upload uses background thread |
| IV. Testability | PASS | Services are injectable; dialog result is testable |

## Project Structure

### Documentation (this feature)

```text
specs/003-new-folder-dialog/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── models/              # No new models needed
├── services/
│   ├── local_filesystem.py  # Add create_directory() method
│   └── gcs_client.py        # Add create_folder() method
├── ui/
│   ├── app.py               # Add F7 binding + _on_new_folder()
│   ├── toolbar.py            # Add "New Folder (F7)" button
│   └── dialogs/
│       └── new_folder.py     # NEW: Modal dialog for folder name input
tests/
└── unit/
```

**Structure Decision**: Single project layout. New dialog file `src/ui/dialogs/new_folder.py` follows existing dialog patterns (ConflictDialog, ProgressDialog).
