# Feature Specification: Dual-Panel File Manager

**Feature Branch**: `001-dual-panel-filemanager`
**Created**: 2026-02-04
**Status**: Draft
**Input**: User description: "Build the desktop application which will be used as file-manager to manipulate with files located locally and in different GCP GCS buckets. The application represent two-panel file-manager in style of famous total-commander application. User will be able to choose on each side the list of all available buckets which belongs to some GCP project or file hierarchy of specific bucket or file hierarchy of local disk. Then user will be able to copy/move files between panels, delete them, see their metadata, creation date, size etc."

## Clarifications

### Session 2026-02-04

- Q: When copying folders, should contents be included? → A: Recursive copy - include all nested files and subfolders
- Q: How should users specify which GCP project to browse? → A: Configuration file listing allowed project IDs
- Q: How many concurrent file transfers should be allowed? → A: User-configurable limit in settings
- Q: How should users authenticate with GCP? → A: Browser-based authentication flow (OAuth2)

## User Scenarios & Testing *(mandatory)*

### User Story 0 - Authenticate with GCP (Priority: P0)

As a user, I want to sign in to my Google Cloud account through my web browser so that the application can access my GCS buckets without requiring me to run command-line tools or manually configure credentials. When I launch the application and try to access GCS features, I am prompted to sign in via my default browser.

**Why this priority**: Authentication is a prerequisite for all GCS functionality. Without authentication, users cannot access any cloud features. Browser-based auth provides the most user-friendly experience for desktop applications.

**Independent Test**: Can be fully tested by launching the application, attempting to access GCS, completing browser sign-in, and verifying GCS buckets are accessible.

**Acceptance Scenarios**:

1. **Given** the application is launched for the first time, **When** the user attempts to access GCS features, **Then** a dialog appears explaining that sign-in is required with a "Sign in with Google" button.
2. **Given** the sign-in dialog is shown, **When** the user clicks "Sign in with Google", **Then** the default web browser opens to Google's authentication page.
3. **Given** the browser is showing Google sign-in, **When** the user completes authentication and grants permissions, **Then** the browser shows a success message and the application receives the credentials.
4. **Given** authentication succeeds, **When** the application receives credentials, **Then** GCS features become available and the user's account email is displayed in the application.
5. **Given** the user has previously authenticated, **When** the application is launched again, **Then** the stored credentials are used automatically without requiring re-authentication (until they expire or are revoked).
6. **Given** stored credentials have expired, **When** the user attempts a GCS operation, **Then** the application automatically refreshes the token or prompts for re-authentication if refresh fails.

---

### User Story 0.1 - Sign Out (Priority: P0)

As a user, I want to sign out of my Google account so that I can switch accounts or remove my credentials from the application for security reasons.

**Why this priority**: Users need control over their authentication state for security and multi-account scenarios.

**Independent Test**: Can be fully tested by signing in, then signing out, and verifying GCS access is revoked.

**Acceptance Scenarios**:

1. **Given** the user is signed in, **When** the user selects "Sign Out" from the account menu, **Then** a confirmation dialog appears.
2. **Given** the confirmation dialog is shown, **When** the user confirms sign-out, **Then** stored credentials are removed and GCS features show the sign-in prompt.
3. **Given** the user has signed out, **When** they attempt GCS operations, **Then** they are prompted to sign in again.

---

### User Story 1 - Browse Local Files (Priority: P1)

As a user, I want to browse my local file system in one panel so that I can see and navigate through my folders and files. The panel displays the current directory path, a list of files and folders with their names, sizes, modification dates, and type indicators. I can double-click folders to enter them, use a parent directory option to go up, and select files for operations.

**Why this priority**: This is the foundational functionality. Without local file browsing, the application has no value. This enables users to work with their most common files immediately.

**Independent Test**: Can be fully tested by launching the application, seeing the local file system displayed, navigating folders, and verifying file metadata displays correctly.

**Acceptance Scenarios**:

1. **Given** the application is launched, **When** the user starts the app, **Then** one panel displays the user's home directory with files and folders listed showing name, size, and modification date.
2. **Given** a panel shows a directory listing, **When** the user double-clicks a folder, **Then** the panel navigates into that folder and displays its contents.
3. **Given** a panel shows a directory listing, **When** the user clicks the parent directory option (..), **Then** the panel navigates to the parent folder.
4. **Given** a panel shows files, **When** the user views the list, **Then** each file shows its name, size (human-readable format), and last modified date.

---

### User Story 2 - Browse GCS Buckets (Priority: P2)

As a user, I want to browse Google Cloud Storage buckets in a panel so that I can see cloud-stored files alongside local files. I can select a GCP project, see all buckets in that project, navigate into a bucket to see its contents (blobs organized by prefix/folder structure), and view object metadata.

**Why this priority**: This is the core differentiating feature that enables cloud file management. It builds on the browsing paradigm established in P1.

**Independent Test**: Can be fully tested by connecting to a GCP project, listing buckets, navigating into a bucket, and viewing object metadata.

**Acceptance Scenarios**:

