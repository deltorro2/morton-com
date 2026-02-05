# Tasks: Dual-Panel File Manager

**Input**: Design documents from `/specs/001-dual-panel-filemanager/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/services.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US0, US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, packaging configuration, and basic directory structure

- [x] T001 Create project directory structure per plan.md: `src/`, `src/models/`, `src/services/`, `src/ui/`, `src/ui/dialogs/`, `src/ui/widgets/`, `src/platform/`, `tests/`, `tests/unit/`, `tests/integration/`, `tests/fixtures/`, `config/`
- [x] T002 Create `pyproject.toml` with project metadata (PEP 621), runtime dependencies (`google-cloud-storage>=2.14.0`, `google-auth>=2.28.0`, `google-auth-oauthlib>=1.2.0`, `keyring>=25.0.0`, `cryptography>=42.0.0`) and dev dependencies (`pytest>=8.0.0`, `pytest-mock>=3.12.0`, `pytest-cov>=4.1.0`, `mypy>=1.8.0`, `ruff>=0.2.0`, `pyinstaller>=6.3.0`). Include `[project.scripts]` entry and `pip install -e ".[dev]"` support
- [x] T003 [P] Create `config/projects.json.example` with sample GCP project configuration per quickstart.md
- [x] T004 [P] Create all `__init__.py` files: `src/__init__.py`, `src/models/__init__.py`, `src/services/__init__.py`, `src/ui/__init__.py`, `src/ui/dialogs/__init__.py`, `src/ui/widgets/__init__.py`, `src/platform/__init__.py`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`
- [x] T005 [P] Create `tests/conftest.py` with shared pytest fixtures (temp directories, mock GCS credentials, sample FileItem/GCSObject factories)

**Checkpoint**: Project skeleton ready, `pip install -e ".[dev]"` succeeds, `pytest` runs (0 tests collected)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, enumerations, error hierarchy, platform abstraction, and configuration — required before ANY user story

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Create enumerations in `src/models/__init__.py`: `SourceType`, `OperationType`, `TransferStatus`, `ConflictResolution`, `AuthState` per data-model.md
- [x] T007 [P] Create `MortonError` exception hierarchy in `src/models/__init__.py` (or `src/errors.py`): `MortonError` base with `user_message`, `suggested_action`, `technical_detail` fields; subclasses `AuthenticationError`, `PermissionError`, `NetworkError`, `TransferError`, `ConfigurationError`, `FileSystemError` per contracts/services.md
- [x] T008 [P] Create `FileItem` dataclass in `src/models/file_item.py` with fields: `name`, `path`, `size`, `modified_date`, `created_date`, `is_directory`, `permissions`, `is_hidden`. Include derived properties: `display_size`, `extension`, `icon_type` per data-model.md
- [x] T009 [P] Create `GCSObject` dataclass in `src/models/gcs_object.py` with fields: `name`, `bucket_name`, `size`, `content_type`, `storage_class`, `created_time`, `updated_time`, `generation`, `metadata`, `md5_hash`. Include derived properties: `display_name`, `prefix`, `display_size`, `is_prefix` per data-model.md
- [x] T010 [P] Create `GCSBucket` dataclass in `src/models/gcs_bucket.py` with fields: `name`, `project_id`, `location`, `storage_class`, `created_time`, `versioning_enabled`. Include `display_location` derived property per data-model.md
- [x] T011 [P] Create `PanelState` dataclass in `src/models/panel_state.py` with fields: `id`, `source_type`, `location`, `project_id`, `bucket_name`, `items`, `selected_indices`, `sort_column`, `sort_ascending`, `loading`, `error` per data-model.md
- [x] T012 [P] Create `TransferOperation` dataclass in `src/models/transfer_operation.py` with fields per data-model.md: `id`, `operation_type`, `source_items`, `destination`, `status`, `progress_percent`, `current_file`, `current_file_progress`, `bytes_transferred`, `total_bytes`, `started_at`, `completed_at`, `error_message`, `files_completed`, `files_total`. Include `TransferDestination` value object
- [x] T013 [P] Create `UserSession` dataclass in `src/models/user_session.py` with fields: `email`, `access_token`, `refresh_token`, `token_expiry`, `scopes`, `signed_in_at`. Include derived properties: `is_authenticated`, `is_expired`, `needs_refresh`, `display_name` per data-model.md
- [x] T014 [P] Create `Configuration` and `ProjectConfig` dataclasses in `src/config.py` with fields per data-model.md: `projects`, `max_concurrent_transfers`, `show_hidden_files`, `confirm_delete`, `window_state`
- [x] T015 Implement `PlatformService` base class in `src/platform/base.py` with abstract methods: `get_config_directory()`, `get_modifier_key()`, `get_modifier_symbol()`, `get_dialog_button_order()`, `is_dark_mode()`, `get_default_font_family()`, `open_browser()`, `open_file_externally()`, `reveal_in_finder()` per contracts/services.md
- [x] T016 [P] Implement `MacOSPlatform` in `src/platform/macos.py` implementing all `PlatformService` methods: config dir `~/.config/morton-com`, modifier key `Cmd`/`⌘`, dark mode detection via `defaults read`, browser via `webbrowser.open()`, `open` subprocess commands
- [x] T017 [P] Implement `WindowsPlatform` in `src/platform/windows.py` implementing all `PlatformService` methods: config dir `%APPDATA%\morton-com`, modifier key `Ctrl`/`Ctrl+`, dark mode detection via registry, browser via `webbrowser.open()`, `os.startfile` for file operations
- [x] T018 Create platform detector factory in `src/platform/__init__.py` that returns `MacOSPlatform` or `WindowsPlatform` based on `sys.platform`
- [x] T019 Implement `ConfigManagerService` in `src/services/config_manager.py`: `load()` reads `settings.json` and `projects.json` from platform config dir, `save()` writes back, `get_projects()`, `add_project()`, `remove_project()` per contracts/services.md. Use `Configuration` and `ProjectConfig` models. Create config dir if it doesn't exist
- [x] T020 Implement `LocalFilesystemService` in `src/services/local_filesystem.py`: `list_directory()` using `pathlib.Path.iterdir()` returning `FileItem` list, `get_file_info()`, `copy_file()` with progress callback using chunked copy, `copy_directory()` recursive with progress, `move_file()`, `delete_file()`, `delete_directory()`, `exists()`, `get_home_directory()` per contracts/services.md

