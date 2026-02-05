# Research: Dual-Panel File Manager

**Feature**: 001-dual-panel-filemanager
**Date**: 2026-02-04
**Updated**: 2026-02-04 (added browser-based authentication)

## Technology Decisions

### 1. GUI Framework: Tkinter with ttk

**Decision**: Use `tkinter.ttk` as the GUI framework.

**Rationale**:
- Bundled with Python - no additional dependencies for core GUI
- Cross-platform by design (macOS, Windows, Linux)
- ttk provides native-looking widgets on each platform
- Sufficient widget set for file manager (Treeview, buttons, dialogs)
- Constitution mandates ttk over classic tk widgets

**Alternatives Considered**:
- **PyQt/PySide**: More widgets and polish, but GPL/LGPL licensing complexity and larger bundle size
- **wxPython**: Good native look, but additional dependency and less documentation
- **Kivy**: Touch-oriented, not ideal for traditional desktop file manager UX

### 2. GCS Client Library: google-cloud-storage

**Decision**: Use official `google-cloud-storage` Python library.

**Rationale**:
- Official Google-maintained library
- Handles authentication via google-auth library
- Supports resumable uploads for large files (required for multi-GB transfers)
- Provides progress callbacks for transfer monitoring
- Well-documented with async-compatible patterns

**Alternatives Considered**:
- **boto3 with S3-compatible endpoint**: Possible but loses GCS-specific features (storage classes, generations)
- **Raw REST API via requests**: More control but significant implementation effort
- **gcloud CLI subprocess**: Simpler but poor progress tracking and error handling

### 3. Authentication: Browser-Based OAuth2 Flow

**Decision**: Use `google-auth-oauthlib` for browser-based OAuth2 authentication with local redirect.

**Rationale**:
- Best user experience for desktop applications - no command-line required
- Standard Google OAuth2 flow using user's default browser
- `InstalledAppFlow` handles local HTTP server for redirect automatically
- Refresh tokens enable persistent sessions without re-authentication
- Secure - credentials never stored in plain text

**Flow**:
1. User clicks "Sign in with Google" in the application
2. Application starts local HTTP server on random port (e.g., `localhost:8085`)
3. Browser opens to Google OAuth2 consent page
4. User authenticates and grants permissions
5. Google redirects to `localhost:8085/callback` with authorization code
6. Application exchanges code for access + refresh tokens
7. Tokens stored securely; user email displayed in app

**Alternatives Considered**:
- **Application Default Credentials (ADC)**: Requires `gcloud auth` CLI - poor UX for non-developers
- **Service Account**: Requires manual key file setup - not suitable for end-user app
- **Device Flow**: Better for devices without browsers, but we have browser available
- **Manual Token Entry**: Terrible UX, error-prone

### 4. Token Storage: Encrypted Local File

**Decision**: Store OAuth2 tokens in an encrypted JSON file using platform keyring for encryption key.

**Rationale**:
- Tokens must persist between sessions (FR-012a)
- Plain text storage is a security risk
- Platform keyrings (macOS Keychain, Windows Credential Manager) provide secure key storage
- `keyring` library provides cross-platform abstraction
- Fallback to file-based encryption if keyring unavailable

**Storage Location**:
- macOS: `~/.config/morton-com/credentials.enc`
- Windows: `%APPDATA%\morton-com\credentials.enc`

**Encryption Approach**:
- Generate random encryption key on first run
- Store key in platform keyring (service: "morton-com", username: "oauth-key")
- Encrypt token JSON with Fernet (symmetric encryption)
- On load: retrieve key from keyring, decrypt tokens

**Alternatives Considered**:
- **Plain text JSON**: Insecure - rejected
- **Keyring direct storage**: Some keyrings have size limits; tokens can be large
- **OS-specific encrypted storage**: More complex, less portable

### 5. Token Refresh Strategy

**Decision**: Proactive refresh with fallback to re-authentication.

**Rationale**:
- Access tokens expire (typically 1 hour)
- Refresh tokens enable automatic renewal without user interaction
- Proactive refresh prevents failed requests

**Implementation**:
1. On startup: Load stored credentials, check expiry
2. If access token expires within 5 minutes: Refresh proactively
3. On GCS request failure (401): Attempt refresh
4. If refresh fails (refresh token revoked): Prompt user to sign in again
5. Never store expired credentials without valid refresh token