1. **Given** the user has GCP credentials configured, **When** the user selects "GCS" as the source for a panel and chooses a project, **Then** the panel displays all accessible buckets in that project.
2. **Given** a panel shows a bucket list, **When** the user double-clicks a bucket, **Then** the panel navigates into the bucket showing top-level objects and prefixes (displayed as folders).
3. **Given** a panel shows bucket contents, **When** the user views an object, **Then** metadata displays including name, size, storage class, creation date, and content type.
4. **Given** a panel shows bucket contents with prefixes, **When** the user double-clicks a prefix (folder), **Then** the panel shows objects under that prefix.

---

### User Story 3 - Copy Files Between Panels (Priority: P3)

As a user, I want to copy files from one panel to the other so that I can transfer files between local storage and GCS, or between different GCS locations. I select one or more files in the source panel and initiate a copy operation to the destination shown in the other panel.

**Why this priority**: File transfer is the primary action users need after browsing. Copy is non-destructive and safer than move for initial implementation.

**Independent Test**: Can be fully tested by selecting files in one panel and copying them to the location shown in the other panel, then verifying the files appear in the destination.

**Acceptance Scenarios**:

1. **Given** files are selected in the left panel showing local files and the right panel shows a GCS bucket location, **When** the user initiates copy, **Then** selected files are uploaded to the GCS location and appear in the right panel after refresh.
2. **Given** files are selected in a GCS panel and the other panel shows a local directory, **When** the user initiates copy, **Then** selected objects are downloaded to the local directory.
3. **Given** a copy operation is in progress, **When** the user views the interface, **Then** a progress indicator shows transfer status including percentage complete.
4. **Given** multiple files are selected for copy, **When** the copy completes, **Then** all files exist in both source and destination locations.

---

### User Story 4 - Move Files Between Panels (Priority: P4)

As a user, I want to move files from one panel to the other so that I can relocate files without leaving copies behind. Move copies the file to the destination then deletes the source.

**Why this priority**: Move is a common operation but riskier than copy since it deletes the source. Built on copy functionality.

**Independent Test**: Can be fully tested by selecting files, initiating move, and verifying files exist in destination but not in source.

**Acceptance Scenarios**:

1. **Given** files are selected in one panel, **When** the user initiates move, **Then** files are copied to the destination panel location and removed from the source location.
2. **Given** a move operation completes successfully, **When** the user views both panels, **Then** files appear only in the destination panel.
3. **Given** a move operation fails during copy phase, **When** the error occurs, **Then** source files remain intact and user is notified of the failure.

---

### User Story 5 - Delete Files (Priority: P5)

As a user, I want to delete files from either local storage or GCS so that I can remove unwanted files. Delete requires confirmation before execution.

**Why this priority**: Deletion is destructive and requires careful implementation. Lower priority than transfer operations.

**Independent Test**: Can be fully tested by selecting files, confirming deletion, and verifying files no longer exist.

**Acceptance Scenarios**:

1. **Given** files are selected in a panel, **When** the user initiates delete, **Then** a confirmation dialog appears listing files to be deleted.
2. **Given** the confirmation dialog is shown, **When** the user confirms deletion, **Then** selected files are permanently removed from their location.
3. **Given** the confirmation dialog is shown, **When** the user cancels, **Then** no files are deleted and the dialog closes.
4. **Given** a GCS object is selected for deletion, **When** confirmed, **Then** the object is deleted from the bucket.

---

### User Story 6 - View File Metadata (Priority: P6)

As a user, I want to view detailed metadata for a selected file so that I can see properties beyond what the list shows. This includes full path, exact size in bytes, all timestamps, and for GCS objects: storage class, content type, generation, and custom metadata.

**Why this priority**: Detailed metadata viewing enhances usability but is not essential for core file management tasks.

**Independent Test**: Can be fully tested by selecting a file and viewing its detailed properties panel.

**Acceptance Scenarios**:

1. **Given** a local file is selected, **When** the user requests file properties, **Then** a dialog shows full path, size, created date, modified date, and permissions.
2. **Given** a GCS object is selected, **When** the user requests object properties, **Then** a dialog shows full path, size, content type, storage class, creation time, update time, generation, and any custom metadata.

---

### User Story 7 - Switch Panel Source (Priority: P7)

As a user, I want to switch what each panel displays (local disk, GCS project list, or specific bucket) so that I can configure the two-panel layout for my current task.

**Why this priority**: Essential for flexibility but the default configuration (local + GCS) covers the primary use case.

**Independent Test**: Can be fully tested by using panel controls to switch between local, project view, and bucket views.

**Acceptance Scenarios**:

1. **Given** a panel is showing local files, **When** the user selects "Switch to GCS", **Then** the panel shows a project/bucket selection interface.
2. **Given** a panel is showing GCS contents, **When** the user selects "Switch to Local", **Then** the panel shows the local file system starting at the home directory.
3. **Given** both panels can be independently configured, **When** the user sets both to local directories, **Then** the application supports local-to-local file operations.

---

### Edge Cases

