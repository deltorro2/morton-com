"""Windows implementation of the platform abstraction layer.

Uses the Windows registry (``winreg``), ``os.startfile``, and
``explorer`` to provide native Windows behaviour for configuration
paths, dark-mode detection, and external file/URL handling.
"""

from __future__ import annotations

import os
import subprocess
import webbrowser
from pathlib import Path

from src.platform.base import PlatformService


class WindowsPlatform(PlatformService):
    """Platform service tailored to Windows (win32)."""

    # -- filesystem ------------------------------------------------------------

    def get_config_directory(self) -> Path:
        base = os.environ.get("APPDATA", "~")
        config_dir = Path(base).expanduser() / "morton-com"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    # -- keyboard / UI conventions ---------------------------------------------

    def get_modifier_key(self) -> str:
        return "Ctrl"

    def get_modifier_symbol(self) -> str:
        return "Ctrl+"

    def get_dialog_button_order(self) -> tuple[str, str]:
        return ("OK", "Cancel")

    # -- appearance ------------------------------------------------------------

    def is_dark_mode(self) -> bool:
        try:
            import winreg  # noqa: PLC0415

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return value == 0
        except Exception:  # noqa: BLE001
            return False

    def get_default_font_family(self) -> str:
        return "Segoe UI"

    # -- external actions ------------------------------------------------------

    def open_browser(self, url: str) -> None:
        webbrowser.open(url)

    def open_file_externally(self, path: Path) -> None:
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except AttributeError:
            # os.startfile is only available on Windows; graceful no-op
            # if this class is ever instantiated on another platform.
            subprocess.run(["start", str(path)], shell=True, check=False)

    def reveal_in_finder(self, path: Path) -> None:
        subprocess.run(["explorer", "/select,", str(path)], check=False)
