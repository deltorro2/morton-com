# Tasks: New Folder Dialog

**Input**: Design documents from `/specs/003-new-folder-dialog/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Service-layer methods that both local and GCS user stories depend on

- [x] T001 [P] Add `create_directory(path)` method to `src/services/local_filesystem.py`
- [x] T002 [P] Add `create_folder(bucket_name, prefix)` method to `src/services/gcs_client.py`
- [x] T003 Create `NewFolderDialog` modal dialog in `src/ui/dialogs/new_folder.py`

**Checkpoint**: Foundation ready — service methods and dialog exist, user story wiring can begin

---

## Phase 2: User Story 1 — Create Folder on Local Filesystem (Priority: P1) MVP

**Goal**: User presses F7 or clicks toolbar button, enters a folder name, and a local folder is created

**Independent Test**: Press F7 in a local directory, enter "TestFolder", click OK — folder appears in listing

### Implementation for User Story 1

- [x] T004 [US1] Add "New Folder (F7)" button and `on_new_folder` callback to `src/ui/toolbar.py`
- [x] T005 [US1] Add F7 keyboard binding in `_bind_shortcuts()` in `src/ui/app.py`
- [x] T006 [US1] Implement `_on_new_folder()` handler in `src/ui/app.py` (local filesystem path)
- [x] T007 [US1] Wire `on_new_folder=self._on_new_folder` in Toolbar constructor in `src/ui/app.py`

**Checkpoint**: F7 and toolbar button create local folders. Multi-level paths (a/b/c) work. Error handling for existing folders and permission denied.

---

## Phase 3: User Story 2 — Create Folder in GCS Bucket (Priority: P2)

**Goal**: User presses F7 while viewing a GCS bucket, enters a prefix name, and a GCS folder prefix is created

**Independent Test**: Press F7 in a GCS bucket view, enter "test-prefix", click OK — prefix appears in listing

### Implementation for User Story 2

- [x] T008 [US2] Add GCS bucket path to `_on_new_folder()` in `src/ui/app.py`

**Checkpoint**: F7 creates folders in both local filesystem and GCS buckets.

---

## Phase 4: User Story 3 — Toolbar Button Access (Priority: P3)

**Goal**: Mouse-oriented users can click the toolbar button instead of pressing F7

**Independent Test**: Click "New Folder (F7)" button — same dialog appears as F7

*No additional tasks needed — T004 and T007 already wire the toolbar button callback. This story is automatically satisfied by Phase 2 implementation.*

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T009 Disable "New Folder" button when active panel shows GCS project listing in `src/ui/app.py`
- [x] T010 Run existing tests to verify no regressions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — can start immediately
  - T001 and T002 are parallelizable (different files)
  - T003 has no dependencies on T001/T002
- **User Story 1 (Phase 2)**: Depends on T001 (local_filesystem) and T003 (dialog)
- **User Story 2 (Phase 3)**: Depends on T002 (gcs_client), T003 (dialog), and T006 (handler exists)
- **Polish (Phase 5)**: Depends on all user stories complete

### Parallel Opportunities

```text
# Phase 1 — all three tasks can run in parallel:
T001: Add create_directory to local_filesystem.py
T002: Add create_folder to gcs_client.py
T003: Create NewFolderDialog in new_folder.py

# Phase 2 — T004 and T005 can run in parallel (different files):
T004: Add toolbar button in toolbar.py
T005: Add F7 binding in app.py
# Then T006 and T007 sequentially (same file: app.py)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: T001 + T003 (local service + dialog)
2. Complete Phase 2: T004-T007 (toolbar + shortcut + handler)
3. **STOP and VALIDATE**: F7 creates local folders, multi-level paths work
4. Continue to User Story 2 for GCS support

### Summary

| Metric | Value |
|--------|-------|
| Total tasks | 10 |
| US1 tasks | 4 |
| US2 tasks | 1 |
| US3 tasks | 0 (covered by US1) |
| Foundational tasks | 3 |
| Polish tasks | 2 |
| Parallel opportunities | T001+T002+T003, T004+T005 |