- What happens when the user tries to copy a file that already exists in the destination? (Prompt to overwrite, skip, or rename)
- What happens when GCP credentials are not configured or expired? (Prompt for browser-based sign-in)
- What happens if the user closes the browser during authentication? (Show error and allow retry)
- What happens if the user denies permission scopes? (Explain required permissions and allow retry)
- What happens when network connectivity is lost during a GCS operation? (Cancel operation gracefully, show error, preserve source files)
- What happens when the user tries to access a bucket they don't have permission for? (Display permission error, don't crash)
- What happens when copying very large files (multi-GB)? (Show progress, allow cancellation, use resumable uploads for GCS)
- What happens when a file is deleted externally while displayed in a panel? (Handle gracefully on next operation, refresh panel)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a two-panel interface where each panel can independently show file/folder listings
- **FR-002**: System MUST support browsing local file system directories with navigation (enter folder, go to parent)
- **FR-003**: System MUST support browsing GCS buckets and their contents organized by prefix hierarchy
- **FR-004**: System MUST display file metadata: name, size (human-readable), modification/creation date for all items
- **FR-005**: System MUST allow selection of single or multiple files/objects for operations
- **FR-006**: System MUST support copying files/objects from one panel location to the other panel location; folder copies MUST be recursive (include all nested files and subfolders)
- **FR-007**: System MUST support moving files/objects from one panel location to the other panel location
- **FR-008**: System MUST support deleting files/objects with confirmation before execution
- **FR-009**: System MUST show transfer progress for copy/move operations including percentage complete
- **FR-010**: System MUST allow cancellation of in-progress transfer operations
- **FR-011**: System MUST provide a user-configurable setting for maximum concurrent transfers (default: 3)
- **FR-012**: System MUST authenticate with GCP using browser-based OAuth2 flow; the application opens the user's default browser for Google sign-in
- **FR-012a**: System MUST securely store authentication tokens locally after successful sign-in
- **FR-012b**: System MUST automatically refresh expired tokens when possible
- **FR-012c**: System MUST provide a sign-out option that clears stored credentials
- **FR-012d**: System MUST display the authenticated user's email address when signed in
- **FR-013**: System MUST allow switching each panel between local file system and GCS views
- **FR-014**: System MUST allow selecting which GCP project's buckets to display; available projects MUST be defined in a configuration file
- **FR-015**: System MUST display detailed metadata for selected items on request (properties dialog)
- **FR-016**: System MUST handle file conflicts (existing destination file) by prompting user for action: overwrite, skip, or rename
- **FR-017**: System MUST preserve file metadata (where applicable) during copy/move operations
- **FR-018**: System MUST display appropriate error messages when operations fail (permission denied, network error, etc.)
- **FR-019**: System MUST support keyboard shortcuts for common operations (copy, move, delete, refresh, select all)

### Key Entities

- **Panel**: A file browser view displaying either local filesystem or GCS contents; has current location, selected items, and source type (local/GCS)
- **FileItem**: Represents a local file or folder; has name, path, size, modification date, type (file/directory), permissions
- **GCSObject**: Represents a GCS blob; has name, bucket, size, content type, storage class, creation time, generation, custom metadata
- **GCSBucket**: Represents a GCS bucket; has name, project, location, storage class, creation date
- **TransferOperation**: Represents an in-progress file transfer; has source, destination, progress percentage, status, items list
- **GCPProject**: Represents a GCP project context; has project ID and associated credentials
- **UserSession**: Represents the authenticated user; has email, access token, refresh token, token expiry, sign-in time

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can navigate to any local directory within 3 clicks or keystrokes from application start
- **SC-002**: Users can list contents of a GCS bucket within 5 seconds of selecting it (for buckets with <1000 objects)
- **SC-003**: Users can complete a file copy operation between local and GCS in under 5 user actions (select, initiate, confirm)
- **SC-004**: File transfers show progress updates at least every 2 seconds during active transfer
- **SC-005**: Users can identify file size, type, and date for any listed item without additional clicks
- **SC-006**: System handles 10,000+ files in a single directory/bucket listing without becoming unresponsive
- **SC-007**: Users can cancel any in-progress operation within 2 seconds of initiating cancel
- **SC-008**: 90% of common file operations (copy, move, delete) can be performed via keyboard shortcuts
- **SC-009**: Error messages clearly indicate what went wrong and suggest corrective action
- **SC-010**: Application cold start completes and shows usable interface within 3 seconds
- **SC-011**: Users can complete browser-based sign-in and access GCS within 60 seconds of clicking "Sign in"
- **SC-012**: Returning users with valid stored credentials can access GCS immediately without re-authentication

## Assumptions

- Users have Python 3.10+ installed for development/packaging purposes (end users receive standalone executable)
- Users have a Google account with access to at least one GCP project
- Users can complete OAuth2 authentication via their web browser
- The application will request only the minimum required GCS scopes (read/write storage)
- Users understand the GCS bucket/object model (objects, prefixes as pseudo-folders)
- Local file operations follow operating system permissions (application doesn't require elevated privileges)
- Network connectivity is available for GCS operations (no offline mode for cloud features)
- Standard GCS pricing applies for operations and data transfer (not application's concern, but users should be aware)
