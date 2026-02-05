# Data Model: Dual-Panel File Manager

**Feature**: 001-dual-panel-filemanager
**Date**: 2026-02-04
**Updated**: 2026-02-04 (added UserSession entity for browser-based auth)

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   Application   │       │  Configuration  │       │   UserSession   │
│                 │       │                 │       │                 │
│ - left_panel    │       │ - projects[]    │       │ - email         │
│ - right_panel   │       │ - settings      │       │ - access_token  │
│ - user_session  │───────┤                 │       │ - refresh_token │
└────────┬────────┘       └─────────────────┘       └─────────────────┘
         │                                                   │
         │ contains (2)                                      │
         ▼                                                   │
┌─────────────────┐                                          │
│     Panel       │                                          │
│                 │───────┐                                  │
│ - source_type   │       │                                  │
│ - location      │       │                                  │
│ - items[]       │       │                                  │
│ - selected[]    │       │                                  │
└────────┬────────┘       │                                  │
         │                │ source_type determines           │
         │ displays       │                                  │
         ▼                ▼                                  │
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│   FileItem      │  │   GCSObject     │  │   GCSBucket     ││
│   (local)       │  │   (cloud file)  │  │   (cloud dir)   ││
└─────────────────┘  └─────────────────┘  └─────────────────┘│
         │                   │                    │          │
         └───────────────────┴────────────────────┘          │
                             │                               │
                    ┌────────┴────────┐                      │
                    │ TransferOperation│                     │
                    │                 │◄─────────────────────┘
                    │ - source_items[]│    requires auth
                    │ - destination   │
                    │ - progress      │
                    └─────────────────┘
```

## Entities

### UserSession

Represents the authenticated user's OAuth2 session.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| email | str | User's Google account email | Valid email format |
| access_token | str | OAuth2 access token | Non-empty when authenticated |
| refresh_token | str | OAuth2 refresh token | Non-empty; used to obtain new access tokens |
| token_expiry | datetime | When access token expires | UTC; typically 1 hour from issue |
| scopes | list[str] | Granted OAuth2 scopes | Must include required GCS scopes |
| signed_in_at | datetime | When user signed in | UTC |

**Derived Properties**:
- `is_authenticated`: True if access_token is valid or refresh_token can obtain one
- `is_expired`: True if token_expiry < now
- `needs_refresh`: True if token_expiry < now + 5 minutes
- `display_name`: Email prefix (before @) for compact display

**State Transitions**:
```
SIGNED_OUT ──[sign_in]──▶ SIGNING_IN ──[success]──▶ SIGNED_IN
                              │                         │
                              └──[error]──▶ SIGNED_OUT  │
                                                        │
SIGNED_IN ──[token_expired]──▶ REFRESHING ──[success]──▶ SIGNED_IN
                                    │
                                    └──[error]──▶ SIGNED_OUT

