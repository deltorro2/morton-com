"""New Folder dialog for creating directories."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class NewFolderDialog(tk.Toplevel):
    """Modal dialog that prompts the user for a new folder name.

    After the dialog closes, :attr:`folder_name` contains the entered
    name (stripped) or ``None`` if the user cancelled.
    """

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.title("New Folder")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.folder_name: str | None = None

        self._build_ui()
        self._center_on_parent(parent)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.wait_window()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Enter folder name:").pack(anchor=tk.W, pady=(0, 5))

        self._entry = ttk.Entry(frame, width=40)
        self._entry.pack(fill=tk.X, pady=(0, 10))
        self._entry.focus_set()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="OK", command=self._ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())

    def _ok(self) -> None:
        name = self._entry.get().strip()
        if not name:
            return
        self.folder_name = name
        self.grab_release()
        self.destroy()

    def _cancel(self) -> None:
        self.folder_name = None
        self.grab_release()
        self.destroy()

    def _center_on_parent(self, parent: tk.Widget) -> None:
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - w // 2}+{py - h // 2}")
