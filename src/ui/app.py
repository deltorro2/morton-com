"""Main application window for the dual-panel file manager."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any

from src.models import SourceType
from src.models.transfer_operation import TransferDestination, TransferOperation
from src.platform import get_platform
from src.platform.base import PlatformService
from src.services.auth_service import AuthService
from src.services.config_manager import ConfigManager
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
        self._active_panel_id = "left"
        self._switching_selection = False
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
        self._sync_gcs_credentials()
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
            on_new_folder=self._on_new_folder,
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
            on_tab=self._on_tab,
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
            on_tab=self._on_tab,
        )

        paned.add(self._left_panel, weight=1)
        paned.add(self._right_panel, weight=1)

        # Initial focus (delayed so async item loading finishes first)
        self._toolbar.set_actions_enabled(False)
        self._root.after(200, self._initial_focus)

    def _bind_shortcuts(self) -> None:
        """Register keyboard shortcuts."""
        is_mac = sys.platform == "darwin"
        mod = "Command" if is_mac else "Control"

        # Copy (F5) / Move (F6) — direct operations with confirmation
        self._root.bind("<F5>", lambda e: self._on_copy())
        self._root.bind("<F6>", lambda e: self._on_move())

        # Delete
        self._root.bind("<Delete>", lambda e: self._on_delete())
        if is_mac:
            self._root.bind("<Command-Delete>", lambda e: self._on_delete())

        # Select all
        self._root.bind(f"<{mod}-a>", lambda e: self._on_select_all())

        # New Folder (F7)
        self._root.bind("<F7>", lambda e: self._on_new_folder())

        # Refresh
        self._root.bind(f"<{mod}-r>", lambda e: self._on_refresh())

        # Properties
        self._root.bind(f"<{mod}-i>", lambda e: self._on_properties())
        self._root.bind("<Alt-Return>", lambda e: self._on_properties())

        # Tab: kill ALL default Tk focus traversal at the Tcl level,
        # then install our own handler so Tab only switches panels.
        self._root.tk.eval('bind all <Tab> {break}')
        self._root.tk.eval('bind all <Shift-Tab> {break}')
        self._root.bind("<Tab>", self._on_tab_event)
        self._root.bind("<Shift-Tab>", self._on_tab_event)

        # Backspace to go up
        self._root.bind("<BackSpace>", lambda e: self._on_navigate_up())

    # ------------------------------------------------------------------
    # Panel helpers
    # ------------------------------------------------------------------

    def _initial_focus(self) -> None:
        """Set up left panel focus after startup item loading finishes."""
        self._switching_selection = True
        self._active_panel_id = "left"
        self._right_panel.clear_selection()
        self._left_panel.focus_panel()
        self._left_panel.select_first()
        self._switching_selection = False
        self._toolbar.set_actions_enabled(
            len(self._left_panel.get_selected_items()) > 0
        )
        self._update_new_folder_state()

    def _active_panel(self) -> Panel:
        return self._left_panel if self._active_panel_id == "left" else self._right_panel

    def _inactive_panel(self) -> Panel:
        return self._right_panel if self._active_panel_id == "left" else self._left_panel

    def _update_new_folder_state(self) -> None:
        """Enable/disable New Folder button based on active panel type."""
        panel = self._active_panel()
        enabled = panel.state.source_type != SourceType.GCS_PROJECT
        self._toolbar.set_new_folder_enabled(enabled)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _get_destination_path(self, panel: Panel) -> str:
        """Build a human-readable destination path string for a panel."""
        state = panel.state
        if state.source_type == SourceType.LOCAL:
            return state.location
        elif state.source_type == SourceType.GCS_BUCKET:
            prefix = state.location or ""
            return f"gs://{state.bucket_name}/{prefix}"
        return ""

    def _execute_transfer(self, operation: str) -> None:
        """Show confirmation dialog and execute a copy or move transfer.

        Parameters
        ----------
        operation:
            Either ``"Copy"`` or ``"Move"``.
        """
        items = self._active_panel().get_selected_items()
        if not items:
            return

        dest_panel = self._inactive_panel()
        dest_state = dest_panel.state

        # Don't allow transfer to GCS project listing (no file target)
        if dest_state.source_type == SourceType.GCS_PROJECT:
            return

        dest_path = self._get_destination_path(dest_panel)

        from tkinter import messagebox

        confirmed = messagebox.askokcancel(
            operation,
            f"Are you sure you want to {operation} these objects to {dest_path}?",
            parent=self._root,
        )
        if not confirmed:
            return

        destination = TransferDestination(
            type=dest_state.source_type,
            path=dest_state.location,
            bucket_name=dest_state.bucket_name,
            project_id=dest_state.project_id,
        )

        from src.ui.dialogs.progress import ProgressDialog

        if operation == "Move":
            op = self._transfer_mgr.move(
                items=list(items),
                destination=destination,
                on_progress=lambda o: self._root.after(0, lambda: self._update_progress(o)),
                on_complete=lambda o: self._root.after(0, lambda: self._transfer_complete(o)),
                on_error=lambda o, e: self._root.after(0, lambda: self._transfer_error(o, e)),
            )
        else:
            op = self._transfer_mgr.copy(
                items=list(items),
                destination=destination,
                on_progress=lambda o: self._root.after(0, lambda: self._update_progress(o)),
                on_complete=lambda o: self._root.after(0, lambda: self._transfer_complete(o)),
                on_error=lambda o, e: self._root.after(0, lambda: self._transfer_error(o, e)),
            )

        self._progress_dialog = ProgressDialog(
            self._root, op,
            on_cancel=lambda: self._transfer_mgr.cancel(op),
        )

    def _on_copy(self) -> None:
        self._execute_transfer("Copy")

    def _on_move(self) -> None:
        self._execute_transfer("Move")

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

    def _on_new_folder(self) -> None:
        """Show the New Folder dialog and create the folder."""
        panel = self._active_panel()
        state = panel.state

        # Not available on GCS project listing
        if state.source_type == SourceType.GCS_PROJECT:
            return

        from src.ui.dialogs.new_folder import NewFolderDialog

        dialog = NewFolderDialog(self._root)
        if dialog.folder_name is None:
            return

        folder_name = dialog.folder_name

        from tkinter import messagebox

        from src.errors import FileSystemError

        try:
            if state.source_type == SourceType.LOCAL:
                target = Path(state.location) / folder_name
                self._local_fs.create_directory(target)
            elif state.source_type == SourceType.GCS_BUCKET:
                prefix = state.location or ""
                self._gcs_client.create_folder(
                    state.bucket_name, prefix + folder_name,
                )
        except (FileSystemError, Exception) as exc:
            messagebox.showerror(
                "New Folder",
                str(getattr(exc, "user_message", exc)),
                parent=self._root,
            )
            return

        panel.refresh()

    def _on_select_all(self) -> None:
        self._active_panel().select_all()

    def _on_navigate_up(self) -> None:
        self._active_panel().navigate_up()

    def _on_tab_event(self, event: tk.Event) -> str:
        """Tab event handler (accepts event, returns 'break')."""
        self._on_tab()
        return "break"

    def _on_tab(self) -> None:
        """Switch focus between panels (Total Commander style)."""
        self._switching_selection = True
        old_panel = self._active_panel()
        if self._active_panel_id == "left":
            self._active_panel_id = "right"
        else:
            self._active_panel_id = "left"
        old_panel.clear_selection()
        new_panel = self._active_panel()
        new_panel.focus_panel()
        new_panel.select_first()
        self._switching_selection = False
        self._toolbar.set_actions_enabled(
            len(new_panel.get_selected_items()) > 0
        )
        self._update_new_folder_state()

    def _on_panel_selection_changed(self, panel_id: str, items: list) -> None:
        """Update toolbar state when selection changes."""
        if self._switching_selection:
            return
        if self._active_panel_id != panel_id:
            self._switching_selection = True
            old_panel = self._active_panel()
            self._active_panel_id = panel_id
            old_panel.clear_selection()
            self._switching_selection = False
        self._toolbar.set_actions_enabled(len(items) > 0)
        self._update_new_folder_state()

    def _on_auth_changed(self) -> None:
        """Handle auth state change (sign-in/sign-out)."""
        self._sync_gcs_credentials()
        self._account_menu.refresh()
        # Refresh GCS panels
        for panel in (self._left_panel, self._right_panel):
            if panel.state.source_type in (SourceType.GCS_PROJECT, SourceType.GCS_BUCKET):
                panel.refresh()

    def _sync_gcs_credentials(self) -> None:
        """Pass current auth credentials to the GCS client."""
        if self._gcs_client is None:
            return
        try:
            credentials = self._auth_service.get_credentials()
            self._gcs_client.set_credentials(credentials)
        except Exception:
            pass

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
