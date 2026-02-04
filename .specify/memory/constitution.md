<!--
SYNC IMPACT REPORT
==================
Version change: N/A → 1.0.0 (initial ratification)
Modified principles: N/A (initial creation)
Added sections:
  - Core Principles (4 principles)
  - Technical Standards (Python & Tkinter requirements)
  - Development Workflow (testing, packaging, CI)
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ (compatible - no changes needed)
  - .specify/templates/spec-template.md ✅ (compatible - no changes needed)
  - .specify/templates/tasks-template.md ✅ (compatible - no changes needed)
Follow-up TODOs: None
==================
-->

# morton-com Constitution

## Core Principles

### I. Cross-Platform Parity

All features MUST work identically on macOS and Windows. No platform-specific functionality
may be shipped unless a documented equivalent exists for the other platform.

- Every feature MUST be tested on both macOS and Windows before merge
- Platform-specific code MUST be isolated in dedicated modules (e.g., `src/platform/macos/`, `src/platform/windows/`)
- Shared logic MUST reside in platform-agnostic modules
- File paths MUST use `pathlib.Path` - never hardcoded separators
- Configuration MUST use platform-appropriate locations (`~/.config` on macOS, `%APPDATA%` on Windows)

**Rationale**: Users expect the same experience regardless of their operating system. Divergent
behavior creates support burden and erodes trust.

### II. Native Look & Feel

The application MUST respect each platform's visual conventions and system preferences while
maintaining functional parity.

- Use `tkinter.ttk` themed widgets as the default - avoid classic `tk` widgets
- Honor system color schemes (light/dark mode) via OS detection
- Follow platform conventions for:
  - Menu bar placement (top of window on Windows, system menu bar on macOS)
  - Dialog button ordering (OK/Cancel vs Cancel/OK)
  - Keyboard shortcuts (Cmd on macOS, Ctrl on Windows)
- Window chrome and controls MUST feel native to each platform

**Rationale**: Desktop users have strong expectations about how applications should look and
behave on their chosen platform. Violating these conventions creates friction.

### III. Performance

The application MUST start quickly and remain responsive under normal usage conditions.

- Cold startup MUST complete in under 3 seconds on reference hardware
- UI MUST never block for more than 100ms - use background threads for long operations
- Memory usage MUST stay under 200MB for typical workloads
- All long-running operations MUST provide progress feedback to the user
- Lazy loading MUST be used for heavy resources (images, data files)

**Rationale**: Desktop applications compete with native apps that users expect to be fast.
Sluggish performance drives users to alternatives.

### IV. Testability

All code MUST be structured to enable automated testing, including UI components.

- Business logic MUST be separated from UI code (MVC/MVP pattern)
- All services and data access MUST be injectable for mocking
- UI tests MUST be possible without manual interaction
- Minimum 80% code coverage for non-UI modules
- Integration tests MUST verify cross-platform behavior
- Tests MUST pass on both macOS and Windows CI runners

**Rationale**: A cross-platform application has double the surface area for bugs. Without
comprehensive testing, regressions will ship.

## Technical Standards

### Python Requirements

- **Minimum Version**: Python 3.10+
- **Type Hints**: MUST use type annotations on all public functions and methods
- **Style**: MUST follow PEP 8; enforce via `ruff` or `black`
- **Imports**: MUST use absolute imports; no relative imports beyond current package

### Tkinter Guidelines

- MUST use `tkinter.ttk` for all standard widgets
- Custom widgets MUST extend `ttk.Frame` or appropriate base class
- MUST NOT use `time.sleep()` in UI code - use `after()` for scheduling
- MUST use `threading` or `concurrent.futures` for background work
- MUST communicate with UI thread via thread-safe queues or `after()` callbacks

### Packaging & Distribution

- MUST use `pyproject.toml` for project metadata (PEP 621)
- MUST support packaging via PyInstaller for standalone executables
- macOS builds MUST produce `.app` bundles or `.dmg` installers
- Windows builds MUST produce `.exe` installers (via NSIS or similar)
- MUST NOT require users to install Python separately

## Development Workflow

### Testing Gates

All pull requests MUST pass:

1. Unit tests (`pytest tests/unit/`)
2. Integration tests (`pytest tests/integration/`)
3. Linting (`ruff check .`)
4. Type checking (`mypy src/`)
5. Cross-platform CI (both macOS and Windows runners)

### Code Review Requirements

- All changes MUST be reviewed before merge
- Reviewer MUST verify cross-platform considerations are addressed
- UI changes MUST include screenshots from both platforms

### Release Process

1. Version bump following semantic versioning
2. Changelog update with user-facing changes
3. Tag release in git
4. Build executables for both platforms
5. Test installers on clean systems before publishing

## Governance

This constitution is the authoritative source for project standards. All code, reviews, and
architectural decisions MUST comply with these principles.

### Amendment Process

1. Propose amendment via pull request to this file
2. Document rationale and impact assessment
3. Obtain approval from project maintainer(s)
4. Update version according to semantic versioning:
   - MAJOR: Principle removal or incompatible redefinition
   - MINOR: New principle or significant expansion
   - PATCH: Clarification or wording improvements
5. Update dependent templates if affected

### Compliance

- All PRs MUST pass Constitution Check in the implementation plan
- Violations MUST be documented and justified in Complexity Tracking
- Runtime guidance lives in project documentation (README, docs/)

**Version**: 1.0.0 | **Ratified**: 2026-02-04 | **Last Amended**: 2026-02-04
