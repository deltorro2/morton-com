# Implementation Plan: Dual-Panel File Manager

**Branch**: `001-dual-panel-filemanager` | **Date**: 2026-02-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-dual-panel-filemanager/spec.md`

## Summary

Build a cross-platform (macOS/Windows) dual-panel file manager application using Python and Tkinter. The application enables users to browse local filesystems and Google Cloud Storage buckets side-by-side, with support for copy, move, and delete operations between any combination of local and cloud storage.

**Key features**:
- Browser-based OAuth2 authentication for GCP (no command-line setup required)
- Two-panel Total Commander-style interface
- Seamless file transfer between local and GCS
- Secure credential storage with automatic token refresh

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: tkinter/ttk (GUI), google-cloud-storage (GCS API), google-auth-oauthlib (OAuth2 browser flow), pathlib (file paths)
**Storage**: Local filesystem + GCS buckets; JSON configuration for settings/projects; Encrypted token storage for OAuth2 credentials
**Testing**: pytest (unit/integration), pytest-mock (mocking GCS/OAuth)
**Target Platform**: macOS (10.15+), Windows (10+) - standalone executables
**Project Type**: Single desktop application
**Performance Goals**: <3s cold start, <100ms UI response, <5s bucket listing (1000 objects), <60s auth flow
**Constraints**: <200MB memory, no Python installation required for end users, secure credential storage
**Scale/Scope**: Single user, typical usage: 10-50 GCS buckets, 10,000+ files per directory

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Cross-Platform Parity ✅

| Requirement | Compliance |
|-------------|------------|
| Features work identically on macOS and Windows | ✅ Using Python/Tkinter - inherently cross-platform |
| Platform-specific code isolated | ✅ Will use `src/platform/` for OS-specific code (paths, shortcuts, browser launch) |
| Shared logic in platform-agnostic modules | ✅ Core services in `src/services/`, UI in `src/ui/` |
| File paths use `pathlib.Path` | ✅ Required by design |
| Configuration uses platform-appropriate locations | ✅ Will detect OS and use `~/.config/morton-com` or `%APPDATA%\morton-com` |

**Auth Note**: Browser-based OAuth2 works identically on both platforms via `webbrowser.open()`.

### II. Native Look & Feel ✅

| Requirement | Compliance |
|-------------|------------|
| Use `tkinter.ttk` themed widgets | ✅ All widgets will use ttk |
| Honor system color schemes | ✅ Will detect and apply light/dark mode |
| Platform-specific menu placement | ✅ Will handle via platform detection |
| Platform-specific keyboard shortcuts | ✅ Cmd on macOS, Ctrl on Windows |
| Platform-specific dialog button ordering | ✅ Will apply per-platform ordering |

### III. Performance ✅

| Requirement | Compliance |
|-------------|------------|
| Cold startup <3s | ✅ Target: <3s (matches SC-010) |
| UI never blocks >100ms | ✅ All GCS/file/auth ops in background threads |
| Memory <200MB | ✅ Target: <200MB typical usage |
| Progress feedback for long operations | ✅ FR-009 requires progress indicators |
| Lazy loading for heavy resources | ✅ Directory listings loaded on-demand |

### IV. Testability ✅

| Requirement | Compliance |
|-------------|------------|
| Business logic separated from UI (MVC/MVP) | ✅ Services layer handles all logic |
| Services injectable for mocking | ✅ Dependency injection for GCS client and OAuth flow |
| UI tests without manual interaction | ✅ Will use tkinter test utilities |
| 80% code coverage for non-UI | ✅ Target in CI pipeline |
| Tests pass on both platforms | ✅ GitHub Actions with macOS + Windows |

**Gate Status**: PASSED - No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/001-dual-panel-filemanager/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal service interfaces)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── main.py                    # Application entry point
├── config.py                  # Configuration loading/saving
├── models/
│   ├── __init__.py
│   ├── file_item.py           # Local file/folder representation
│   ├── gcs_object.py          # GCS blob representation
│   ├── gcs_bucket.py          # GCS bucket representation
│   ├── transfer_operation.py  # Transfer job tracking
│   ├── panel_state.py         # Panel current state
│   └── user_session.py        # OAuth2 user session
├── services/
│   ├── __init__.py
│   ├── local_filesystem.py    # Local file operations
│   ├── gcs_client.py          # GCS operations wrapper
│   ├── transfer_manager.py    # Copy/move orchestration
│   ├── config_manager.py      # Settings persistence
│   └── auth_service.py        # OAuth2 browser flow, token management
├── ui/
│   ├── __init__.py
│   ├── app.py                 # Main application window
│   ├── panel.py               # File browser panel widget
│   ├── toolbar.py             # Action buttons
│   ├── account_menu.py        # User account display, sign-out
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── properties.py      # File properties dialog
│   │   ├── conflict.py        # Overwrite/skip/rename dialog
│   │   ├── progress.py        # Transfer progress dialog
│   │   ├── settings.py        # Settings dialog
│   │   └── auth.py            # Sign-in prompt dialog
│   └── widgets/
│       ├── __init__.py
│       └── file_list.py       # Treeview-based file listing
└── platform/
    ├── __init__.py
    ├── base.py                # Platform abstraction interface
    ├── macos.py               # macOS-specific implementations
    └── windows.py             # Windows-specific implementations

tests/
├── __init__.py
├── conftest.py                # Shared fixtures
├── unit/
│   ├── __init__.py
│   ├── test_local_filesystem.py
│   ├── test_gcs_client.py
│   ├── test_transfer_manager.py
│   ├── test_auth_service.py   # OAuth flow tests (mocked)
│   └── test_models.py
├── integration/
│   ├── __init__.py
│   ├── test_local_to_local.py
│   ├── test_local_to_gcs.py
│   └── test_gcs_to_local.py
└── fixtures/
    └── sample_files/          # Test data

config/
└── projects.json.example      # Example GCP projects configuration
```

**Structure Decision**: Single project structure selected. Desktop application with clear separation:
- `models/` - Data classes representing domain entities (including UserSession)
- `services/` - Business logic, file operations, GCS integration, OAuth2 authentication
- `ui/` - Tkinter widgets and dialogs (including auth dialogs)
- `platform/` - OS-specific code isolation per Constitution I

## Complexity Tracking

> No violations - all Constitution requirements met with standard patterns.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *None* | - | - |
