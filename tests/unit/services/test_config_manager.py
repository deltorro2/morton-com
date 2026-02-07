"""Unit tests for ConfigManager service.

Tests cover configuration file loading, saving, project management,
and error handling for malformed or missing configuration files.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import Configuration, ProjectConfig, WindowState
from src.errors import ConfigurationError
from src.services.config_manager import ConfigManager


class TestConfigManagerInit:
    """Tests for ConfigManager initialization."""

    def test_init_with_explicit_config_dir(self, tmp_path: Path) -> None:
        """ConfigManager should use the provided config_dir when explicitly set."""
        config_dir = tmp_path / "custom_config"
        config_dir.mkdir()

        manager = ConfigManager(config_dir=config_dir)

        assert manager.get_config_directory() == config_dir

    def test_init_with_none_uses_platform_config_directory(
        self, tmp_path: Path
    ) -> None:
        """ConfigManager should use platform's config directory when config_dir is None."""
        mock_platform = MagicMock()
        mock_platform.get_config_directory.return_value = tmp_path / "platform_config"

        with patch("src.services.config_manager.get_platform", return_value=mock_platform):
            manager = ConfigManager(config_dir=None)

        mock_platform.get_config_directory.assert_called_once()
        assert manager.get_config_directory() == tmp_path / "platform_config"


class TestConfigManagerLoad:
    """Tests for ConfigManager.load() method."""

    def test_load_with_missing_files_returns_defaults(self, tmp_path: Path) -> None:
        """load() should return default Configuration when files do not exist."""
        config_dir = tmp_path / "empty_config"
        config_dir.mkdir()

        manager = ConfigManager(config_dir=config_dir)
        config = manager.config

        assert config.projects == []
        assert config.max_concurrent_transfers == 3
        assert config.show_hidden_files is False
        assert config.confirm_delete is True
        assert config.window_state is None

    def test_load_with_valid_json_files(self, tmp_path: Path) -> None:
        """load() should correctly parse valid settings.json and projects.json."""
        config_dir = tmp_path / "valid_config"
        config_dir.mkdir()

        settings_data = {
            "max_concurrent_transfers": 5,
            "show_hidden_files": True,
            "confirm_delete": False,
            "window_state": {"width": 1600, "height": 900, "x": 50, "y": 75},
        }
        projects_data = {
            "projects": [
                {"project_id": "proj-1", "display_name": "Project One", "default": True},
                {"project_id": "proj-2", "display_name": "", "default": False},
            ]
        }

        (config_dir / "settings.json").write_text(
            json.dumps(settings_data), encoding="utf-8"
        )
        (config_dir / "projects.json").write_text(
            json.dumps(projects_data), encoding="utf-8"
        )

        manager = ConfigManager(config_dir=config_dir)
        config = manager.config

        assert config.max_concurrent_transfers == 5
        assert config.show_hidden_files is True
        assert config.confirm_delete is False
        assert config.window_state is not None
        assert config.window_state.width == 1600
        assert config.window_state.height == 900
        assert config.window_state.x == 50
        assert config.window_state.y == 75
        assert len(config.projects) == 2
        assert config.projects[0].project_id == "proj-1"
        assert config.projects[0].display_name == "Project One"
        assert config.projects[0].default is True
        assert config.projects[1].project_id == "proj-2"

    def test_load_with_malformed_json_raises_configuration_error(
        self, tmp_path: Path
    ) -> None:
        """load() should raise ConfigurationError for malformed JSON."""
        config_dir = tmp_path / "malformed_config"
        config_dir.mkdir()

        (config_dir / "settings.json").write_text(
            "{ invalid json syntax", encoding="utf-8"
        )

        with pytest.raises(ConfigurationError) as exc_info:
            ConfigManager(config_dir=config_dir)

        assert "invalid JSON" in exc_info.value.user_message

    def test_load_with_non_dict_json_raises_configuration_error(
        self, tmp_path: Path
    ) -> None:
        """load() should raise ConfigurationError when JSON is not an object."""
        config_dir = tmp_path / "array_config"
        config_dir.mkdir()

        (config_dir / "settings.json").write_text(
            json.dumps(["not", "a", "dict"]), encoding="utf-8"
        )

        with pytest.raises(ConfigurationError) as exc_info:
            ConfigManager(config_dir=config_dir)

        assert "unexpected format" in exc_info.value.user_message

    def test_load_creates_config_directory_if_missing(self, tmp_path: Path) -> None:
        """load() should create the config directory if it does not exist."""
        config_dir = tmp_path / "nonexistent" / "nested" / "config"

        manager = ConfigManager(config_dir=config_dir)

        assert config_dir.exists()
        assert config_dir.is_dir()
        assert manager.config is not None


