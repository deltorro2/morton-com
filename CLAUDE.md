# morton-com Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-04

## Active Technologies
- Python 3.10+ + kinter/ttk (GUI), google-cloud-storage (GCS API), google-auth-oauthlib (OAuth2 browser flow), pathlib (file paths) (001-dual-panel-filemanager)
- Local filesystem + GCS buckets; JSON configuration for settings/projects; Encrypted token storage for OAuth2 credentials (001-dual-panel-filemanager)
- Python 3.10+ (Python 3.13 in current dev environment) + kinter/ttk (GUI), google-cloud-storage (GCS API) (002-copy-move-dialog)
- Python 3.10+ (currently running on 3.13) + kinter/ttk (GUI), google-cloud-storage (GCS API), pathlib (file paths) (003-new-folder-dialog)

- Python 3.10+ + kinter/ttk (GUI), google-cloud-storage (GCS API), pathlib (file paths) (001-dual-panel-filemanager)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.10+: Follow standard conventions

## Recent Changes
- 003-new-folder-dialog: Added Python 3.10+ (currently running on 3.13) + kinter/ttk (GUI), google-cloud-storage (GCS API), pathlib (file paths)
- 002-copy-move-dialog: Added Python 3.10+ (Python 3.13 in current dev environment) + kinter/ttk (GUI), google-cloud-storage (GCS API)
- 001-dual-panel-filemanager: Added Python 3.10+ + kinter/ttk (GUI), google-cloud-storage (GCS API), google-auth-oauthlib (OAuth2 browser flow), pathlib (file paths)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
