"""File conflict resolution dialog."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.models import ConflictResolution


class ConflictDialog(tk.Toplevel):
    """Modal dialog for resolving file conflicts at destination."""

    def __init__(
        self,
        parent: tk.Widget,
        source_name: str,
        dest_name: str,
    ) -> None:
        super().__init__(parent)
        self.title("File Already Exists")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.result: ConflictResolution = ConflictResolution.SKIP
        self.apply_to_all: bool = False

        self._build_ui(source_name, dest_name)
        self._center_on_parent(parent)
        self.wait_window()

    def _build_ui(self, source_name: str, dest_name: str) -> None:
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="A file with the same name already exists at the destination.",
            font=("TkDefaultFont", 11, "bold"),
        ).pack(pady=(0, 10))

        ttk.Label(frame, text=f"Source: {source_name}").pack(anchor=tk.W)
        ttk.Label(frame, text=f"Destination: {dest_name}").pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(frame, text="What would you like to do?").pack(pady=(0, 5))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=5)

        ttk.Button(
            btn_frame, text="Overwrite",
            command=lambda: self._choose(ConflictResolution.OVERWRITE),
        ).pack(side=tk.LEFT, padx=3)

        ttk.Button(
            btn_frame, text="Skip",
            command=lambda: self._choose(ConflictResolution.SKIP),
        ).pack(side=tk.LEFT, padx=3)

        ttk.Button(
            btn_frame, text="Rename",
            command=lambda: self._choose(ConflictResolution.RENAME),
        ).pack(side=tk.LEFT, padx=3)

        # Apply to all checkbox
        self._apply_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Apply to all remaining conflicts",
            variable=self._apply_all_var,
        ).pack(pady=(10, 0))

    def _choose(self, resolution: ConflictResolution) -> None:
        self.result = resolution
        self.apply_to_all = self._apply_all_var.get()
        self.destroy()

    def _center_on_parent(self, parent: tk.Widget) -> None:
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - w // 2}+{py - h // 2}")
