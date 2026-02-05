"""Application configuration data models.

Provides dataclass-based configuration objects for project settings,
window geometry, and global application preferences.  These are designed
to be serialised to / deserialised from a JSON configuration file.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProjectConfig:
    """A single Google Cloud project reference.

    Parameters
    ----------
    project_id:
        Google Cloud project identifier.
    display_name:
        Human-friendly label.  Falls back to *project_id* when empty.
    default:
        ``True`` when this is the default project.
    """

    project_id: str
    display_name: str = ""
    default: bool = False

    @property
    def effective_display_name(self) -> str:
        """Return *display_name* if set, otherwise *project_id*."""
        return self.display_name if self.display_name else self.project_id


@dataclass
class WindowState:
    """Persisted window geometry.

    Parameters
    ----------
    width:
        Window width in pixels.
    height:
        Window height in pixels.
    x:
        Horizontal offset of the top-left corner.
    y:
        Vertical offset of the top-left corner.
    """

    width: int = 1200
    height: int = 800
    x: int = 100
    y: int = 100


@dataclass
class Configuration:
    """Top-level application configuration.

    Parameters
    ----------
    projects:
        List of configured Google Cloud projects.
    max_concurrent_transfers:
        Maximum number of simultaneous file transfers.
    show_hidden_files:
        Whether hidden files are visible by default.
    confirm_delete:
        Whether to prompt before destructive operations.
    window_state:
        Saved window position and size, or ``None``.
    """

    projects: list[ProjectConfig] = field(default_factory=list)
    max_concurrent_transfers: int = 3
    show_hidden_files: bool = False
    confirm_delete: bool = True
    window_state: WindowState | None = None
