# Implementation Plan: Copy & Move Operations with Confirmation Dialog

**Branch**: `002-copy-move-dialog` | **Date**: 2026-02-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-copy-move-dialog/spec.md`

## Summary

Replace the clipboard-based copy/move workflow (Cmd+C → Cmd+V) with a direct confirmation dialog flow (F5/F6). When the user selects files and presses F5 (Copy) or F6 (Move), a modal dialog confirms the operation and destination (opposite panel). On confirmation, the existing transfer manager executes the operation with progress feedback. This eliminates the clipboard/paste step and aligns with Total Commander conventions.

## Technical Context

**Language/Version**: Python 3.10+ (Python 3.13 in current dev environment)
**Primary Dependencies**: tkinter/ttk (GUI), google-cloud-storage (GCS API)
**Storage**: Local filesystem + GCS buckets
**Testing**: pytest
**Target Platform**: macOS and Windows (cross-platform)
**Project Type**: Single desktop application
**Performance Goals**: Confirmation dialog appears within 1 second; UI never blocks >100ms
**Constraints**: <200MB memory; all long operations use background threads with progress
**Scale/Scope**: Dual-panel file manager with local and GCS support

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Cross-Platform Parity | PASS | F5/F6 keys work identically on macOS and Windows. Dialog uses ttk widgets. No platform-specific code needed. |
| II. Native Look & Feel | PASS | Uses ttk themed widgets. Dialog button order follows platform conventions (already handled by tkinter messagebox patterns). Toolbar labels will show F5/F6 instead of Cmd/Ctrl shortcuts. |
| III. Performance | PASS | Dialog is instant (no I/O). Transfer operations already use background threads with progress callbacks. |
| IV. Testability | PASS | Confirmation dialog logic is separable from UI. Transfer manager already has injectable callbacks. New dialog is a simple modal with testable state. |

**Gate result: PASS** — No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-copy-move-dialog/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── models/
│   └── transfer_operation.py   # TransferDestination, TransferOperation (existing)
├── services/
│   └── transfer_manager.py     # Copy/move/delete orchestration (existing, no changes)
├── ui/
│   ├── app.py                  # MODIFY: shortcuts, _on_copy/_on_move rewrite, remove paste
│   ├── toolbar.py              # MODIFY: button labels (F5/F6 instead of Cmd+C/X)
│   └── dialogs/
│       ├── confirm_transfer.py # NEW: confirmation dialog for copy/move
│       └── progress.py         # Existing progress dialog (no changes)
└── platform/
    └── base.py                 # get_modifier_symbol (used for toolbar labels)

tests/
├── unit/
│   └── test_confirm_transfer.py  # NEW: tests for confirmation dialog logic
└── integration/
```

**Structure Decision**: Single project structure matching existing layout. One new file (`confirm_transfer.py`) in the existing `ui/dialogs/` package. All other changes are modifications to existing files.
