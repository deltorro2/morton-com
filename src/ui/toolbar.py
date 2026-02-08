"""Toolbar widget with action buttons for file operations."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.platform import get_platform


class Toolbar(ttk.Frame):
    """Action toolbar with Copy, Move, Delete, Properties, and Refresh buttons."""

    def __init__(
        self,
        parent: tk.Widget,
        on_copy: callable | None = None,
        on_move: callable | None = None,
        on_delete: callable | None = None,
        on_properties: callable | None = None,
        on_refresh: callable | None = None,
        on_settings: callable | None = None,
    ) -> None:
        super().__init__(parent)
        self._callbacks = {
            "copy": on_copy,
            "move": on_move,
            "delete": on_delete,
            "properties": on_properties,
            "refresh": on_refresh,
            "settings": on_settings,
        }

        platform = get_platform()
        mod = platform.get_modifier_symbol()

        self._buttons: dict[str, ttk.Button] = {}

        btn_defs = [
            ("copy", f"Copy ({mod}C)", "copy"),
            ("move", f"Move ({mod}X)", "move"),
            ("delete", "Delete (Del)", "delete"),
            ("properties", f"Properties ({mod}I)", "properties"),
            ("refresh", f"Refresh ({mod}R)", "refresh"),
        ]

        for name, label, callback_key in btn_defs:
            btn = ttk.Button(
                self,
                text=label,
                command=lambda k=callback_key: self._invoke(k),
                takefocus=False,
            )
            btn.pack(side=tk.LEFT, padx=2, pady=2)
            self._buttons[name] = btn

        # Settings button on the right
        if on_settings:
            settings_btn = ttk.Button(
                self,
                text="Settings",
                command=lambda: self._invoke("settings"),
                takefocus=False,
            )
            settings_btn.pack(side=tk.RIGHT, padx=2, pady=2)
            self._buttons["settings"] = settings_btn

    def _invoke(self, key: str) -> None:
        cb = self._callbacks.get(key)
        if cb:
            cb()

    def set_actions_enabled(self, has_selection: bool) -> None:
        """Enable/disable action buttons based on selection state."""
        state = "!disabled" if has_selection else "disabled"
        for name in ("copy", "move", "delete", "properties"):
            if name in self._buttons:
                self._buttons[name].state([state])
