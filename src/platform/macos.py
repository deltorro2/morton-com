"""macOS implementation of the platform abstraction layer.

Uses ``defaults read``, ``open``, and ``webbrowser`` to provide
native macOS behaviour for configuration paths, dark-mode detection,
and external file/URL handling.
"""

from __future__ import annotations

import subprocess
import webbrowser
from pathlib import Path

from src.platform.base import PlatformService


class MacOSPlatform(PlatformService):
    """Platform service tailored to macOS (Darwin)."""

    # -- filesystem ------------------------------------------------------------

    def get_config_directory(self) -> Path:
        config_dir = Path.home() / ".config" / "morton-com"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    # -- keyboard / UI conventions ---------------------------------------------

    def get_modifier_key(self) -> str:
        return "Cmd"

    def get_modifier_symbol(self) -> str:
        return "⌘"

    def get_dialog_button_order(self) -> tuple[str, str]:
        return ("Cancel", "OK")

    # -- appearance ------------------------------------------------------------

    def is_dark_mode(self) -> bool:
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                check=False,
            )
            return "Dark" in result.stdout
        except Exception:  # noqa: BLE001
            return False

    def get_default_font_family(self) -> str:
        return "Helvetica Neue"

    # -- external actions ------------------------------------------------------

    def open_browser(self, url: str) -> None:
        webbrowser.open(url)

    def open_file_externally(self, path: Path) -> None:
        subprocess.run(["open", str(path)], check=False)

    def reveal_in_finder(self, path: Path) -> None:
        subprocess.run(["open", "-R", str(path)], check=False)