**Checkpoint**: All models importable, platform detection works, config loads/saves, local filesystem operations functional. Run `pytest` to verify model creation and basic service tests pass

---

## Phase 3: User Story 0 - Authenticate with GCP (Priority: P0) 🎯 MVP

**Goal**: Users can sign in via browser-based OAuth2 and the application securely stores/refreshes credentials

**Independent Test**: Launch app, attempt GCS access, complete browser sign-in, verify GCS becomes accessible. Restart app and verify stored credentials work automatically

### Implementation for User Story 0

- [x] T021 Implement `CredentialStorageService` in `src/services/credential_storage.py`: generate Fernet encryption key on first run, store key in platform keyring (service: `morton-com`, username: `oauth-key`), encrypt/decrypt token JSON with Fernet, `save()` writes to `credentials.enc`, `load()` reads and decrypts, `clear()` removes file and keyring entry, `has_credentials()` per contracts/services.md and research.md
- [x] T022 Implement `AuthService` in `src/services/auth_service.py`: `sign_in()` using `google_auth_oauthlib.flow.InstalledAppFlow` with local HTTP callback server, runs in background thread; `sign_out()` clears via `CredentialStorageService`; `refresh_token()` for proactive token refresh; `load_stored_credentials()` on startup; `get_credentials()` returns `google.oauth2.credentials.Credentials`; `ensure_authenticated()` checks state and calls appropriate callback. Manage `AuthState` transitions atomically per contracts/services.md and research.md. Required scopes: `devstorage.read_write`, `userinfo.email`
- [x] T023 Create sign-in prompt dialog in `src/ui/dialogs/auth.py`: modal dialog explaining sign-in requirement with "Sign in with Google" button and "Cancel" button. Show loading spinner while browser flow in progress. Display error message on failure with retry option
- [x] T024 Create account menu widget in `src/ui/account_menu.py`: display authenticated user email in top-right of application; dropdown menu with "Sign Out" option; confirmation dialog on sign-out per spec.md User Story 0.1
- [x] T025 Wire auth flow into application startup in `src/main.py` and `src/ui/app.py`: on launch call `auth_service.load_stored_credentials()`; when panel switches to GCS call `auth_service.ensure_authenticated()`; display sign-in prompt if needed; on success update UI and enable GCS panel

