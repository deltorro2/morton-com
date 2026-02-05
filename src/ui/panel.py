"""File browser panel widget.

Each panel can display local filesystem, GCS bucket list, or GCS bucket
contents.  Navigation, loading, and source-type switching are handled here.
"""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING, Any

from src.models import SourceType
from src.models.file_item import FileItem
from src.models.panel_state import PanelState
from src.ui.widgets.file_list import FileListWidget

if TYPE_CHECKING:
    from src.services.auth_service import AuthService
    from src.services.gcs_client import GCSClient
    from src.services.local_filesystem import LocalFilesystem


class Panel(ttk.Frame):
    """A single file-browser panel."""

    def __init__(
        self,
        parent: tk.Widget,
        panel_id: str,
        local_fs: LocalFilesystem,
        auth_service: AuthService | None = None,
        gcs_client: Any = None,
        projects: list | None = None,
        show_hidden: bool = False,
        on_selection_changed: callable | None = None,
    ) -> None:
        super().__init__(parent)
        self._panel_id = panel_id
        self._local_fs = local_fs
        self._auth_service = auth_service
        self._gcs_client = gcs_client
        self._projects = projects or []
        self._show_hidden = show_hidden
        self._on_selection_changed = on_selection_changed

        self._state = PanelState(
            id=panel_id,
            source_type=SourceType.LOCAL,
            location=str(local_fs.get_home_directory()),
        )

        self._build_ui()
        self._load_current()

    @property
    def state(self) -> PanelState:
        return self._state

    @property
    def panel_id(self) -> str:
        return self._panel_id

    def _build_ui(self) -> None:
        # Top bar: source selector + path
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=2, pady=2)

        # Source type dropdown
        self._source_var = tk.StringVar(value="Local")
        source_options = ["Local"]
        for proj in self._projects:
            name = proj.display_name or proj.project_id
            source_options.append(f"GCS: {name}")

        self._source_combo = ttk.Combobox(
            top_frame,
            textvariable=self._source_var,
            values=source_options,
            state="readonly",
            width=20,
        )
        self._source_combo.pack(side=tk.LEFT, padx=(0, 5))
        self._source_combo.bind("<<ComboboxSelected>>", self._on_source_changed)

        # Path label
        self._path_var = tk.StringVar(value=self._state.location)
        self._path_label = ttk.Label(
            top_frame,
            textvariable=self._path_var,
            anchor=tk.W,
        )
        self._path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # File list
        self._file_list = FileListWidget(
            self,
            on_double_click=self._on_item_double_click,
            on_selection_changed=self._on_item_selection_changed,
        )
        self._file_list.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Status bar
        self._status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self._status_var, anchor=tk.W).pack(
            fill=tk.X, padx=5, pady=(0, 2)
        )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate_to(self, path: str) -> None:
        """Navigate to a local directory path."""
        self._state.source_type = SourceType.LOCAL
        self._state.location = path
        self._path_var.set(path)
        self._load_current()

    def navigate_up(self) -> None:
        """Go to parent directory or prefix."""
        if self._state.source_type == SourceType.LOCAL:
            parent = str(Path(self._state.location).parent)
            self.navigate_to(parent)
        elif self._state.source_type == SourceType.GCS_BUCKET:
            prefix = self._state.location
            if prefix:
                # Go up one level in prefix hierarchy
                parts = prefix.rstrip("/").rsplit("/", 1)
                new_prefix = parts[0] + "/" if len(parts) > 1 else ""
                self._state.location = new_prefix
                self._path_var.set(
                    f"gs://{self._state.bucket_name}/{new_prefix}" if new_prefix else
                    f"gs://{self._state.bucket_name}/"
                )
                self._load_current()
            else:
                # Go back to bucket list
                self._state.source_type = SourceType.GCS_PROJECT
                self._state.bucket_name = ""
                self._state.location = ""
                self._path_var.set(f"GCS: {self._state.project_id}")
                self._load_current()

    def refresh(self) -> None:
        """Reload the current listing."""
        self._load_current()

    def set_show_hidden(self, show: bool) -> None:
        """Update hidden files visibility and refresh."""
        self._show_hidden = show
        if self._state.source_type == SourceType.LOCAL:
            self._load_current()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_current(self) -> None:
        """Load items for the current state in a background thread."""
        self._state.loading = True
        self._state.error = ""
        self._status_var.set("Loading...")

        thread = threading.Thread(target=self._load_worker, daemon=True)
        thread.start()

    def _load_worker(self) -> None:
        """Background loading logic."""
        try:
            if self._state.source_type == SourceType.LOCAL:
                items = self._local_fs.list_directory(
                    Path(self._state.location),
                    show_hidden=self._show_hidden,
                )
                # Prepend ".." entry when not at a filesystem root
                current = Path(self._state.location)
                if current.parent != current:
                    items = [".."] + list(items)
                self.after(0, lambda: self._display_items(items, "local"))

            elif self._state.source_type == SourceType.GCS_PROJECT:
                if self._gcs_client is None:
                    self.after(
                        0,
                        lambda: self._show_error("GCS client not available"),
                    )
                    return
                buckets = self._gcs_client.list_buckets(self._state.project_id)
                self.after(0, lambda: self._display_items(buckets, "gcs_bucket"))

            elif self._state.source_type == SourceType.GCS_BUCKET:
                if self._gcs_client is None:
                    self.after(
                        0,
                        lambda: self._show_error("GCS client not available"),
                    )
                    return
                objects, prefixes = self._gcs_client.list_objects(
                    self._state.bucket_name,
                    prefix=self._state.location,
                )
                # Build mixed list: prefix pseudo-dirs first, then objects
                from src.models.gcs_object import GCSObject

                prefix_items = [
                    GCSObject(
                        name=p,
                        bucket_name=self._state.bucket_name,
                        size=0,
                        content_type="",
                        storage_class="",
                        created_time=objects[0].created_time if objects else __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                        updated_time=objects[0].updated_time if objects else __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                        generation=0,
                        metadata={},
                        md5_hash="",
                    )
                    for p in prefixes
                ]
                all_items: list = prefix_items + list(objects)
                self.after(0, lambda: self._display_items(all_items, "gcs_object"))

        except Exception as exc:
            self.after(0, lambda: self._show_error(str(exc)))

    def _display_items(self, items: list, mode: str) -> None:
        """Update the file list on the main thread."""
        self._state.items = items
        self._state.loading = False
        self._state.selected_indices = set()

        if mode == "local":
            self._file_list.set_columns_for_local()
        elif mode == "gcs_bucket":
            self._file_list.set_columns_for_gcs_buckets()
        elif mode == "gcs_object":
            self._file_list.set_columns_for_gcs_objects()

        self._file_list.set_items(items, mode)
        count = len(items)
        self._status_var.set(f"{count} item{'s' if count != 1 else ''}")

    def _show_error(self, message: str) -> None:
        self._state.loading = False
        self._state.error = message
        self._status_var.set(f"Error: {message}")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_item_double_click(self, item: Any) -> None:
        """Handle double-click on an item."""
        if self._state.source_type == SourceType.LOCAL:
            if isinstance(item, FileItem) and item.is_directory:
                self.navigate_to(str(item.path))
            elif isinstance(item, str) and item == "..":
                self.navigate_up()

        elif self._state.source_type == SourceType.GCS_PROJECT:
            from src.models.gcs_bucket import GCSBucket

            if isinstance(item, GCSBucket):
                self._state.source_type = SourceType.GCS_BUCKET
                self._state.bucket_name = item.name
                self._state.location = ""
                self._path_var.set(f"gs://{item.name}/")
                self._load_current()

        elif self._state.source_type == SourceType.GCS_BUCKET:
            from src.models.gcs_object import GCSObject

            if isinstance(item, GCSObject) and item.is_prefix:
                self._state.location = item.name
                self._path_var.set(f"gs://{self._state.bucket_name}/{item.name}")
                self._load_current()

    def _on_item_selection_changed(self, items: list) -> None:
        indices = self._file_list.get_selected_indices()
        self._state.selected_indices = set(indices)
        if self._on_selection_changed:
            self._on_selection_changed(self._panel_id, items)

    def _on_source_changed(self, event: tk.Event) -> None:
        """Handle source type dropdown change."""
        value = self._source_var.get()

        if value == "Local":
            self._state.source_type = SourceType.LOCAL
            self._state.location = str(self._local_fs.get_home_directory())
            self._state.project_id = ""
            self._state.bucket_name = ""
            self._path_var.set(self._state.location)
            self._file_list.set_columns_for_local()
            self._load_current()
        elif value.startswith("GCS: "):
            project_name = value[5:]
            # Find matching project
            for proj in self._projects:
                display = proj.display_name or proj.project_id
                if display == project_name:
                    self._switch_to_gcs_project(proj.project_id)
                    break

    def _switch_to_gcs_project(self, project_id: str) -> None:
        """Switch panel to GCS project view (with auth check)."""
        if self._auth_service is None:
            self._show_error("Authentication service not available")
            return

        self._auth_service.ensure_authenticated(
            on_authenticated=lambda _: self._load_gcs_project(project_id),
            on_sign_in_required=lambda: self._prompt_sign_in(project_id),
        )

    def _load_gcs_project(self, project_id: str) -> None:
        self._state.source_type = SourceType.GCS_PROJECT
        self._state.project_id = project_id
        self._state.bucket_name = ""
        self._state.location = ""
        self._path_var.set(f"GCS: {project_id}")
        self._file_list.set_columns_for_gcs_buckets()
        self._load_current()

    def _prompt_sign_in(self, project_id: str) -> None:
        """Show sign-in dialog, then load project on success."""
        from src.ui.dialogs.auth import SignInDialog

        SignInDialog(
            self.winfo_toplevel(),
            self._auth_service,
            on_success=lambda _: self._load_gcs_project(project_id),
        )

    # ------------------------------------------------------------------
    # Selection helpers (used by keyboard shortcuts)
    # ------------------------------------------------------------------

    def select_all(self) -> None:
        self._file_list.select_all()

    def get_selected_items(self) -> list:
        return [i for i in self._file_list.get_selected_items() if i != ".."]

    def focus_panel(self) -> None:
        self._file_list.focus_widget()