class TestConfigManagerSave:
    """Tests for ConfigManager.save() method."""

    def test_save_writes_to_settings_and_projects_files(self, tmp_path: Path) -> None:
        """save() should write to both settings.json and projects.json."""
        config_dir = tmp_path / "save_config"
        config_dir.mkdir()

        manager = ConfigManager(config_dir=config_dir)
        config = Configuration(
            projects=[ProjectConfig(project_id="my-proj", display_name="My Project")],
            max_concurrent_transfers=10,
            show_hidden_files=True,
            confirm_delete=False,
            window_state=WindowState(width=800, height=600, x=10, y=20),
        )
        manager.save(config)

        settings_path = config_dir / "settings.json"
        projects_path = config_dir / "projects.json"

        assert settings_path.exists()
        assert projects_path.exists()

        settings_data = json.loads(settings_path.read_text(encoding="utf-8"))
        projects_data = json.loads(projects_path.read_text(encoding="utf-8"))

        assert settings_data["max_concurrent_transfers"] == 10
        assert settings_data["show_hidden_files"] is True
        assert settings_data["confirm_delete"] is False
        assert settings_data["window_state"]["width"] == 800
        assert projects_data["projects"][0]["project_id"] == "my-proj"
        assert projects_data["projects"][0]["display_name"] == "My Project"

    def test_save_creates_directory_if_needed(self, tmp_path: Path) -> None:
        """save() should create the config directory if it does not exist."""
        config_dir = tmp_path / "new_save_dir"

        manager = ConfigManager(config_dir=config_dir)
        new_config = Configuration(max_concurrent_transfers=7)
        manager.save(new_config)

        assert config_dir.exists()
        assert (config_dir / "settings.json").exists()
        assert (config_dir / "projects.json").exists()

    def test_save_with_oserror_raises_configuration_error(
        self, tmp_path: Path
    ) -> None:
        """save() should raise ConfigurationError when file write fails."""
        config_dir = tmp_path / "readonly_config"
        config_dir.mkdir()

        manager = ConfigManager(config_dir=config_dir)

        with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
            with pytest.raises(ConfigurationError) as exc_info:
                manager.save(Configuration())

        assert "Could not save" in exc_info.value.user_message


class TestConfigManagerProjectOperations:
    """Tests for ConfigManager project management methods."""

    def test_add_project_appends_and_saves(self, tmp_path: Path) -> None:
        """add_project() should append the project and persist to disk."""
        config_dir = tmp_path / "add_proj_config"
        config_dir.mkdir()

        manager = ConfigManager(config_dir=config_dir)
        new_project = ProjectConfig(
            project_id="new-proj", display_name="New Project", default=True
        )
        manager.add_project(new_project)

        assert len(manager.config.projects) == 1
        assert manager.config.projects[0].project_id == "new-proj"

        # Verify it was persisted
        projects_data = json.loads(
            (config_dir / "projects.json").read_text(encoding="utf-8")
        )
        assert len(projects_data["projects"]) == 1
        assert projects_data["projects"][0]["project_id"] == "new-proj"

    def test_remove_project_removes_by_id_and_saves(self, tmp_path: Path) -> None:
        """remove_project() should remove the project by ID and persist to disk."""
        config_dir = tmp_path / "remove_proj_config"
        config_dir.mkdir()

        projects_data = {
            "projects": [
                {"project_id": "keep-me", "display_name": "Keep", "default": False},
                {"project_id": "remove-me", "display_name": "Remove", "default": False},
            ]
        }
        (config_dir / "projects.json").write_text(
            json.dumps(projects_data), encoding="utf-8"
        )

        manager = ConfigManager(config_dir=config_dir)
        assert len(manager.config.projects) == 2

        manager.remove_project("remove-me")

        assert len(manager.config.projects) == 1
        assert manager.config.projects[0].project_id == "keep-me"

        # Verify it was persisted
        persisted_data = json.loads(
            (config_dir / "projects.json").read_text(encoding="utf-8")
        )
        assert len(persisted_data["projects"]) == 1
        assert persisted_data["projects"][0]["project_id"] == "keep-me"

    def test_get_projects_returns_list_copy(self, tmp_path: Path) -> None:
        """get_projects() should return a copy, not the internal list."""
        config_dir = tmp_path / "projects_copy_config"
        config_dir.mkdir()

        projects_data = {
            "projects": [
                {"project_id": "proj-1", "display_name": "", "default": False},
            ]
        }
        (config_dir / "projects.json").write_text(
            json.dumps(projects_data), encoding="utf-8"
        )

        manager = ConfigManager(config_dir=config_dir)
        projects = manager.get_projects()

        # Modify returned list
        projects.append(ProjectConfig(project_id="proj-2"))

        # Original should be unchanged
        assert len(manager.get_projects()) == 1