**Checkpoint**: Can sign in via browser, email displayed in app, sign out works, credentials persist across restarts, expired tokens refresh automatically

---

## Phase 4: User Story 1 - Browse Local Files (Priority: P1) 🎯 MVP

**Goal**: Users can browse their local file system in a panel with navigation, file metadata display, and selection

**Independent Test**: Launch app, verify home directory displayed, navigate folders via double-click and "..", verify file metadata (name, size, date) displays correctly

### Implementation for User Story 1

- [x] T026 Create `FileListWidget` (Treeview-based) in `src/ui/widgets/file_list.py`: ttk.Treeview with columns `Name`, `Size`, `Modified`; supports single and multi-selection; double-click handler for navigation; sorting by column click; lazy loading with "Load more..." for >1000 items; displays human-readable sizes per research.md
- [x] T027 Create `Panel` widget in `src/ui/panel.py`: contains source-type dropdown (Local/GCS), current path breadcrumb/label, `FileListWidget`, handles navigation state. Maintains `PanelState` model. Dispatches `list_directory()` via `LocalFilesystemService` in background thread. Shows loading indicator. Shows ".." entry for parent navigation per spec.md FR-001, FR-002, FR-004
- [x] T028 Create toolbar in `src/ui/toolbar.py`: action buttons for Copy, Move, Delete, Properties, Refresh. Buttons enabled/disabled based on current selection. Platform-appropriate keyboard shortcut labels per research.md
- [x] T029 Create main application window in `src/ui/app.py`: root Tk window with ttk styling, two `Panel` widgets side-by-side using PanedWindow, `Toolbar` at top, `AccountMenu` in top-right. Left panel defaults to local home directory. Wire `Tab` key to switch focus between panels. Set window title, minimum size, restore window state from config per spec.md FR-001, FR-019
- [x] T030 Create application entry point in `src/main.py`: parse arguments, initialize platform service, load configuration, create service instances (LocalFilesystemService, ConfigManager), create and launch main App window, handle graceful shutdown. Entry via `python -m src.main` per plan.md
- [x] T031 Implement selection behavior in `Panel`/`FileListWidget`: single click selects, Shift+click for range selection, Cmd/Ctrl+click for toggle selection, Cmd/Ctrl+A for select all, Space to toggle per spec.md FR-005, quickstart.md navigation table
- [x] T032 Implement keyboard shortcuts registry in `src/ui/app.py` or dedicated module: centralized shortcut bindings using platform modifier key (`Cmd` on macOS, `Ctrl` on Windows), bind Refresh (Cmd/Ctrl+R or F5), Select All (Cmd/Ctrl+A), Tab (switch panels), Enter (enter folder), Backspace (parent folder) per research.md and spec.md FR-019

**Checkpoint**: Application launches with two panels, left panel shows local home directory, can navigate folders, file metadata displays correctly, selection works, keyboard shortcuts functional

---

## Phase 5: User Story 2 - Browse GCS Buckets (Priority: P2)

**Goal**: Users can browse GCS bucket lists and bucket contents in a panel, with prefix-based folder navigation

**Independent Test**: Sign in, select GCS source for a panel, choose project, see buckets, navigate into a bucket, verify object metadata displays

### Implementation for User Story 2

