"""Properties dialog for viewing file/object metadata."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from src.models.file_item import FileItem
from src.models.gcs_bucket import GCSBucket
from src.models.gcs_object import GCSObject


class PropertiesDialog(tk.Toplevel):
    """Modal dialog showing detailed metadata for a file, GCS object, or bucket."""

    def __init__(self, parent: tk.Widget, item: Any) -> None:
        super().__init__(parent)
        self.title("Properties")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        if isinstance(item, FileItem):
            self._show_file_item(frame, item)
        elif isinstance(item, GCSObject):
            self._show_gcs_object(frame, item)
        elif isinstance(item, GCSBucket):
            self._show_gcs_bucket(frame, item)
        else:
            ttk.Label(frame, text=f"Unknown item type: {type(item).__name__}").pack()

        ttk.Button(frame, text="Close", command=self.destroy).pack(pady=(15, 0))

        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - w // 2}+{py - h // 2}")

    def _add_row(self, parent: ttk.Frame, label: str, value: str) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=f"{label}:", width=18, anchor=tk.E).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row, text=value, anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _show_file_item(self, frame: ttk.Frame, item: FileItem) -> None:
        ttk.Label(
            frame,
            text=item.name,
            font=("TkDefaultFont", 13, "bold"),
        ).pack(pady=(0, 10))

        self._add_row(frame, "Type", "Folder" if item.is_directory else "File")
        self._add_row(frame, "Full Path", str(item.path))
        self._add_row(frame, "Size", f"{item.size:,} bytes ({item.display_size})")
        self._add_row(frame, "Created", item.created_date.strftime("%Y-%m-%d %H:%M:%S UTC"))
        self._add_row(frame, "Modified", item.modified_date.strftime("%Y-%m-%d %H:%M:%S UTC"))
        self._add_row(frame, "Permissions", item.permissions)
        if not item.is_directory:
            self._add_row(frame, "Extension", item.extension or "(none)")

    def _show_gcs_object(self, frame: ttk.Frame, item: GCSObject) -> None:
        ttk.Label(
            frame,
            text=item.display_name,
            font=("TkDefaultFont", 13, "bold"),
        ).pack(pady=(0, 10))

        self._add_row(frame, "Full Path", f"gs://{item.bucket_name}/{item.name}")
        self._add_row(frame, "Bucket", item.bucket_name)
        self._add_row(frame, "Size", f"{item.size:,} bytes ({item.display_size})")
        self._add_row(frame, "Content Type", item.content_type)
        self._add_row(frame, "Storage Class", item.storage_class)
        self._add_row(frame, "Created", item.created_time.strftime("%Y-%m-%d %H:%M:%S UTC"))
        self._add_row(frame, "Updated", item.updated_time.strftime("%Y-%m-%d %H:%M:%S UTC"))
        self._add_row(frame, "Generation", str(item.generation))
        self._add_row(frame, "MD5 Hash", item.md5_hash or "(none)")

        if item.metadata:
            ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
            ttk.Label(frame, text="Custom Metadata:", font=("TkDefaultFont", 10, "bold")).pack(
                anchor=tk.W, pady=(0, 5)
            )
            for key, value in item.metadata.items():
                self._add_row(frame, key, value)

    def _show_gcs_bucket(self, frame: ttk.Frame, item: GCSBucket) -> None:
        ttk.Label(
            frame,
            text=item.name,
            font=("TkDefaultFont", 13, "bold"),
        ).pack(pady=(0, 10))

        self._add_row(frame, "Project", item.project_id)
        self._add_row(frame, "Location", item.display_location)
        self._add_row(frame, "Storage Class", item.storage_class)
        self._add_row(frame, "Created", item.created_time.strftime("%Y-%m-%d %H:%M:%S UTC"))
        self._add_row(frame, "Versioning", "Enabled" if item.versioning_enabled else "Disabled")
