"""Unit tests for configuration dataclasses.

Tests cover ProjectConfig, WindowState, and Configuration dataclasses
including default values, custom values, properties, equality, and hashability.
"""

from __future__ import annotations

import pytest

from src.config import Configuration, ProjectConfig, WindowState


class TestProjectConfig:
    """Tests for ProjectConfig dataclass."""

    def test_required_fields_only(self) -> None:
        """ProjectConfig with only project_id should use defaults for other fields."""
        config = ProjectConfig(project_id="my-project-123")

        assert config.project_id == "my-project-123"
        assert config.display_name == ""
        assert config.default is False

    def test_effective_display_name_returns_display_name_when_set(self) -> None:
        """effective_display_name should return display_name when it is non-empty."""
        config = ProjectConfig(
            project_id="my-project-123",
            display_name="My Project",
        )

        assert config.effective_display_name == "My Project"

    def test_effective_display_name_returns_project_id_when_empty(self) -> None:
        """effective_display_name should return project_id when display_name is empty."""
        config = ProjectConfig(project_id="my-project-123", display_name="")

        assert config.effective_display_name == "my-project-123"

    def test_equality(self) -> None:
        """Two ProjectConfig instances with same values should be equal."""
        config1 = ProjectConfig(
            project_id="my-project",
            display_name="My Project",
            default=True,
        )
        config2 = ProjectConfig(
            project_id="my-project",
            display_name="My Project",
            default=True,
        )

        assert config1 == config2

    def test_inequality(self) -> None:
        """Two ProjectConfig instances with different values should not be equal."""
        config1 = ProjectConfig(project_id="project-a")
        config2 = ProjectConfig(project_id="project-b")

        assert config1 != config2


class TestWindowState:
    """Tests for WindowState dataclass."""

    def test_default_values(self) -> None:
        """WindowState should have correct default values."""
        state = WindowState()

        assert state.width == 1200
        assert state.height == 800
        assert state.x == 100
        assert state.y == 100

    def test_custom_values(self) -> None:
        """WindowState should accept custom values for all fields."""
        state = WindowState(width=1920, height=1080, x=50, y=75)

        assert state.width == 1920
        assert state.height == 1080
        assert state.x == 50
        assert state.y == 75

    def test_equality(self) -> None:
        """Two WindowState instances with same values should be equal."""
        state1 = WindowState(width=800, height=600, x=0, y=0)
        state2 = WindowState(width=800, height=600, x=0, y=0)

        assert state1 == state2


class TestConfiguration:
    """Tests for Configuration dataclass."""

    def test_default_values(self) -> None:
        """Configuration should have correct default values."""
        config = Configuration()

        assert config.projects == []
        assert config.max_concurrent_transfers == 3
        assert config.show_hidden_files is False
        assert config.confirm_delete is True
        assert config.window_state is None

    def test_with_projects_list(self) -> None:
        """Configuration should accept a list of ProjectConfig instances."""
        projects = [
            ProjectConfig(project_id="project-1", display_name="Project 1"),
            ProjectConfig(project_id="project-2", default=True),
        ]
        config = Configuration(projects=projects)

        assert len(config.projects) == 2
        assert config.projects[0].project_id == "project-1"
        assert config.projects[1].project_id == "project-2"
        assert config.projects[1].default is True

    def test_with_custom_settings(self) -> None:
        """Configuration should accept custom values for all settings."""
        config = Configuration(
            max_concurrent_transfers=5,
            show_hidden_files=True,
            confirm_delete=False,
        )

        assert config.max_concurrent_transfers == 5
        assert config.show_hidden_files is True
        assert config.confirm_delete is False

    def test_with_window_state(self) -> None:
        """Configuration should accept a WindowState instance."""
        window_state = WindowState(width=1600, height=900, x=200, y=150)
        config = Configuration(window_state=window_state)

        assert config.window_state is not None
        assert config.window_state.width == 1600
        assert config.window_state.height == 900
        assert config.window_state.x == 200
        assert config.window_state.y == 150

    def test_projects_list_is_mutable(self) -> None:
        """Projects list should be mutable after creation."""
        config = Configuration()
        config.projects.append(ProjectConfig(project_id="new-project"))

        assert len(config.projects) == 1
        assert config.projects[0].project_id == "new-project"

    def test_separate_instances_have_independent_projects_lists(self) -> None:
        """Each Configuration instance should have its own projects list."""
        config1 = Configuration()
        config2 = Configuration()

        config1.projects.append(ProjectConfig(project_id="project-a"))

        assert len(config1.projects) == 1
        assert len(config2.projects) == 0

    def test_equality(self) -> None:
        """Two Configuration instances with same values should be equal."""
        config1 = Configuration(
            projects=[ProjectConfig(project_id="test")],
            max_concurrent_transfers=5,
            show_hidden_files=True,
            confirm_delete=False,
            window_state=WindowState(width=800, height=600, x=0, y=0),
        )
        config2 = Configuration(
            projects=[ProjectConfig(project_id="test")],
            max_concurrent_transfers=5,
            show_hidden_files=True,
            confirm_delete=False,
            window_state=WindowState(width=800, height=600, x=0, y=0),
        )

        assert config1 == config2