- [x] T033 Implement `GCSClientService` in `src/services/gcs_client.py`: `set_credentials()` creates `google.cloud.storage.Client` with OAuth2 credentials; `list_buckets()` for a project ID; `list_objects()` with prefix/delimiter for pseudo-folder browsing; `get_object_metadata()`; `object_exists()`. Handle pagination (1000 objects per page). Raise `AuthenticationError`, `PermissionError`, `NetworkError` as appropriate per contracts/services.md
- [x] T034 Extend `Panel` widget in `src/ui/panel.py` to support GCS source types: when dropdown changes to GCS, call `auth_service.ensure_authenticated()`; if authenticated show project selector (from `ConfigManager.get_projects()`); on project select call `gcs_client.list_buckets()` in background thread; display `GCSBucket` items in `FileListWidget`. Handle `GCS_PROJECT` and `GCS_BUCKET` source types per data-model.md `SourceType`
- [x] T035 Extend `FileListWidget` in `src/ui/widgets/file_list.py` to display `GCSBucket` items (name, location, storage class, created date) and `GCSObject` items (display_name, size, content type, updated date). Double-click on bucket navigates into it; double-click on prefix navigates into prefix; ".." goes to parent prefix or back to bucket list per spec.md FR-003
- [x] T036 Integrate `GCSClientService` with `AuthService`: pass credentials from `auth_service.get_credentials()` to `gcs_client.set_credentials()` after sign-in. On 401 errors, trigger `auth_service.refresh_token()`. If refresh fails, show sign-in prompt via `on_auth_required` callback per research.md token refresh strategy

**Checkpoint**: Can sign in, switch panel to GCS, select project, browse buckets, navigate into bucket contents, see object metadata. Auth errors trigger re-authentication flow

---

## Phase 6: User Story 3 - Copy Files Between Panels (Priority: P3)

**Goal**: Users can copy files between local and GCS (in both directions) and between two local locations, with progress feedback

**Independent Test**: Select files in one panel, initiate copy to other panel, verify files appear in destination, verify progress indicator shown

### Implementation for User Story 3

- [x] T037 Implement `TransferManagerService` in `src/services/transfer_manager.py`: `copy()` method that determines transfer type (local→local, local→GCS, GCS→local, GCS→GCS) and dispatches accordingly. Uses `ThreadPoolExecutor` with configurable `max_concurrent` transfers. Creates `TransferOperation` for tracking. Recursive directory copy support. Handles `ConflictResolution` per contracts/services.md
- [x] T038 Implement local→GCS copy in `TransferManagerService`: for each `FileItem`, call `gcs_client.upload_file()` with progress callback. For directories, walk recursively creating corresponding GCS prefixes. Update `TransferOperation` progress per file per research.md (resumable uploads for >5MB)
- [x] T039 Implement GCS→local copy in `TransferManagerService`: for each `GCSObject`, call `gcs_client.download_file()` with progress callback. For prefixes, list all objects under prefix and download maintaining directory structure. Update `TransferOperation` progress per file
- [x] T040 Implement local→local copy in `TransferManagerService`: delegate to `local_filesystem.copy_file()` / `copy_directory()` with progress callbacks
- [x] T041 Implement GCS→GCS copy in `TransferManagerService`: use `gcs_client.copy_object()` for server-side copy. For prefixes, list and copy all objects under prefix
- [x] T042 Create transfer progress dialog in `src/ui/dialogs/progress.py`: modal dialog showing overall progress bar, current file name, bytes transferred/total, files completed/total, cancel button. Updates via `on_progress` callback marshaled to UI thread via `root.after()` per spec.md FR-009, FR-010
- [x] T043 Create conflict resolution dialog in `src/ui/dialogs/conflict.py`: modal dialog shown when destination file exists. Options: Overwrite, Skip, Rename (adds suffix), "Apply to all" checkbox. Per spec.md FR-016
- [x] T044 Wire copy operation into UI: bind Cmd/Ctrl+C → store selection as "clipboard", Cmd/Ctrl+V → initiate copy from clipboard to active panel's location. Show progress dialog. Refresh destination panel on completion. Handle `on_auth_required` callback per spec.md FR-006

**Checkpoint**: Can copy files between any combination of local and GCS panels. Progress shown. Conflicts handled. Recursive folder copy works

---

## Phase 7: User Story 4 - Move Files Between Panels (Priority: P4)

**Goal**: Users can move files between panels (copy + delete source), with progress feedback

**Independent Test**: Select files, initiate move, verify files exist in destination and NOT in source

### Implementation for User Story 4

