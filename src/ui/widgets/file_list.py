"""Treeview-based file listing widget for displaying files and GCS objects."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any


class FileListWidget(ttk.Frame):
    """A Treeview widget for displaying file/object listings.

    Supports local FileItem, GCSObject, and GCSBucket display with
    column sorting, selection, and navigation callbacks.
    """

    # Column definitions: (id, heading, width, anchor, stretch)
    _LOCAL_COLUMNS = [
        ("name", "Name", 300, tk.W, True),
        ("size", "Size", 100, tk.E, False),
        ("modified", "Modified", 180, tk.W, False),
    ]
    _GCS_OBJECT_COLUMNS = [
        ("name", "Name", 300, tk.W, True),
        ("size", "Size", 100, tk.E, False),
        ("type", "Type", 120, tk.W, False),
        ("modified", "Modified", 180, tk.W, False),
    ]
    _GCS_BUCKET_COLUMNS = [
        ("name", "Name", 250, tk.W, True),
        ("location", "Location", 150, tk.W, False),
        ("class", "Storage Class", 120, tk.W, False),
        ("created", "Created", 180, tk.W, False),
    ]

    def __init__(
        self,
        parent: tk.Widget,
        on_double_click: callable | None = None,
        on_selection_changed: callable | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_double_click = on_double_click
        self._on_selection_changed = on_selection_changed
        self._items: list[Any] = []
        self._sort_column = "name"
        self._sort_ascending = True

        self._build_tree(self._LOCAL_COLUMNS)

    def _build_tree(self, columns: list[tuple]) -> None:
        """Create or recreate the Treeview with given columns."""
        # Remove existing tree if present
        for child in self.winfo_children():
            child.destroy()

        col_ids = [c[0] for c in columns]

        self._tree = ttk.Treeview(
            self,
            columns=col_ids,
            show="headings",
            selectmode="extended",
        )

        for col_id, heading, width, anchor, stretch in columns:
            self._tree.heading(
                col_id,
                text=heading,
                command=lambda c=col_id: self._on_sort(c),
            )
            self._tree.column(col_id, width=width, anchor=anchor, stretch=stretch)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bindings
        self._tree.bind("<Double-1>", self._handle_double_click)
        self._tree.bind("<<TreeviewSelect>>", self._handle_selection)
        self._tree.bind("<Return>", self._handle_double_click)

    def set_columns_for_local(self) -> None:
        """Configure columns for local filesystem display."""
        self._build_tree(self._LOCAL_COLUMNS)

    def set_columns_for_gcs_objects(self) -> None:
        """Configure columns for GCS object display."""
        self._build_tree(self._GCS_OBJECT_COLUMNS)

    def set_columns_for_gcs_buckets(self) -> None:
        """Configure columns for GCS bucket display."""
        self._build_tree(self._GCS_BUCKET_COLUMNS)

    def set_items(self, items: list[Any], mode: str = "local") -> None:
        """Populate the tree with items.

        Parameters
        ----------
        items:
            List of FileItem, GCSObject, or GCSBucket.
        mode:
            One of ``"local"``, ``"gcs_object"``, ``"gcs_bucket"``.
        """
        self._items = list(items)
        self._tree.delete(*self._tree.get_children())

        for idx, item in enumerate(self._items):
            values = self._format_item(item, mode)
            self._tree.insert("", tk.END, iid=str(idx), values=values)

    def _format_item(self, item: Any, mode: str) -> tuple:
        """Format an item into column values."""
        if mode == "local":
            from src.models.file_item import FileItem

            if isinstance(item, FileItem):
                icon = "\U0001f4c1 " if item.is_directory else "\U0001f4c4 "
                return (
                    icon + item.name,
                    item.display_size if not item.is_directory else "<DIR>",
                    item.modified_date.strftime("%Y-%m-%d %H:%M"),
                )
            # ".." parent entry
            return ("\U0001f4c1 ..", "", "")

        elif mode == "gcs_object":
            from src.models.gcs_object import GCSObject

            if isinstance(item, GCSObject):
                if item.is_prefix:
                    return ("\U0001f4c1 " + item.display_name, "<DIR>", "", "")
                return (
                    "\U0001f4c4 " + item.display_name,
                    item.display_size,
                    item.content_type,
                    item.updated_time.strftime("%Y-%m-%d %H:%M"),
                )
            return ("\U0001f4c1 ..", "", "", "")

        elif mode == "gcs_bucket":
            from src.models.gcs_bucket import GCSBucket

            if isinstance(item, GCSBucket):
                return (
                    "\U0001f5c4 " + item.name,
                    item.display_location,
                    item.storage_class,
                    item.created_time.strftime("%Y-%m-%d %H:%M"),
                )
            return ("", "", "", "")

        return (str(item),)

    def get_selected_indices(self) -> list[int]:
        """Return indices of selected items."""
        return [int(iid) for iid in self._tree.selection()]

    def get_selected_items(self) -> list[Any]:
        """Return the selected item objects."""
        return [self._items[i] for i in self.get_selected_indices() if i < len(self._items)]

    def select_all(self) -> None:
        """Select all items."""
        all_ids = self._tree.get_children()
        self._tree.selection_set(all_ids)

    def clear_selection(self) -> None:
        """Deselect all items."""
        self._tree.selection_remove(*self._tree.selection())

    def _on_sort(self, column: str) -> None:
        """Sort items by column, toggling direction."""
        if self._sort_column == column:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = column
            self._sort_ascending = True

        # Re-sort the display (not the underlying data)
        items_with_idx = list(enumerate(self._tree.get_children()))
        # This is a visual sort only — real sorting would need mode-aware comparators
        # For now, sort by the displayed text in the column
        col_idx = [c[0] for c in self._tree["columns"]].index(column) if column in self._tree["columns"] else 0

        decorated = []
        for original_idx, iid in items_with_idx:
            val = self._tree.set(iid, column)
            decorated.append((val, iid))

        # Keep ".." pinned at position 0
        parent_entry = None
        if self._items and self._items[0] == "..":
            parent_entry = decorated.pop(0)

        decorated.sort(key=lambda x: x[0].lower(), reverse=not self._sort_ascending)

        if parent_entry is not None:
            decorated.insert(0, parent_entry)

        for new_pos, (_, iid) in enumerate(decorated):
            self._tree.move(iid, "", new_pos)

    def _handle_double_click(self, event: tk.Event) -> None:
        selection = self._tree.selection()
        if selection and self._on_double_click:
            idx = int(selection[0])
            if idx < len(self._items):
                self._on_double_click(self._items[idx])

    def _handle_selection(self, event: tk.Event) -> None:
        if self._on_selection_changed:
            self._on_selection_changed(self.get_selected_items())

    def focus_widget(self) -> None:
        """Set keyboard focus to the treeview."""
        self._tree.focus_set()
