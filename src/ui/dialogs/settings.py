"""Settings dialog for application preferences."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.config_manager import ConfigManager


class SettingsDialog(tk.Toplevel):
    """Modal dialog for editing application settings."""

    def __init__(self, parent: tk.Widget, config_manager: ConfigManager) -> None:
        super().__init__(parent)
        self.title("Settings")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self._config_mgr = config_manager
        self._config = config_manager.config
        self._build_ui()

        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - self.winfo_width() // 2}+{py - self.winfo_height() // 2}")

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Max concurrent transfers
        row1 = ttk.Frame(frame)
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="Max concurrent transfers:").pack(side=tk.LEFT)
        self._concurrent_var = tk.IntVar(value=self._config.max_concurrent_transfers)
        ttk.Spinbox(
            row1, from_=1, to=10, textvariable=self._concurrent_var, width=5,
        ).pack(side=tk.RIGHT)

        # Show hidden files
        self._hidden_var = tk.BooleanVar(value=self._config.show_hidden_files)
        ttk.Checkbutton(
            frame, text="Show hidden files", variable=self._hidden_var,
        ).pack(anchor=tk.W, pady=5)

        # Confirm delete
        self._confirm_var = tk.BooleanVar(value=self._config.confirm_delete)
        ttk.Checkbutton(
            frame, text="Confirm before delete", variable=self._confirm_var,
        ).pack(anchor=tk.W, pady=5)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(15, 0))
        ttk.Button(btn_frame, text="Save", command=self._on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _on_save(self) -> None:
        self._config.max_concurrent_transfers = max(1, min(10, self._concurrent_var.get()))
        self._config.show_hidden_files = self._hidden_var.get()
        self._config.confirm_delete = self._confirm_var.get()
        self._config_mgr.save(self._config)
        self.destroy()
