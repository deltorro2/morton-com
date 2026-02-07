"""Unit tests for WindowsPlatform class.

Tests cover Windows-specific platform service implementation including
configuration directory, keyboard modifiers, dark mode detection, and
external file/URL handling.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from src.platform.windows import WindowsPlatform


class TestWindowsPlatformConfigDirectory:
    """Tests for get_config_directory method."""

    def test_uses_appdata_env_var(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """get_config_directory should use APPDATA environment variable."""
        appdata_path = tmp_path / "AppData" / "Roaming"
        appdata_path.mkdir(parents=True)
        monkeypatch.setenv("APPDATA", str(appdata_path))

        # Set up mock winreg before importing
        mock_winreg = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        # Force reimport to pick up the mock
        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()
        config_dir = platform.get_config_directory()

        assert config_dir == appdata_path / "morton-com"

    def test_creates_directory_if_not_exists(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """get_config_directory should create the directory if it does not exist."""
        appdata_path = tmp_path / "AppData" / "Roaming"
        appdata_path.mkdir(parents=True)
        monkeypatch.setenv("APPDATA", str(appdata_path))

        # Set up mock winreg before importing
        mock_winreg = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        # Force reimport to pick up the mock
        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()
        config_dir = platform.get_config_directory()

        assert config_dir.exists()
        assert config_dir.is_dir()


class TestWindowsPlatformModifierKeys:
    """Tests for keyboard modifier methods."""

    def test_get_modifier_key_returns_ctrl(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_modifier_key should return 'Ctrl' on Windows."""
        mock_winreg = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()

        assert platform.get_modifier_key() == "Ctrl"

    def test_get_modifier_symbol_returns_ctrl_plus(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_modifier_symbol should return 'Ctrl+' on Windows."""
        mock_winreg = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()

        assert platform.get_modifier_symbol() == "Ctrl+"


class TestWindowsPlatformDialogButtonOrder:
    """Tests for dialog button order method."""

    def test_get_dialog_button_order_returns_ok_cancel(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_dialog_button_order should return ('OK', 'Cancel') on Windows."""
        mock_winreg = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()
        button_order = platform.get_dialog_button_order()

        assert button_order == ("OK", "Cancel")


class TestWindowsPlatformDarkMode:
    """Tests for is_dark_mode method."""

    def test_is_dark_mode_returns_true_when_registry_value_is_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """is_dark_mode should return True when AppsUseLightTheme registry value is 0."""
        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = (0, 1)  # value=0 means dark mode
        mock_winreg.HKEY_CURRENT_USER = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()
        result = platform.is_dark_mode()

        assert result is True
        mock_winreg.OpenKey.assert_called_once()
        mock_winreg.QueryValueEx.assert_called_once_with(
            mock_key, "AppsUseLightTheme"
        )
        mock_winreg.CloseKey.assert_called_once_with(mock_key)

    def test_is_dark_mode_returns_false_when_registry_value_is_one(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """is_dark_mode should return False when AppsUseLightTheme registry value is 1."""
        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = (1, 1)  # value=1 means light mode
        mock_winreg.HKEY_CURRENT_USER = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()
        result = platform.is_dark_mode()

        assert result is False
        mock_winreg.CloseKey.assert_called_once_with(mock_key)

    def test_is_dark_mode_returns_false_on_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """is_dark_mode should return False when registry access raises exception."""
        mock_winreg = MagicMock()
        mock_winreg.OpenKey.side_effect = FileNotFoundError("Registry key not found")
        mock_winreg.HKEY_CURRENT_USER = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()
        result = platform.is_dark_mode()

        assert result is False


class TestWindowsPlatformDefaultFont:
    """Tests for get_default_font_family method."""

    def test_get_default_font_family_returns_segoe_ui(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_default_font_family should return 'Segoe UI' on Windows."""
        mock_winreg = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()

        assert platform.get_default_font_family() == "Segoe UI"


class TestWindowsPlatformOpenBrowser:
    """Tests for open_browser method."""

    def test_open_browser_calls_webbrowser_open(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """open_browser should call webbrowser.open with the provided URL."""
        mock_winreg = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()

        with patch("webbrowser.open") as mock_open:
            platform.open_browser("https://example.com")

            mock_open.assert_called_once_with("https://example.com")


class TestWindowsPlatformOpenFileExternally:
    """Tests for open_file_externally method."""

    def test_open_file_externally_uses_startfile(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """open_file_externally should use os.startfile when available."""
        mock_winreg = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with patch("os.startfile", create=True) as mock_startfile:
            platform.open_file_externally(test_file)

            mock_startfile.assert_called_once_with(str(test_file))

    def test_open_file_externally_falls_back_to_subprocess(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """open_file_externally should fall back to subprocess when startfile unavailable."""
        mock_winreg = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with patch("os.startfile", create=True, side_effect=AttributeError("no startfile")):
            with patch("subprocess.run") as mock_run:
                platform.open_file_externally(test_file)

                mock_run.assert_called_once_with(
                    ["start", str(test_file)], shell=True, check=False
                )


class TestWindowsPlatformRevealInFinder:
    """Tests for reveal_in_finder method."""

    def test_reveal_in_finder_calls_explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """reveal_in_finder should call explorer with /select, flag."""
        mock_winreg = MagicMock()
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        if "src.platform.windows" in sys.modules:
            del sys.modules["src.platform.windows"]

        from src.platform.windows import WindowsPlatform

        platform = WindowsPlatform()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with patch("subprocess.run") as mock_run:
            platform.reveal_in_finder(test_file)

            mock_run.assert_called_once_with(
                ["explorer", "/select,", str(test_file)], check=False
            )
