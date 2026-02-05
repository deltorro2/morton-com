"""Configuration management service.

Handles loading and persisting application configuration from JSON files
stored in the platform-specific configuration directory.  Two files are
managed:

* ``settings.json`` -- global preferences and window state.
* ``projects.json``  -- list of configured Google Cloud projects.

Missing files are silently replaced with defaults; malformed JSON raises
:class:`~src.errors.ConfigurationError` with user-facing messaging.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.config import Configuration, ProjectConfig, WindowState
from src.errors import ConfigurationError
from src.platform import get_platform

logger = logging.getLogger(__name__)

_SETTINGS_FILE = "settings.json"
_PROJECTS_FILE = "projects.json"


class ConfigManager:
    """Service for configuration management.

    Parameters
    ----------
    config_dir:
        Explicit directory for configuration files.  When *None* (the
        default), the platform service is queried for the appropriate
        location.
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        if config_dir is not None:
            self._config_dir = config_dir
        else:
            platform = get_platform()
            self._config_dir = platform.get_config_directory()

        self._config: Configuration = self.load()

    # -- public interface ------------------------------------------------------

    def load(self) -> Configuration:
        """Load configuration from *settings.json* and *projects.json*.

        Returns a :class:`Configuration` populated with defaults for any
        values that are missing or for files that do not exist.  The
        configuration directory is created if it does not already exist.

        Raises
        ------
        ConfigurationError
            If either file contains malformed JSON.
        """
        self._config_dir.mkdir(parents=True, exist_ok=True)

        settings_data = self._read_json(self._config_dir / _SETTINGS_FILE)
        projects_data = self._read_json(self._config_dir / _PROJECTS_FILE)

        projects = self._parse_projects(projects_data)
        settings = self._parse_settings(settings_data)

        config = Configuration(
            projects=projects,
            max_concurrent_transfers=settings["max_concurrent_transfers"],
            show_hidden_files=settings["show_hidden_files"],
            confirm_delete=settings["confirm_delete"],
            window_state=settings["window_state"],
        )

        self._config = config
        return config

    def save(self, config: Configuration) -> None:
        """Persist *config* to *settings.json* and *projects.json*.

        Raises
        ------
        ConfigurationError
            If the files cannot be written (permissions, disk full, etc.).
        """
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config = config

        settings_payload = self._build_settings_payload(config)
        projects_payload = self._build_projects_payload(config)

        self._write_json(self._config_dir / _SETTINGS_FILE, settings_payload)
        self._write_json(self._config_dir / _PROJECTS_FILE, projects_payload)

    def get_config_directory(self) -> Path:
        """Return the configuration directory path."""
        return self._config_dir

    def add_project(self, project: ProjectConfig) -> None:
        """Add *project* to the current configuration and save to disk."""
        self._config.projects.append(project)
        self.save(self._config)

    def remove_project(self, project_id: str) -> None:
        """Remove the project identified by *project_id* and save to disk."""
        self._config.projects = [
            p for p in self._config.projects if p.project_id != project_id
        ]
        self.save(self._config)

    def get_projects(self) -> list[ProjectConfig]:
        """Return the list of configured projects."""
        return list(self._config.projects)

    @property
    def config(self) -> Configuration:
        """Current in-memory configuration."""
        return self._config

    # -- private helpers -------------------------------------------------------

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        """Read and parse a JSON file, returning ``{}`` when absent."""
        if not path.exists():
            logger.debug("Configuration file not found, using defaults: %s", path)
            return {}

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigurationError(
                message=f"Failed to read configuration file: {exc}",
                user_message="Could not read the configuration file.",
                suggested_action="Check file permissions and try again.",
                technical_detail=str(path),
            ) from exc

        if not text.strip():
            return {}

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                message=f"Malformed JSON in {path}: {exc}",
                user_message="The configuration file contains invalid JSON.",
                suggested_action=(
                    "Fix or delete the file and restart the application."
                ),
                technical_detail=str(path),
            ) from exc

        if not isinstance(data, dict):
            raise ConfigurationError(
                message=f"Expected JSON object in {path}, got {type(data).__name__}",
                user_message="The configuration file has an unexpected format.",
                suggested_action=(
                    "Fix or delete the file and restart the application."
                ),
                technical_detail=str(path),
            )

        return data

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        """Serialise *payload* as pretty-printed JSON to *path*."""
        try:
            path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise ConfigurationError(
                message=f"Failed to write configuration file: {exc}",
                user_message="Could not save the configuration file.",
                suggested_action="Check disk space and file permissions.",
                technical_detail=str(path),
            ) from exc

    @staticmethod
    def _parse_projects(data: dict[str, Any]) -> list[ProjectConfig]:
        """Extract a list of :class:`ProjectConfig` from raw JSON data."""
        raw_projects = data.get("projects", [])
        if not isinstance(raw_projects, list):
            return []

        projects: list[ProjectConfig] = []
        for entry in raw_projects:
            if not isinstance(entry, dict):
                continue
            project_id = entry.get("project_id")
            if not project_id or not isinstance(project_id, str):
                continue
            projects.append(
                ProjectConfig(
                    project_id=project_id,
                    display_name=str(entry.get("display_name", "")),
                    default=bool(entry.get("default", False)),
                )
            )
        return projects

    @staticmethod
    def _parse_settings(data: dict[str, Any]) -> dict[str, Any]:
        """Extract settings values with defaults for missing keys."""
        defaults = Configuration()

        window_state: WindowState | None = None
        raw_ws = data.get("window_state")
        if isinstance(raw_ws, dict):
            ws_defaults = WindowState()
            window_state = WindowState(
                width=int(raw_ws.get("width", ws_defaults.width)),
                height=int(raw_ws.get("height", ws_defaults.height)),
                x=int(raw_ws.get("x", ws_defaults.x)),
                y=int(raw_ws.get("y", ws_defaults.y)),
            )

        return {
            "max_concurrent_transfers": int(
                data.get("max_concurrent_transfers", defaults.max_concurrent_transfers)
            ),
            "show_hidden_files": bool(
                data.get("show_hidden_files", defaults.show_hidden_files)
            ),
            "confirm_delete": bool(
                data.get("confirm_delete", defaults.confirm_delete)
            ),
            "window_state": window_state,
        }

    @staticmethod
    def _build_settings_payload(config: Configuration) -> dict[str, Any]:
        """Build the JSON-serialisable dict for *settings.json*."""
        payload: dict[str, Any] = {
            "max_concurrent_transfers": config.max_concurrent_transfers,
            "show_hidden_files": config.show_hidden_files,
            "confirm_delete": config.confirm_delete,
        }
        if config.window_state is not None:
            payload["window_state"] = {
                "width": config.window_state.width,
                "height": config.window_state.height,
                "x": config.window_state.x,
                "y": config.window_state.y,
            }
        return payload

    @staticmethod
    def _build_projects_payload(config: Configuration) -> dict[str, Any]:
        """Build the JSON-serialisable dict for *projects.json*."""
        return {
            "projects": [
                {
                    "project_id": p.project_id,
                    "display_name": p.display_name,
                    "default": p.default,
                }
                for p in config.projects
            ]
        }