SIGNED_IN ──[sign_out]──▶ SIGNED_OUT
```

### FileItem

Represents a file or directory on the local filesystem.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| name | str | File or folder name | Non-empty |
| path | Path | Absolute path | Valid filesystem path |
| size | int | Size in bytes | ≥0; 0 for directories |
| modified_date | datetime | Last modification time | UTC |
| created_date | datetime | Creation time | UTC; may equal modified on some OS |
| is_directory | bool | True if folder | - |
| permissions | str | Permission string | e.g., "rwxr-xr-x" |
| is_hidden | bool | Starts with dot or hidden attr | Platform-dependent |

**Derived Properties**:
- `display_size`: Human-readable size (e.g., "1.5 MB")
- `extension`: File extension or empty string
- `icon_type`: folder/file/image/document/etc. for UI

**State Transitions**: None (immutable snapshot)

### GCSObject

Represents a blob (file) in Google Cloud Storage.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| name | str | Object name (full path in bucket) | Non-empty |
| bucket_name | str | Parent bucket name | Valid bucket name |
| size | int | Size in bytes | ≥0 |
| content_type | str | MIME type | e.g., "application/pdf" |
| storage_class | str | GCS storage class | STANDARD/NEARLINE/COLDLINE/ARCHIVE |
| created_time | datetime | Object creation time | UTC |
| updated_time | datetime | Last update time | UTC |
| generation | int | Object generation number | Unique version identifier |
| metadata | dict[str, str] | Custom metadata | Key-value pairs |
| md5_hash | str | MD5 hash (base64) | For integrity verification |

**Derived Properties**:
- `display_name`: Last segment of name (pseudo-filename)
- `prefix`: Parent "folder" prefix
- `display_size`: Human-readable size
- `is_prefix`: True if this represents a folder prefix (size=0, ends with /)

**State Transitions**: None (immutable snapshot)

### GCSBucket

Represents a Google Cloud Storage bucket.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| name | str | Bucket name | Globally unique |
| project_id | str | GCP project ID | From configuration |
| location | str | Bucket location | e.g., "US-CENTRAL1" |
| storage_class | str | Default storage class | STANDARD/NEARLINE/COLDLINE/ARCHIVE |
| created_time | datetime | Bucket creation time | UTC |
| versioning_enabled | bool | Object versioning on | - |

**Derived Properties**:
- `display_location`: Human-friendly location name

**State Transitions**: None (immutable snapshot)

### Panel

Represents the state of one file browser panel.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | str | Panel identifier | "left" or "right" |
| source_type | SourceType | What the panel shows | LOCAL/GCS_BUCKET/GCS_PROJECT |
| location | str | Current path/prefix | Valid for source_type |
| project_id | str | Current GCP project (if GCS) | Optional |
| bucket_name | str | Current bucket (if GCS bucket) | Optional |
| items | list[FileItem\|GCSObject\|GCSBucket] | Current listing | May be empty |
| selected_indices | set[int] | Selected item indices | Valid indices into items |
| sort_column | str | Current sort field | name/size/date |
| sort_ascending | bool | Sort direction | - |
| loading | bool | Currently fetching items | - |
| error | str | Last error message | Optional |

**State Transitions**:
```
IDLE ──[navigate]──▶ LOADING ──[success]──▶ IDLE
                         │
                         └──[error]──▶ ERROR ──[retry/navigate]──▶ LOADING
```

**GCS Panel Requires Authentication**:
- When `source_type` is GCS_PROJECT or GCS_BUCKET, operations require `UserSession.is_authenticated == True`
- If not authenticated, panel shows sign-in prompt instead of file listing

### TransferOperation

Represents an in-progress file transfer (copy or move).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | str | Unique operation ID | UUID |
| operation_type | OperationType | COPY or MOVE | - |
| source_items | list[FileItem\|GCSObject] | Items being transferred | Non-empty |
| destination | TransferDestination | Target location | Valid location |
| status | TransferStatus | Current status | PENDING/RUNNING/PAUSED/COMPLETED/FAILED/CANCELLED |
| progress_percent | float | Overall completion | 0.0-100.0 |
| current_file | str | File currently transferring | Optional |
| current_file_progress | float | Current file progress | 0.0-100.0 |
| bytes_transferred | int | Total bytes moved | ≥0 |
| total_bytes | int | Total bytes to transfer | ≥0 |
| started_at | datetime | Operation start time | UTC |
| completed_at | datetime | Operation end time | UTC; Optional |
| error_message | str | Error details if failed | Optional |
| files_completed | int | Number of files done | ≥0 |
| files_total | int | Total files to transfer | ≥0 |

**State Transitions**:
```
PENDING ──[start]──▶ RUNNING ──[complete]──▶ COMPLETED
                        │
                        ├──[pause]──▶ PAUSED ──[resume]──▶ RUNNING
                        │
                        ├──[cancel]──▶ CANCELLED
                        │
                        └──[error]──▶ FAILED
