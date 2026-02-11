# Quickstart: Dual-Panel File Manager

**Feature**: 001-dual-panel-filemanager
**Date**: 2026-02-04
**Updated**: 2026-02-04 (added browser-based authentication)

## Prerequisites

1. **Python 3.10+** installed
2. **Google account** with access to at least one GCP project
3. **Web browser** for OAuth2 authentication

## Installation (Development)

```bash
# Clone repository
git clone <repository-url>
cd morton-com

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"
```

## Configuration

1. Create configuration directory:
   ```bash
   # macOS
   mkdir -p ~/.config/morton-com

   # Windows (PowerShell)
   mkdir -Force "$env:APPDATA\morton-com"
   ```

2. Create `projects.json` with your GCP project IDs:
   ```json
   {
     "projects": [
       {
         "project_id": "my-gcp-project",
         "display_name": "My Project",
         "default": true
       },
       {
         "project_id": "another-project",
         "display_name": "Another Project"
       }
     ]
   }
   ```

3. (Optional) Create `settings.json` for preferences:
   ```json
   {
     "max_concurrent_transfers": 3,
     "show_hidden_files": false,
     "confirm_delete": true
   }
   ```

**Note**: You do NOT need to manually configure GCP credentials. The application will guide you through browser-based sign-in.

## Running the Application

```bash
# From project root with virtual environment activated
python -m src.main
```

## First-Time Setup: Signing In

1. **Launch the application** - You'll see the two-panel interface with local files
2. **Switch to GCS** - Click the panel dropdown and select "GCS"
3. **Sign in prompt appears** - Click "Sign in with Google"
4. **Browser opens** - Your default browser opens to Google's sign-in page
5. **Authenticate** - Sign in with your Google account
6. **Grant permissions** - Allow access to Google Cloud Storage
7. **Success!** - Browser shows success message; application now shows your GCS buckets

Your credentials are securely stored and will be used automatically next time.

## Basic Usage

### Navigation

| Action | Keyboard | Mouse |
|--------|----------|-------|
| Enter folder | Enter | Double-click |
| Go to parent | Backspace | Click ".." |
| Switch panels | Tab | Click panel |
| Select file | Space | Click |
| Select multiple | Shift+Click | Shift+Click range |
| Select all | Cmd/Ctrl+A | - |
| Refresh | Cmd/Ctrl+R or F5 | - |

### File Operations

| Action | Keyboard | Description |
|--------|----------|-------------|
| Copy | Cmd/Ctrl+C then Cmd/Ctrl+V | Copy selected to other panel |
| Move | Cmd/Ctrl+X then Cmd/Ctrl+V | Move selected to other panel |
| Delete | Cmd/Ctrl+Delete or Delete | Delete selected (with confirmation) |
| Properties | Cmd/Ctrl+I or Alt+Enter | View file details |

### Panel Modes

Each panel can display:
- **Local**: Your computer's file system
- **GCS Project**: List of buckets in a GCP project
- **GCS Bucket**: Contents of a specific bucket

Switch modes using the dropdown at the top of each panel.

### Account Management

- **View account**: Your Google email appears in the top-right when signed in
- **Sign out**: Click your email → "Sign Out" to clear credentials
- **Switch accounts**: Sign out, then sign in with a different Google account

## Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests (requires GCP credentials)
pytest tests/integration/

# With coverage
pytest --cov=src --cov-report=html
```

## Building Standalone Executable

```bash
# macOS
pyinstaller --onefile --windowed --name="Morton" src/main.py

# Windows
pyinstaller --onefile --windowed --name="Morton" --icon=assets/icon.ico src/main.py
```

Output will be in `dist/` directory.

## Troubleshooting

### "Sign-in required" when accessing GCS

Click the "Sign in with Google" button and complete browser authentication.

### Browser doesn't open for sign-in

1. Check your default browser is set correctly in system settings
2. Try copying the URL from the console and pasting in browser manually

### "Permission denied" after sign-in

Your Google account may not have access to the GCP project. Ensure:
- You're signed in with the correct Google account
- Your account has `roles/storage.objectViewer` or `roles/storage.objectAdmin` on the bucket

### "Token refresh failed"

Your session may have expired or been revoked. Sign out and sign in again.

### Application won't start

Check Python version:
```bash
python --version  # Should be 3.10+
```

Verify tkinter is installed:
```bash
python -c "import tkinter; print('OK')"
```

### Slow bucket listing

For buckets with >10,000 objects, initial listing may take longer. The application loads in pages of 1,000 objects.

## Security Notes

- **Credentials are encrypted** using your system's secure storage (macOS Keychain / Windows Credential Manager)
- **Tokens are never stored in plain text**
- **Sign out clears all stored credentials**
- The application only requests minimum required permissions (GCS read/write)