class TestConfigManagerProperties:
    """Tests for ConfigManager properties."""

    def test_config_property_returns_configuration(self, tmp_path: Path) -> None:
        """config property should return the current Configuration instance."""
        config_dir = tmp_path / "prop_config"
        config_dir.mkdir()

        manager = ConfigManager(config_dir=config_dir)
        config = manager.config

        assert isinstance(config, Configuration)
        assert config is manager.config  # Same instance

    def test_get_config_directory_returns_path(self, tmp_path: Path) -> None:
        """get_config_directory() should return the configured path."""
        config_dir = tmp_path / "dir_config"
        config_dir.mkdir()

        manager = ConfigManager(config_dir=config_dir)

        assert manager.get_config_directory() == config_dir
        assert isinstance(manager.get_config_directory(), Path)


class TestConfigManagerParsing:
    """Tests for ConfigManager parsing methods (tested indirectly)."""

    def test_parse_projects_handles_invalid_entries_gracefully(
        self, tmp_path: Path
    ) -> None:
        """_parse_projects should skip invalid entries without raising errors."""
        config_dir = tmp_path / "invalid_entries_config"
        config_dir.mkdir()

        projects_data = {
            "projects": [
                {"project_id": "valid-proj", "display_name": "Valid", "default": True},
                "not a dict",  # Invalid: not a dict
                {"display_name": "No ID"},  # Invalid: missing project_id
                {"project_id": "", "display_name": "Empty ID"},  # Invalid: empty ID
                {"project_id": 123, "display_name": "Numeric ID"},  # Invalid: non-string ID
                None,  # Invalid: null
                {"project_id": "another-valid", "display_name": "Also Valid"},
            ]
        }
        (config_dir / "projects.json").write_text(
            json.dumps(projects_data), encoding="utf-8"
        )

        manager = ConfigManager(config_dir=config_dir)
        projects = manager.config.projects

        assert len(projects) == 2
        assert projects[0].project_id == "valid-proj"
        assert projects[1].project_id == "another-valid"

    def test_parse_projects_handles_non_list_projects_key(
        self, tmp_path: Path
    ) -> None:
        """_parse_projects should return empty list when 'projects' is not a list."""
        config_dir = tmp_path / "non_list_projects"
        config_dir.mkdir()

        projects_data = {"projects": "not a list"}
        (config_dir / "projects.json").write_text(
            json.dumps(projects_data), encoding="utf-8"
        )

        manager = ConfigManager(config_dir=config_dir)

        assert manager.config.projects == []

    def test_parse_settings_handles_missing_keys_with_defaults(
        self, tmp_path: Path
    ) -> None:
        """_parse_settings should use defaults for missing keys."""
        config_dir = tmp_path / "partial_settings"
        config_dir.mkdir()

        settings_data = {"max_concurrent_transfers": 7}  # Only one key set
        (config_dir / "settings.json").write_text(
            json.dumps(settings_data), encoding="utf-8"
        )

        manager = ConfigManager(config_dir=config_dir)
        config = manager.config

        assert config.max_concurrent_transfers == 7
        assert config.show_hidden_files is False  # Default
        assert config.confirm_delete is True  # Default
        assert config.window_state is None  # Default