### 6. Threading Model: concurrent.futures.ThreadPoolExecutor

**Decision**: Use `ThreadPoolExecutor` for background operations including OAuth flow.

**Rationale**:
- Part of Python standard library
- Clean interface for submitting tasks and getting results
- Configurable pool size matches user setting for concurrent transfers (FR-011)
- Future objects allow cancellation tracking
- Constitution requires background threads for long operations

**Auth-Specific Threading**:
- OAuth browser flow runs in separate thread to avoid blocking UI
- Local HTTP server for callback runs in thread
- Token refresh runs in background when triggered

**Alternatives Considered**:
- **asyncio**: Better for I/O-bound work but Tkinter integration is complex
- **multiprocessing**: Overkill for I/O-bound file transfers; complicates UI communication
- **Raw threading.Thread**: Works but less convenient than executor pattern

### 7. Configuration Storage: JSON Files

**Decision**: Store configuration in JSON files in platform-appropriate locations.

**Rationale**:
- Human-readable and editable
- No additional dependencies
- Standard format for GCP project lists
- Easy to version control example configurations
- Platform paths per Constitution I: `~/.config/morton-com/` (macOS) or `%APPDATA%\morton-com\` (Windows)

**Configuration Files**:
- `settings.json`: User preferences (concurrent transfers, UI state)
- `projects.json`: GCP project IDs list
- `credentials.enc`: Encrypted OAuth2 tokens (see Token Storage above)

**Alternatives Considered**:
- **SQLite**: Overkill for simple key-value settings
- **YAML**: Requires PyYAML dependency
- **INI files**: Less structured, poor fit for nested data
- **Environment variables**: Not persistent, poor UX for desktop app

### 8. File Listing Strategy: Virtual/Lazy Loading with Treeview

**Decision**: Use ttk.Treeview with lazy loading for large directories.

**Rationale**:
- Treeview is the standard ttk widget for hierarchical/tabular data
- Supports columns (name, size, date) natively
- Can handle 10,000+ items when properly configured
- Lazy loading (load children on expand) prevents memory issues
- Sorting and selection built-in

**Implementation Details**:
- Initial load: First 1000 items with "Load more..." placeholder
- Pagination for directories >1000 items
- Sorting performed on currently loaded items
- Virtual scrolling via Treeview's built-in optimization

**Alternatives Considered**:
- **Listbox**: Too simple, no columns
- **Custom canvas widget**: Maximum flexibility but significant implementation effort
- **Third-party data grid**: Adds dependency, may not integrate well with ttk theme

### 9. Large File Transfer Handling

**Decision**: Use GCS resumable uploads/downloads with chunked progress.

**Rationale**:
- GCS library supports resumable uploads natively
- Required for files >5MB per GCS best practices
- Enables progress tracking at chunk level
- Allows resume after network interruption
- Supports cancellation between chunks

**Implementation**:
- Chunk size: 8MB (GCS default, good balance)
- Progress callback updates UI every chunk
- Store upload URI for potential resume
- Local→Local: Use `shutil.copy2` with callback via custom copy function

**Alternatives Considered**:
- **Simple upload/download**: Fails for large files, no progress
- **Streaming only**: No resume capability

### 10. Platform Abstraction Pattern

**Decision**: Strategy pattern with platform detector.

**Rationale**:
- Clean separation per Constitution I
- Single detection point at startup
- Each platform module implements same interface
- Easy to add Linux support later

**Interface Methods**:
- `get_config_dir() -> Path`
- `get_modifier_key() -> str` (Cmd/Ctrl)
- `get_dialog_button_order() -> tuple`
- `detect_dark_mode() -> bool`
- `get_default_font() -> str`
- `open_browser(url: str) -> None` (for OAuth flow)

### 11. Keyboard Shortcuts Implementation

**Decision**: Centralized shortcut registry with platform-aware bindings.

**Rationale**:
- FR-019 requires keyboard shortcuts for common operations
- Platform differences (Cmd vs Ctrl) handled centrally
- Easy to display in menus and help
- Allows future customization

**Default Shortcuts**:
| Action | macOS | Windows |
|--------|-------|---------|
| Copy | Cmd+C | Ctrl+C |
| Move | Cmd+X, then Cmd+V | Ctrl+X, then Ctrl+V |
| Delete | Cmd+Delete | Delete |
| Refresh | Cmd+R | F5 |
| Select All | Cmd+A | Ctrl+A |
| Properties | Cmd+I | Alt+Enter |
| Switch Panel | Tab | Tab |

### 12. Error Handling Strategy

**Decision**: Typed exceptions with user-friendly messages.

**Rationale**:
- FR-018 requires clear error messages with suggested actions
- Different error types need different handling
- GCS errors should not expose raw API messages
- Auth errors need specific handling (re-authentication prompts)

**Exception Hierarchy**:
```
MortonError (base)
├── AuthenticationError - GCP credentials issue (sign-in required, token expired)
├── PermissionError - Bucket/file access denied
├── NetworkError - Connection/timeout issues
├── TransferError - Copy/move/delete failures
├── ConfigurationError - Invalid settings
└── FileSystemError - Local file issues
```

Each exception includes:
- `user_message`: Display to user
- `suggested_action`: What they can do to fix it
- `technical_detail`: For logging

## Dependencies Summary

### Runtime Dependencies

```
google-cloud-storage>=2.14.0    # GCS API client
google-auth>=2.28.0             # Authentication base
google-auth-oauthlib>=1.2.0     # OAuth2 browser flow
keyring>=25.0.0                 # Secure credential storage
cryptography>=42.0.0            # Token encryption (Fernet)
```

### Development Dependencies

```
pytest>=8.0.0                   # Testing framework
pytest-mock>=3.12.0             # Mocking support
pytest-cov>=4.1.0               # Coverage reporting
mypy>=1.8.0                     # Type checking
ruff>=0.2.0                     # Linting and formatting
pyinstaller>=6.3.0              # Executable packaging
```

### Standard Library (no install)

```
tkinter                         # GUI (bundled with Python)
tkinter.ttk                     # Themed widgets
pathlib                         # Cross-platform paths
concurrent.futures              # Thread pool
json                            # Configuration files
shutil                          # Local file operations
os                              # OS detection
threading                       # Thread synchronization
queue                           # Thread-safe communication
dataclasses                     # Model definitions
typing                          # Type hints
datetime                        # Timestamps
enum                            # Status enumerations
webbrowser                      # Open OAuth URL in browser
http.server                     # Local callback server for OAuth
urllib.parse                    # Parse OAuth callback URL
secrets                         # Generate secure state parameter
```

## OAuth2 Implementation Details

### Required Scopes

```python
SCOPES = [
    'https://www.googleapis.com/auth/devstorage.read_write',  # GCS access
    'https://www.googleapis.com/auth/userinfo.email',         # User email for display
]
```

### OAuth Client Setup

The application requires a Google Cloud OAuth2 client ID configured for "Desktop app" type:
1. Create project in Google Cloud Console
2. Enable Cloud Storage API
3. Configure OAuth consent screen
4. Create OAuth client ID (Desktop app type)
5. Embed client_id and client_secret in application (acceptable for desktop apps per Google guidelines)

### Callback Handling

```
1. Start local HTTP server on localhost:PORT
2. Open browser to: https://accounts.google.com/o/oauth2/v2/auth?
     client_id=...
     redirect_uri=http://localhost:PORT/callback
     response_type=code
     scope=...
     state=RANDOM_STATE
     access_type=offline     # Request refresh token
     prompt=consent          # Always show consent for refresh token
3. User authenticates in browser
4. Browser redirects to localhost:PORT/callback?code=...&state=...
5. Verify state matches
6. Exchange code for tokens via POST to https://oauth2.googleapis.com/token
7. Store tokens securely
8. Show success page in browser, close after 3 seconds
```

## Open Questions Resolved

All technical decisions are resolved. No NEEDS CLARIFICATION items remain.

## References

- [google-cloud-storage Python documentation](https://cloud.google.com/python/docs/reference/storage/latest)
- [google-auth-oauthlib documentation](https://google-auth-oauthlib.readthedocs.io/)
- [Tkinter ttk documentation](https://docs.python.org/3/library/tkinter.ttk.html)
- [GCS resumable uploads](https://cloud.google.com/storage/docs/resumable-uploads)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Python keyring documentation](https://keyring.readthedocs.io/)