- [x] T045 Implement `move()` in `TransferManagerService`: execute `copy()` first, then on successful completion delete source files/objects. If copy fails, source remains intact. Update `TransferOperation` status throughout per contracts/services.md and spec.md FR-007
- [x] T046 Wire move operation into UI: bind Cmd/Ctrl+X → store selection as "cut clipboard", Cmd/Ctrl+V → initiate move from cut clipboard to active panel's location. Show progress dialog. Refresh both panels on completion per spec.md User Story 4

**Checkpoint**: Can move files between any panel combination. Source files removed only after successful copy. Progress shown

---

## Phase 8: User Story 5 - Delete Files (Priority: P5)

**Goal**: Users can delete files from local or GCS with confirmation

**Independent Test**: Select files, initiate delete, confirm in dialog, verify files removed

### Implementation for User Story 5

- [x] T047 Implement `delete()` in `TransferManagerService`: delete local files via `local_filesystem.delete_file()`/`delete_directory()`, GCS objects via `gcs_client.delete_object()`. Progress callback for multi-file delete. Auth check for GCS operations per contracts/services.md
- [x] T048 Create delete confirmation dialog: list files to be deleted with total count and size, OK/Cancel buttons in platform-appropriate order. Respect `config.confirm_delete` setting per spec.md FR-008
- [x] T049 Wire delete operation into UI: bind Cmd/Ctrl+Delete and Delete key → show confirmation dialog → execute delete → refresh panel per spec.md User Story 5

**Checkpoint**: Can delete local files and GCS objects. Confirmation shown. Panel refreshes after deletion

---

## Phase 9: User Story 6 - View File Metadata (Priority: P6)

**Goal**: Users can view detailed metadata for any selected file or GCS object in a properties dialog

**Independent Test**: Select a file, open properties, verify all metadata fields displayed correctly

### Implementation for User Story 6

- [x] T050 Create properties dialog in `src/ui/dialogs/properties.py`: for local `FileItem` show full path, exact size, created date, modified date, permissions. For `GCSObject` show full path (bucket + name), size, content type, storage class, created time, updated time, generation, custom metadata key-value pairs. For `GCSBucket` show name, project, location, storage class, created time, versioning status per spec.md FR-015
- [x] T051 Wire properties dialog into UI: bind Cmd/Ctrl+I and Alt+Enter → open properties for selected item. Also accessible via toolbar button and right-click context menu per spec.md FR-019

**Checkpoint**: Can view detailed properties for local files, GCS objects, and GCS buckets

---

## Phase 10: User Story 7 - Switch Panel Source (Priority: P7)

**Goal**: Users can independently switch each panel between local filesystem, GCS project list, and GCS bucket contents

**Independent Test**: Switch panel source types, verify each view loads correctly, verify both panels can show same source type

### Implementation for User Story 7

- [x] T052 Finalize panel source switching in `src/ui/panel.py`: dropdown options "Local", plus one entry per configured GCS project. Switching to Local shows home directory. Switching to GCS project shows bucket list (with auth check). Both panels independently configurable. Support local-to-local, GCS-to-GCS, and mixed configurations per spec.md FR-013, FR-014, User Story 7
- [x] T053 Implement panel refresh (Cmd/Ctrl+R and F5): re-fetch current listing from source (local `list_directory()` or GCS `list_objects()`/`list_buckets()`). Preserve selection and scroll position where possible per spec.md FR-019

**Checkpoint**: Can freely switch any panel between local and GCS views. Both panels independent. Refresh works

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Settings dialog, error handling polish, window state persistence, and final integration