class TestConfigManagerWindowState:
    """Tests for window state parsing and serialization."""

    def test_window_state_parsing(self, tmp_path: Path) -> None:
        """Window state should be correctly parsed from settings.json."""
        config_dir = tmp_path / "window_state_config"
        config_dir.mkdir()

        settings_data = {
            "window_state": {"width": 1920, "height": 1080, "x": 0, "y": 0}
        }
        (config_dir / "settings.json").write_text(
            json.dumps(settings_data), encoding="utf-8"
        )

        manager = ConfigManager(config_dir=config_dir)
        ws = manager.config.window_state

        assert ws is not None
        assert ws.width == 1920
        assert ws.height == 1080
        assert ws.x == 0
        assert ws.y == 0

    def test_window_state_partial_parsing_uses_defaults(self, tmp_path: Path) -> None:
        """Window state should use defaults for missing fields."""
        config_dir = tmp_path / "partial_window_config"
        config_dir.mkdir()

        settings_data = {"window_state": {"width": 1600}}  # Only width specified
        (config_dir / "settings.json").write_text(
            json.dumps(settings_data), encoding="utf-8"
        )

        manager = ConfigManager(config_dir=config_dir)
        ws = manager.config.window_state

        assert ws is not None
        assert ws.width == 1600
        assert ws.height == 800  # Default
        assert ws.x == 100  # Default
        assert ws.y == 100  # Default

    def test_window_state_none_when_not_present(self, tmp_path: Path) -> None:
        """window_state should be None when not present in settings."""
        config_dir = tmp_path / "no_window_config"
        config_dir.mkdir()

        settings_data = {"max_concurrent_transfers": 3}
        (config_dir / "settings.json").write_text(
            json.dumps(settings_data), encoding="utf-8"
        )

        manager = ConfigManager(config_dir=config_dir)

        assert manager.config.window_state is None

    def test_window_state_serialization_when_present(self, tmp_path: Path) -> None:
        """save() should serialize window_state when present."""
        config_dir = tmp_path / "ws_serialize_config"
        config_dir.mkdir()

        manager = ConfigManager(config_dir=config_dir)
        config = Configuration(
            window_state=WindowState(width=1280, height=720, x=25, y=50)
        )
        manager.save(config)

        settings_data = json.loads(
            (config_dir / "settings.json").read_text(encoding="utf-8")
        )

        assert "window_state" in settings_data
        assert settings_data["window_state"]["width"] == 1280
        assert settings_data["window_state"]["height"] == 720
        assert settings_data["window_state"]["x"] == 25
        assert settings_data["window_state"]["y"] == 50

    def test_window_state_omitted_when_none(self, tmp_path: Path) -> None:
        """save() should not include window_state when it is None."""
        config_dir = tmp_path / "no_ws_config"
        config_dir.mkdir()

        manager = ConfigManager(config_dir=config_dir)
        config = Configuration(window_state=None)
        manager.save(config)

        settings_data = json.loads(
            (config_dir / "settings.json").read_text(encoding="utf-8")
        )

        assert "window_state" not in settings_data


class TestConfigManagerRoundTrip:
    """Tests for round-trip save and load operations."""

    def test_round_trip_preserves_data(self, tmp_path: Path) -> None:
        """Saving and reloading should preserve all configuration data."""
        config_dir = tmp_path / "roundtrip_config"
        config_dir.mkdir()

        original_config = Configuration(
            projects=[
                ProjectConfig(
                    project_id="proj-alpha", display_name="Alpha Project", default=True
                ),
                ProjectConfig(
                    project_id="proj-beta", display_name="Beta Project", default=False
                ),
            ],
            max_concurrent_transfers=8,
            show_hidden_files=True,
            confirm_delete=False,
            window_state=WindowState(width=1440, height=900, x=200, y=150),
        )

        manager = ConfigManager(config_dir=config_dir)
        manager.save(original_config)

        # Create new manager to reload from disk
        manager2 = ConfigManager(config_dir=config_dir)
        loaded_config = manager2.config

        assert len(loaded_config.projects) == 2
        assert loaded_config.projects[0].project_id == "proj-alpha"
        assert loaded_config.projects[0].display_name == "Alpha Project"
        assert loaded_config.projects[0].default is True
        assert loaded_config.projects[1].project_id == "proj-beta"
        assert loaded_config.projects[1].display_name == "Beta Project"
        assert loaded_config.projects[1].default is False
        assert loaded_config.max_concurrent_transfers == 8
        assert loaded_config.show_hidden_files is True
        assert loaded_config.confirm_delete is False
        assert loaded_config.window_state is not None
        assert loaded_config.window_state.width == 1440
        assert loaded_config.window_state.height == 900
        assert loaded_config.window_state.x == 200
        assert loaded_config.window_state.y == 150


class TestConfigManagerEmptyFiles:
    """Tests for handling empty configuration files."""

    def test_load_empty_settings_file_returns_defaults(self, tmp_path: Path) -> None:
        """load() should return defaults when settings.json is empty."""
        config_dir = tmp_path / "empty_settings"
        config_dir.mkdir()

        (config_dir / "settings.json").write_text("", encoding="utf-8")

        manager = ConfigManager(config_dir=config_dir)
        config = manager.config

        assert config.max_concurrent_transfers == 3
        assert config.show_hidden_files is False
        assert config.confirm_delete is True

    def test_load_whitespace_only_file_returns_defaults(self, tmp_path: Path) -> None:
        """load() should return defaults when file contains only whitespace."""
        config_dir = tmp_path / "whitespace_config"
        config_dir.mkdir()

        (config_dir / "settings.json").write_text("   \n\t  \n", encoding="utf-8")

        manager = ConfigManager(config_dir=config_dir)
        config = manager.config

        assert config.max_concurrent_transfers == 3
