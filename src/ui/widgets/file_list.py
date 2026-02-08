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
        on_tab: callable | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_double_click = on_double_click
        self._on_selection_changed = on_selection_changed
        self._on_tab = on_tab
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

        # Scrollbar (auto-hide via grid_remove / grid)
        self._scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=self._on_scroll_set)
        self._scrollbar_visible = False

        # Use grid so show/hide is reliable across tree rebuilds
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._tree.grid(row=0, column=0, sticky="nsew")
        self._scrollbar.grid(row=0, column=1, sticky="ns")
        self._scrollbar.grid_remove()

        # Bindings
        self._tree.bind("<Double-1>", self._handle_double_click)
        self._tree.bind("<<TreeviewSelect>>", self._handle_selection)
        self._tree.bind("<Return>", self._handle_double_click)
        self._tree.bind("<Tab>", self._handle_tab)
        self._tree.bind("<Shift-Up>", self._handle_shift_up)
        self._tree.bind("<Shift-Down>", self._handle_shift_down)

        # Remove the default Treeview class binding for <space>
        # (it does "selection toggle [focus]" which conflicts with our
        # multi-select handler). Then bind our own.
        self._tree.unbind_class("Treeview", "<space>")
        self._tree.bind("<space>", self._handle_space)

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

    def select_first(self) -> None:
        """Select the first real item, skipping '..' unless it is the only one."""
        children = self._tree.get_children()
        if not children:
            return
        target = children[0]
        if len(children) > 1 and self._items and self._items[0] == "..":
            target = children[1]
        self._tree.selection_set(target)
        self._tree.focus(target)
        self._tree.see(target)

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

    def _handle_tab(self, event: tk.Event) -> str:
        if self._on_tab:
            self._on_tab()
        return "break"

    def _handle_space(self, event: tk.Event) -> str:
        """Toggle selection on focused item, then move focus down."""
        focused = self._tree.focus()
        if not focused:
            return "break"
        if focused in self._tree.selection():
            self._tree.selection_remove(focused)
        else:
            self._tree.selection_add(focused)
        # Move focus to next item (Total Commander style)
        next_item = self._tree.next(focused)
        if next_item:
            self._tree.focus(next_item)
            self._tree.see(next_item)
        return "break"

    def _handle_shift_up(self, event: tk.Event) -> str:
        """Extend selection upward."""
        focused = self._tree.focus()
        if not focused:
            return "break"
        prev_item = self._tree.prev(focused)
        if not prev_item:
            return "break"
        current_sel = set(self._tree.selection())
        current_sel.add(prev_item)
        self._tree.selection_set(list(current_sel))
        self._tree.focus(prev_item)
        self._tree.see(prev_item)
        return "break"

    def _handle_shift_down(self, event: tk.Event) -> str:
        """Extend selection downward."""
        focused = self._tree.focus()
        if not focused:
            return "break"
        next_item = self._tree.next(focused)
        if not next_item:
            return "break"
        current_sel = set(self._tree.selection())
        current_sel.add(next_item)
        self._tree.selection_set(list(current_sel))
        self._tree.focus(next_item)
        self._tree.see(next_item)
        return "break"

    def _handle_selection(self, event: tk.Event) -> None:
        if self._on_selection_changed:
            self._on_selection_changed(self.get_selected_items())

    def _on_scroll_set(self, first: str, last: str) -> None:
        """Show/hide the scrollbar based on whether all content is visible."""
        self._scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            if self._scrollbar_visible:
                self._scrollbar.grid_remove()
                self._scrollbar_visible = False
        else:
            if not self._scrollbar_visible:
                self._scrollbar.grid()
                self._scrollbar_visible = True

    def focus_widget(self) -> None:
        """Set keyboard focus to the treeview."""
        self._tree.focus_set()
