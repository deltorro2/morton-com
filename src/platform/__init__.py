"""Platform detection and factory for OS-specific service implementations.

Call :func:`get_platform` to obtain a :class:`~src.platform.base.PlatformService`
instance appropriate for the current operating system.
"""

from __future__ import annotations

import sys

from src.platform.base import PlatformService


def get_platform() -> PlatformService:
    """Detect the current OS and return the matching platform service.

    * ``darwin``  -> :class:`~src.platform.macos.MacOSPlatform`
    * ``win32``   -> :class:`~src.platform.windows.WindowsPlatform`
    * everything else falls back to the macOS implementation.
    """
    if sys.platform == "darwin":
        from src.platform.macos import MacOSPlatform  # noqa: PLC0415

        return MacOSPlatform()
    elif sys.platform == "win32":
        from src.platform.windows import WindowsPlatform  # noqa: PLC0415

        return WindowsPlatform()
    else:
        # Fallback to macOS-style for Linux/other
        from src.platform.macos import MacOSPlatform  # noqa: PLC0415

        return MacOSPlatform()


__all__ = ["PlatformService", "get_platform"]