```

**Authentication Requirement**:
- Operations involving GCS destinations require valid `UserSession`
- If token expires mid-transfer, attempt refresh; if refresh fails, pause operation

### TransferDestination

Value object for transfer target location.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| type | SourceType | LOCAL or GCS_BUCKET | - |
| path | str | Local path or GCS prefix | Valid for type |
| bucket_name | str | Target bucket (if GCS) | Optional |
| project_id | str | Target project (if GCS) | Optional |

### Configuration

Application settings and GCP project list.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| projects | list[ProjectConfig] | Configured GCP projects | May be empty |
| max_concurrent_transfers | int | Parallel transfer limit | 1-10, default 3 |
| show_hidden_files | bool | Display hidden files | Default: false |
| confirm_delete | bool | Require delete confirmation | Default: true |
| window_state | WindowState | Last window size/position | Optional |

### ProjectConfig

GCP project configuration entry.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| project_id | str | GCP project ID | Non-empty |
| display_name | str | User-friendly name | Optional; defaults to project_id |
| default | bool | Open by default | Only one can be true |

## Enumerations

### SourceType

```python
class SourceType(Enum):
    LOCAL = "local"              # Local filesystem
    GCS_PROJECT = "gcs_project"  # Showing bucket list for a project
    GCS_BUCKET = "gcs_bucket"    # Inside a specific bucket
```

### OperationType

```python
class OperationType(Enum):
    COPY = "copy"
    MOVE = "move"
```

### TransferStatus

```python
class TransferStatus(Enum):
    PENDING = "pending"       # Queued, not started
    RUNNING = "running"       # Actively transferring
    PAUSED = "paused"         # User paused
    COMPLETED = "completed"   # Successfully finished
    FAILED = "failed"         # Error occurred
    CANCELLED = "cancelled"   # User cancelled
```

### ConflictResolution

```python
class ConflictResolution(Enum):
    OVERWRITE = "overwrite"   # Replace existing file
    SKIP = "skip"             # Skip this file
    RENAME = "rename"         # Add suffix (e.g., "file (1).txt")
    ASK = "ask"               # Prompt for each conflict
```

### AuthState

```python
class AuthState(Enum):
    SIGNED_OUT = "signed_out"     # No credentials
    SIGNING_IN = "signing_in"     # Browser flow in progress
    SIGNED_IN = "signed_in"       # Valid credentials
    REFRESHING = "refreshing"     # Token refresh in progress
```

## Validation Rules

### UserSession
- `email` must be valid email format
- `access_token` must not be empty when state is SIGNED_IN
- `refresh_token` must not be empty (required for token refresh)
- `scopes` must include `devstorage.read_write`
- `token_expiry` must be in the future when freshly authenticated

### FileItem
- `name` must not contain path separators
- `path` must be absolute
- `size` must be ≥0

### GCSObject
- `name` must not be empty
- `bucket_name` must match GCS naming rules (3-63 chars, lowercase, no underscores)
- `storage_class` must be valid GCS class

### GCSBucket
- `name` must be globally unique and match GCS naming rules
- `project_id` must match GCP project ID format

### TransferOperation
- `source_items` must not be empty
- `progress_percent` must be 0.0-100.0
- `bytes_transferred` must not exceed `total_bytes`
- `files_completed` must not exceed `files_total`

### Configuration
- `max_concurrent_transfers` must be 1-10
- At most one project can have `default=true`

## Identity & Uniqueness

| Entity | Identity | Uniqueness Scope |
|--------|----------|------------------|
| UserSession | email | Application instance (single user) |
| FileItem | path | Local filesystem |
| GCSObject | bucket_name + name + generation | GCS (versioned) |
| GCSBucket | name | Global (GCS) |
| Panel | id | Application instance |
| TransferOperation | id (UUID) | Application instance |
| ProjectConfig | project_id | Configuration file |

## Data Volume Assumptions

- Typical directory listing: 100-1000 items
- Large directory/bucket: up to 100,000 items (paginated)
- Concurrent transfer operations: 1-10
- Configured projects: 1-20
- Transfer queue size: 1-100 files per operation
- Single authenticated user per application instance
