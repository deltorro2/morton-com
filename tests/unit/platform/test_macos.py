"""Unit tests for the MacOSPlatform class.

Tests cover:
- get_config_directory returns correct path and creates directory if needed
- get_modifier_key returns "Cmd"
- get_modifier_symbol returns the Command symbol
- get_dialog_button_order returns macOS button order convention
- is_dark_mode detection via subprocess
- get_default_font_family returns macOS system font
- open_browser calls webbrowser.open
- open_file_externally calls subprocess with "open"
- reveal_in_finder calls subprocess with "open -R"
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from src.platform.base import PlatformService
from src.platform.macos import MacOSPlatform

if TYPE_CHECKING:
    from pytest import MonkeyPatch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def macos_platform() -> MacOSPlatform:
    """Create a MacOSPlatform instance for testing."""
    return MacOSPlatform()


@pytest.fixture
def mock_home_dir(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    """Mock Path.home() to return a temporary directory."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Test: MacOSPlatform inherits from PlatformService
# ---------------------------------------------------------------------------


class TestMacOSPlatformInheritance:
    """Tests for MacOSPlatform class hierarchy."""

    def test_macos_platform_is_platform_service_subclass(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that MacOSPlatform is a subclass of PlatformService."""
        assert isinstance(macos_platform, PlatformService)


# ---------------------------------------------------------------------------
# Test: get_config_directory
# ---------------------------------------------------------------------------


class TestGetConfigDirectory:
    """Tests for the get_config_directory method."""

    def test_get_config_directory_returns_correct_path(
        self, macos_platform: MacOSPlatform, mock_home_dir: Path
    ) -> None:
        """Test that get_config_directory returns ~/.config/morton-com."""
        expected_path = mock_home_dir / ".config" / "morton-com"

        result = macos_platform.get_config_directory()

        assert result == expected_path

    def test_get_config_directory_creates_directory_if_not_exists(
        self, macos_platform: MacOSPlatform, mock_home_dir: Path
    ) -> None:
        """Test that get_config_directory creates the directory if it does not exist."""
        config_path = mock_home_dir / ".config" / "morton-com"
        assert not config_path.exists()

        result = macos_platform.get_config_directory()

        assert result.exists()
        assert result.is_dir()

    def test_get_config_directory_succeeds_when_directory_already_exists(
        self, macos_platform: MacOSPlatform, mock_home_dir: Path
    ) -> None:
        """Test that get_config_directory works when directory already exists."""
        config_path = mock_home_dir / ".config" / "morton-com"
        config_path.mkdir(parents=True)
        assert config_path.exists()

        result = macos_platform.get_config_directory()

        assert result == config_path
        assert result.exists()


# ---------------------------------------------------------------------------
# Test: get_modifier_key
# ---------------------------------------------------------------------------


class TestGetModifierKey:
    """Tests for the get_modifier_key method."""

    def test_get_modifier_key_returns_cmd(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that get_modifier_key returns 'Cmd' for macOS."""
        result = macos_platform.get_modifier_key()

        assert result == "Cmd"


# ---------------------------------------------------------------------------
# Test: get_modifier_symbol
# ---------------------------------------------------------------------------


class TestGetModifierSymbol:
    """Tests for the get_modifier_symbol method."""

    def test_get_modifier_symbol_returns_command_symbol(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that get_modifier_symbol returns the Command symbol for macOS."""
        result = macos_platform.get_modifier_symbol()

        assert result == "\u2318"  # Unicode for Command symbol


# ---------------------------------------------------------------------------
# Test: get_dialog_button_order
# ---------------------------------------------------------------------------


class TestGetDialogButtonOrder:
    """Tests for the get_dialog_button_order method."""

    def test_get_dialog_button_order_returns_cancel_ok_tuple(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that get_dialog_button_order returns ('Cancel', 'OK') for macOS."""
        result = macos_platform.get_dialog_button_order()

        assert result == ("Cancel", "OK")

    def test_get_dialog_button_order_returns_tuple(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that get_dialog_button_order returns a tuple type."""
        result = macos_platform.get_dialog_button_order()

        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Test: is_dark_mode
# ---------------------------------------------------------------------------


class TestIsDarkMode:
    """Tests for the is_dark_mode method."""

    def test_is_dark_mode_returns_true_when_subprocess_output_contains_dark(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that is_dark_mode returns True when output contains 'Dark'."""
        mock_result = MagicMock()
        mock_result.stdout = "Dark\n"
        mock_result.returncode = 0

        with patch("src.platform.macos.subprocess.run", return_value=mock_result) as mock_run:
            result = macos_platform.is_dark_mode()

            assert result is True
            mock_run.assert_called_once_with(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_is_dark_mode_returns_false_when_no_dark_in_output(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that is_dark_mode returns False when output does not contain 'Dark'."""
        mock_result = MagicMock()
        mock_result.stdout = "Light\n"
        mock_result.returncode = 0

        with patch("src.platform.macos.subprocess.run", return_value=mock_result):
            result = macos_platform.is_dark_mode()

            assert result is False

    def test_is_dark_mode_returns_false_when_stdout_is_empty(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that is_dark_mode returns False when stdout is empty."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 1

        with patch("src.platform.macos.subprocess.run", return_value=mock_result):
            result = macos_platform.is_dark_mode()

            assert result is False

    def test_is_dark_mode_returns_false_on_exception(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that is_dark_mode returns False when an exception occurs."""
        with patch(
            "src.platform.macos.subprocess.run",
            side_effect=subprocess.SubprocessError("Command failed"),
        ):
            result = macos_platform.is_dark_mode()

            assert result is False

    def test_is_dark_mode_returns_false_on_file_not_found_error(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that is_dark_mode returns False when defaults command not found."""
        with patch(
            "src.platform.macos.subprocess.run",
            side_effect=FileNotFoundError("defaults not found"),
        ):
            result = macos_platform.is_dark_mode()

            assert result is False


# ---------------------------------------------------------------------------
# Test: get_default_font_family
# ---------------------------------------------------------------------------


class TestGetDefaultFontFamily:
    """Tests for the get_default_font_family method."""

    def test_get_default_font_family_returns_helvetica_neue(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that get_default_font_family returns 'Helvetica Neue' for macOS."""
        result = macos_platform.get_default_font_family()

        assert result == "Helvetica Neue"


# ---------------------------------------------------------------------------
# Test: open_browser
# ---------------------------------------------------------------------------


class TestOpenBrowser:
    """Tests for the open_browser method."""

    def test_open_browser_calls_webbrowser_open(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that open_browser calls webbrowser.open with the given URL."""
        test_url = "https://example.com"

        with patch("src.platform.macos.webbrowser.open") as mock_open:
            macos_platform.open_browser(test_url)

            mock_open.assert_called_once_with(test_url)

    def test_open_browser_passes_url_exactly(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that open_browser passes the URL exactly as provided."""
        complex_url = "https://example.com/path?query=value&other=123#anchor"

        with patch("src.platform.macos.webbrowser.open") as mock_open:
            macos_platform.open_browser(complex_url)

            mock_open.assert_called_once_with(complex_url)


# ---------------------------------------------------------------------------
# Test: open_file_externally
# ---------------------------------------------------------------------------


class TestOpenFileExternally:
    """Tests for the open_file_externally method."""

    def test_open_file_externally_calls_subprocess_with_open_command(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that open_file_externally calls subprocess with 'open' command."""
        test_path = Path("/Users/test/document.pdf")

        with patch("src.platform.macos.subprocess.run") as mock_run:
            macos_platform.open_file_externally(test_path)

            mock_run.assert_called_once_with(
                ["open", str(test_path)], check=False
            )

    def test_open_file_externally_converts_path_to_string(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that open_file_externally converts Path object to string."""
        test_path = Path("/Users/test/file with spaces.txt")

        with patch("src.platform.macos.subprocess.run") as mock_run:
            macos_platform.open_file_externally(test_path)

            call_args = mock_run.call_args[0][0]
            assert call_args[1] == "/Users/test/file with spaces.txt"
            assert isinstance(call_args[1], str)


# ---------------------------------------------------------------------------
# Test: reveal_in_finder
# ---------------------------------------------------------------------------


class TestRevealInFinder:
    """Tests for the reveal_in_finder method."""

    def test_reveal_in_finder_calls_subprocess_with_open_r_flag(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that reveal_in_finder calls subprocess with 'open -R' command."""
        test_path = Path("/Users/test/document.pdf")

        with patch("src.platform.macos.subprocess.run") as mock_run:
            macos_platform.reveal_in_finder(test_path)

            mock_run.assert_called_once_with(
                ["open", "-R", str(test_path)], check=False
            )

    def test_reveal_in_finder_converts_path_to_string(
        self, macos_platform: MacOSPlatform
    ) -> None:
        """Test that reveal_in_finder converts Path object to string."""
        test_path = Path("/Users/test/folder/file.txt")

        with patch("src.platform.macos.subprocess.run") as mock_run:
            macos_platform.reveal_in_finder(test_path)

            call_args = mock_run.call_args[0][0]
            assert call_args[2] == "/Users/test/folder/file.txt"
            assert isinstance(call_args[2], str)