- [x] T054 Create settings dialog in `src/ui/dialogs/settings.py`: allow editing `max_concurrent_transfers` (1-10 slider/spinner), `show_hidden_files` toggle, `confirm_delete` toggle. Save via `ConfigManagerService` per data-model.md Configuration entity
- [x] T055 Implement show/hide hidden files: respect `config.show_hidden_files` in both `LocalFilesystemService.list_directory()` (filter `is_hidden`) and panel display. Toggle via settings per spec.md
- [x] T056 Implement window state persistence: save window size/position on close, restore on launch via `Configuration.window_state` and `ConfigManagerService` per data-model.md
- [x] T057 Polish error handling across all services: ensure all GCS errors map to `MortonError` subclasses with `user_message` and `suggested_action`. Show error dialogs in UI with clear messages per spec.md FR-018 and contracts/services.md error hierarchy
- [x] T058 [P] Add file metadata preservation during copy/move: preserve modification times for local copies (`shutil.copy2`), set custom metadata for GCS uploads where applicable per spec.md FR-017
- [x] T059 [P] Implement cancellation for in-progress transfers: `TransferManagerService.cancel()` sets operation status and stops between chunks. UI cancel button in progress dialog triggers cancellation per spec.md FR-010
- [x] T060 Run quickstart.md verification checklist: verify all 12 items from quickstart.md pass (app launches with two panels, local browsing, GCS sign-in flow, bucket navigation, file copy to/from GCS, sign-out)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T005) — BLOCKS all user stories
- **User Story 0 (Phase 3)**: Depends on Foundational — Authentication must work before GCS stories
- **User Story 1 (Phase 4)**: Depends on Foundational — Can run in parallel with US0 (local browsing doesn't need auth)
- **User Story 2 (Phase 5)**: Depends on Foundational + US0 (requires auth for GCS)
- **User Story 3 (Phase 6)**: Depends on US1 + US2 (needs both panels browsable)
- **User Story 4 (Phase 7)**: Depends on US3 (move = copy + delete source)
- **User Story 5 (Phase 8)**: Depends on Foundational + US0 (for GCS delete). Can start after US1 for local-only delete
- **User Story 6 (Phase 9)**: Depends on US1 + US2 (needs items to inspect)
- **User Story 7 (Phase 10)**: Depends on US1 + US2 (needs both source types implemented)
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies (Graph)

```
Setup (Phase 1)
  └──▶ Foundational (Phase 2)
        ├──▶ US0: Auth (Phase 3)
        │     ├──▶ US2: Browse GCS (Phase 5)
        │     │     ├──▶ US3: Copy (Phase 6) ◄── also needs US1
        │     │     │     └──▶ US4: Move (Phase 7)
        │     │     ├──▶ US6: Metadata (Phase 9) ◄── also needs US1
        │     │     └──▶ US7: Switch Panel (Phase 10) ◄── also needs US1
        │     └──▶ US5: Delete (Phase 8) ◄── also needs US1 for local delete
        └──▶ US1: Browse Local (Phase 4) ──▶ (feeds into US2+, US3+, US5+, US6+, US7+)
```

### Parallel Opportunities

Within Phase 2 (Foundational):
- T007, T008, T009, T010, T011, T012, T013, T014 can all run in parallel (independent model/enum files)
- T016, T017 can run in parallel (independent platform implementations)

Phase 3 (US0) and Phase 4 (US1) can run in parallel:
- US0 (auth) doesn't depend on UI panels
- US1 (local browse) doesn't depend on auth

Within Phase 6 (US3 Copy):
- T038, T039, T040, T041 can run in parallel (independent transfer direction implementations)

### Within Each User Story

- Models before services
- Services before UI components
- Core implementation before integration wiring
- Story complete and verified before moving to dependent stories

---

## Implementation Strategy

### Recommended: Sequential by Priority

1. Complete Phase 1: Setup → project skeleton ready
2. Complete Phase 2: Foundational → all models, platform, config, local filesystem
3. Complete Phase 3 + 4 in parallel: US0 (Auth) + US1 (Browse Local) → core app functional
4. Complete Phase 5: US2 (Browse GCS) → dual-panel browsing works
5. Complete Phase 6: US3 (Copy) → file transfers work (primary value)
6. Complete Phase 7: US4 (Move) → builds on copy
7. Complete Phase 8: US5 (Delete) → destructive operation
8. Complete Phase 9: US6 (Metadata) → enhanced info
9. Complete Phase 10: US7 (Switch Panel) → full flexibility
10. Complete Phase 11: Polish → production-ready

### MVP Milestone

After completing Phases 1-6 (through US3 Copy), the application delivers its core value proposition: dual-panel browsing with file transfer between local and GCS. This is the earliest useful demo point.
