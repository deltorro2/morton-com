"""Main application window for the dual-panel file manager."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk
from typing import Any

from src.platform import get_platform
from src.platform.base import PlatformService
from src.services.auth_service import AuthService
from src.services.config_manager import ConfigManager
from src.models import ConflictResolution, SourceType
from src.models.transfer_operation import TransferDestination, TransferOperation
from src.services.gcs_client import GCSClient
from src.services.local_filesystem import LocalFilesystem
from src.services.transfer_manager import TransferManager
from src.ui.account_menu import AccountMenu
from src.ui.panel import Panel
from src.ui.toolbar import Toolbar


class App:
    """Main application class managing the root window and panels."""

    def __init__(
        self,
        config_manager: ConfigManager,
        local_fs: LocalFilesystem,
        auth_service: AuthService,
        platform_service: PlatformService | None = None,
        gcs_client: Any = None,
    ) -> None:
        self._config_mgr = config_manager
        self._local_fs = local_fs
        self._auth_service = auth_service
        self._platform = platform_service or get_platform()
        self._gcs_client = gcs_client
        self._config = config_manager.config
        self._clipboard: list = []
        self._clipboard_is_cut = False
        self._clipboard_source_panel: str = "left"
        self._active_panel_id = "left"
        self._transfer_mgr = TransferManager(
            local_fs=local_fs,
            gcs_client=gcs_client,
            max_concurrent=config_manager.config.max_concurrent_transfers,
        )

        self._root = tk.Tk()
        self._root.title("Morton - File Manager")
        self._root.minsize(800, 500)

        # Restore window state
        ws = self._config.window_state
        if ws:
            self._root.geometry(f"{ws.width}x{ws.height}+{ws.x}+{ws.y}")
        else:
            self._root.geometry("1200x800")

        self._build_ui()
        self._bind_shortcuts()

        # Load stored credentials on startup
        self._auth_service.load_stored_credentials()
        self._account_menu.refresh()

        # Save window state on close
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        """Build the main window layout."""
        # Top frame: toolbar + account menu
        top_frame = ttk.Frame(self._root)
        top_frame.pack(fill=tk.X)

        self._toolbar = Toolbar(
            top_frame,
            on_copy=self._on_copy,
            on_move=self._on_move,
            on_delete=self._on_delete,
            on_properties=self._on_properties,
            on_refresh=self._on_refresh,
        )
        self._toolbar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._account_menu = AccountMenu(
            top_frame,
            self._auth_service,
            on_auth_changed=self._on_auth_changed,
        )
        self._account_menu.pack(side=tk.RIGHT)

        # Panels in a PanedWindow
        paned = ttk.PanedWindow(self._root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        projects = self._config_mgr.get_projects()

        self._left_panel = Panel(
            paned,
            panel_id="left",
            local_fs=self._local_fs,
            auth_service=self._auth_service,
            gcs_client=self._gcs_client,
            projects=projects,
            show_hidden=self._config.show_hidden_files,
            on_selection_changed=self._on_panel_selection_changed,
        )
        self._right_panel = Panel(
            paned,
            panel_id="right",
            local_fs=self._local_fs,
            auth_service=self._auth_service,
            gcs_client=self._gcs_client,
            projects=projects,
            show_hidden=self._config.show_hidden_files,
            on_selection_changed=self._on_panel_selection_changed,
        )

        paned.add(self._left_panel, weight=1)
        paned.add(self._right_panel, weight=1)

        # Initial focus
        self._left_panel.focus_panel()
        self._toolbar.set_actions_enabled(False)

    def _bind_shortcuts(self) -> None:
        """Register keyboard shortcuts."""
        is_mac = sys.platform == "darwin"
        mod = "Command" if is_mac else "Control"

        # Copy / Paste
        self._root.bind(f"<{mod}-c>", lambda e: self._on_copy())
        self._root.bind(f"<{mod}-v>", lambda e: self._on_paste())
        self._root.bind(f"<{mod}-x>", lambda e: self._on_move())

        # Delete
        self._root.bind("<Delete>", lambda e: self._on_delete())
        if is_mac:
            self._root.bind("<Command-Delete>", lambda e: self._on_delete())

        # Select all
        self._root.bind(f"<{mod}-a>", lambda e: self._on_select_all())

        # Refresh
        self._root.bind(f"<{mod}-r>", lambda e: self._on_refresh())
        self._root.bind("<F5>", lambda e: self._on_refresh())

        # Properties
        self._root.bind(f"<{mod}-i>", lambda e: self._on_properties())
        self._root.bind("<Alt-Return>", lambda e: self._on_properties())

        # Tab to switch panels
        self._root.bind("<Tab>", self._on_tab)

        # Backspace to go up
        self._root.bind("<BackSpace>", lambda e: self._on_navigate_up())

    # ------------------------------------------------------------------
    # Panel helpers
    # ------------------------------------------------------------------

    def _active_panel(self) -> Panel:
        return self._left_panel if self._active_panel_id == "left" else self._right_panel

    def _inactive_panel(self) -> Panel:
        return self._right_panel if self._active_panel_id == "left" else self._left_panel

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_copy(self) -> None:
        items = self._active_panel().get_selected_items()
        if items:
            self._clipboard = items
            self._clipboard_is_cut = False
            self._clipboard_source_panel = self._active_panel_id

    def _on_move(self) -> None:
        items = self._active_panel().get_selected_items()
        if items:
            self._clipboard = items
            self._clipboard_is_cut = True
            self._clipboard_source_panel = self._active_panel_id

    def _on_paste(self) -> None:
        if not self._clipboard:
            return

        dest_panel = self._active_panel()
        dest_state = dest_panel.state
        destination = TransferDestination(
            type=dest_state.source_type,
            path=dest_state.location,
            bucket_name=dest_state.bucket_name,
            project_id=dest_state.project_id,
        )

        from src.ui.dialogs.progress import ProgressDialog

        if self._clipboard_is_cut:
            op = self._transfer_mgr.move(
                items=list(self._clipboard),
                destination=destination,
                on_progress=lambda o: self._root.after(0, lambda: self._update_progress(o)),
                on_complete=lambda o: self._root.after(0, lambda: self._transfer_complete(o)),
                on_error=lambda o, e: self._root.after(0, lambda: self._transfer_error(o, e)),
            )
        else:
            op = self._transfer_mgr.copy(
                items=list(self._clipboard),
                destination=destination,
                on_progress=lambda o: self._root.after(0, lambda: self._update_progress(o)),
                on_complete=lambda o: self._root.after(0, lambda: self._transfer_complete(o)),
                on_error=lambda o, e: self._root.after(0, lambda: self._transfer_error(o, e)),
            )

        self._progress_dialog = ProgressDialog(
            self._root, op,
            on_cancel=lambda: self._transfer_mgr.cancel(op),
        )
        self._clipboard = []

    def _update_progress(self, op: TransferOperation) -> None:
        if hasattr(self, "_progress_dialog") and self._progress_dialog.winfo_exists():
            self._progress_dialog.update_progress(op)

    def _transfer_complete(self, op: TransferOperation) -> None:
        if hasattr(self, "_progress_dialog") and self._progress_dialog.winfo_exists():
            self._progress_dialog.finish()
        # Refresh both panels
        self._left_panel.refresh()
        self._right_panel.refresh()

    def _transfer_error(self, op: TransferOperation, exc: Exception) -> None:
        if hasattr(self, "_progress_dialog") and self._progress_dialog.winfo_exists():
            self._progress_dialog.destroy()
        from tkinter import messagebox
        messagebox.showerror(
            "Transfer Error",
            f"Operation failed: {exc}",
            parent=self._root,
        )

    def _on_delete(self) -> None:
        items = self._active_panel().get_selected_items()
        if not items:
            return

        if self._config.confirm_delete:
            from tkinter import messagebox

            count = len(items)
            names = ", ".join(
                getattr(i, "name", getattr(i, "display_name", str(i)))
                for i in items[:5]
            )
            if count > 5:
                names += f"... and {count - 5} more"

            confirmed = messagebox.askyesno(
                "Confirm Delete",
                f"Delete {count} item{'s' if count != 1 else ''}?\n\n{names}",
                parent=self._root,
            )
            if not confirmed:
                return

        self._transfer_mgr.delete(
            items=items,
            on_progress=lambda done, total: None,
            on_complete=lambda: self._root.after(0, self._active_panel().refresh),
            on_error=lambda exc: self._root.after(
                0, lambda: __import__("tkinter").messagebox.showerror(
                    "Delete Error", str(exc), parent=self._root,
                ),
            ),
        )

    def _on_properties(self) -> None:
        items = self._active_panel().get_selected_items()
        if not items:
            return
        from src.ui.dialogs.properties import PropertiesDialog
        PropertiesDialog(self._root, items[0])

    def _on_refresh(self) -> None:
        self._active_panel().refresh()

    def _on_select_all(self) -> None:
        self._active_panel().select_all()

    def _on_navigate_up(self) -> None:
        self._active_panel().navigate_up()

    def _on_tab(self, event: tk.Event) -> str:
        """Switch focus between panels."""
        if self._active_panel_id == "left":
            self._active_panel_id = "right"
            self._right_panel.focus_panel()
        else:
            self._active_panel_id = "left"
            self._left_panel.focus_panel()
        return "break"  # Prevent default Tab behavior

    def _on_panel_selection_changed(self, panel_id: str, items: list) -> None:
        """Update toolbar state when selection changes."""
        self._active_panel_id = panel_id
        self._toolbar.set_actions_enabled(len(items) > 0)

    def _on_auth_changed(self) -> None:
        """Handle auth state change (sign-in/sign-out)."""
        self._account_menu.refresh()
        # Refresh GCS panels
        for panel in (self._left_panel, self._right_panel):
            if panel.state.source_type in (SourceType.GCS_PROJECT, SourceType.GCS_BUCKET):
                panel.refresh()

    def _on_close(self) -> None:
        """Save window state and exit."""
        from src.config import WindowState

        geo = self._root.geometry()
        # Parse WxH+X+Y
        try:
            size, pos = geo.split("+", 1)
            w, h = size.split("x")
            x, y = pos.split("+")
            ws = WindowState(width=int(w), height=int(h), x=int(x), y=int(y))
            self._config.window_state = ws
            self._config_mgr.save(self._config)
        except (ValueError, AttributeError):
            pass

        self._root.destroy()

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self._root.mainloop()
