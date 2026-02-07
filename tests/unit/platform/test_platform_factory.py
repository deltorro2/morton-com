"""Unit tests for platform factory function get_platform().

Tests verify that get_platform() returns the correct platform service
implementation based on sys.platform value.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.platform import get_platform
from src.platform.base import PlatformService
from src.platform.macos import MacOSPlatform
from src.platform.windows import WindowsPlatform


class TestGetPlatform:
    """Tests for the get_platform() factory function."""

    def test_get_platform_returns_macos_on_darwin(self) -> None:
        """get_platform() returns MacOSPlatform when sys.platform is 'darwin'."""
        with patch("src.platform.sys.platform", "darwin"):
            result = get_platform()

        assert isinstance(result, MacOSPlatform)

    def test_get_platform_returns_windows_on_win32(self) -> None:
        """get_platform() returns WindowsPlatform when sys.platform is 'win32'."""
        with patch("src.platform.sys.platform", "win32"):
            result = get_platform()

        assert isinstance(result, WindowsPlatform)

    def test_get_platform_returns_macos_on_linux_fallback(self) -> None:
        """get_platform() returns MacOSPlatform as fallback for 'linux'."""
        with patch("src.platform.sys.platform", "linux"):
            result = get_platform()

        assert isinstance(result, MacOSPlatform)

    def test_get_platform_returns_platform_service_instance(self) -> None:
        """get_platform() always returns an instance of PlatformService."""
        platforms = ["darwin", "win32", "linux", "freebsd"]

        for platform in platforms:
            with patch("src.platform.sys.platform", platform):
                result = get_platform()

            assert isinstance(result, PlatformService), (
                f"Expected PlatformService instance for platform '{platform}'"
            )
