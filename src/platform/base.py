"""Abstract base class defining the platform abstraction layer interface.

Every OS-specific backend must subclass ``PlatformService`` and implement
all of its abstract methods so that the rest of the application can
consume platform-dependent behaviour through a single, stable API.
"""

from __future__ import annotations

import abc
from pathlib import Path


class PlatformService(abc.ABC):
    """Contract that each platform-specific implementation must fulfil."""

    # -- filesystem ------------------------------------------------------------

    @abc.abstractmethod
    def get_config_directory(self) -> Path:
        """Return the platform-appropriate configuration directory.

        The directory is created (including parents) if it does not already
        exist.
        """

    # -- keyboard / UI conventions ---------------------------------------------

    @abc.abstractmethod
    def get_modifier_key(self) -> str:
        """Return the human-readable name of the primary modifier key.

        Examples: ``"Cmd"`` on macOS, ``"Ctrl"`` on Windows.
        """

    @abc.abstractmethod
    def get_modifier_symbol(self) -> str:
        """Return the symbolic representation used in menu accelerators.

        Examples: ``"⌘"`` on macOS, ``"Ctrl+"`` on Windows.
        """

    @abc.abstractmethod
    def get_dialog_button_order(self) -> tuple[str, str]:
        """Return the conventional (secondary, primary) button label order.

        macOS convention: ``("Cancel", "OK")``
        Windows convention: ``("OK", "Cancel")``
        """

    # -- appearance ------------------------------------------------------------

    @abc.abstractmethod
    def is_dark_mode(self) -> bool:
        """Return ``True`` if the operating system is using a dark theme."""

    @abc.abstractmethod
    def get_default_font_family(self) -> str:
        """Return the platform's preferred default UI font family name."""

    # -- external actions ------------------------------------------------------

    @abc.abstractmethod
    def open_browser(self, url: str) -> None:
        """Open *url* in the user's default web browser."""

    @abc.abstractmethod
    def open_file_externally(self, path: Path) -> None:
        """Open *path* with the operating system's default application."""

    @abc.abstractmethod
    def reveal_in_finder(self, path: Path) -> None:
        """Reveal *path* in the platform's native file manager."""
