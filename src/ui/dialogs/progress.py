"""Transfer progress dialog."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.transfer_operation import TransferOperation


class ProgressDialog(tk.Toplevel):
    """Modal dialog showing transfer progress with cancel button."""

    def __init__(
        self,
        parent: tk.Widget,
        operation: TransferOperation,
        on_cancel: callable | None = None,
    ) -> None:
        super().__init__(parent)
        self.title(f"{'Copying' if operation.operation_type.value == 'copy' else 'Moving'} Files")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self._operation = operation
        self._on_cancel = on_cancel

        self._build_ui()
        self._center_on_parent(parent)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Current file
        self._file_var = tk.StringVar(value="Preparing...")
        ttk.Label(frame, textvariable=self._file_var, anchor=tk.W).pack(
            fill=tk.X, pady=(0, 5)
        )

        # Overall progress bar
        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(
            frame, variable=self._progress_var, maximum=100, length=350
        )
        self._progress_bar.pack(fill=tk.X, pady=(0, 5))

        # Stats
        self._stats_var = tk.StringVar(value="0 / 0 files")
        ttk.Label(frame, textvariable=self._stats_var, anchor=tk.W).pack(
            fill=tk.X, pady=(0, 10)
        )

        # Cancel button
        ttk.Button(frame, text="Cancel", command=self._on_cancel_click).pack()

    def update_progress(self, operation: TransferOperation) -> None:
        """Update the dialog with current operation state."""
        self._file_var.set(f"Current: {operation.current_file}")
        self._progress_var.set(operation.progress_percent)
        self._stats_var.set(
            f"{operation.files_completed} / {operation.files_total} files"
        )
        self.update_idletasks()

    def finish(self) -> None:
        """Close the dialog on completion."""
        self._progress_var.set(100)
        self._file_var.set("Complete!")
        self.after(800, self.destroy)

    def _on_cancel_click(self) -> None:
        if self._on_cancel:
            self._on_cancel()
        self.destroy()

    def _center_on_parent(self, parent: tk.Widget) -> None:
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - w // 2}+{py - h // 2}")
