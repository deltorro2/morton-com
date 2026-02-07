"""Account menu widget displaying signed-in user info and sign-out option."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.auth_service import AuthService


class AccountMenu(ttk.Frame):
    """Displays the authenticated user's email with a sign-out dropdown."""

    def __init__(
        self,
        parent: tk.Widget,
        auth_service: AuthService,
        on_auth_changed: callable | None = None,
    ) -> None:
        super().__init__(parent)
        self._auth_service = auth_service
        self._on_auth_changed = on_auth_changed

        self._account_var = tk.StringVar(value="Not signed in")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self._menu_btn = ttk.Menubutton(
            self,
            textvariable=self._account_var,
            direction="below",
        )
        self._menu_btn.pack(side=tk.RIGHT, padx=5)

        self._menu = tk.Menu(self._menu_btn, tearoff=0)
        self._menu_btn["menu"] = self._menu

    def refresh(self) -> None:
        """Update display based on current auth state."""
        # Clear existing menu items
        self._menu.delete(0, tk.END)

        user = self._auth_service.current_user
        if user is not None:
            self._account_var.set(user.email)
            self._menu.add_command(label="Sign Out", command=self._on_sign_out)
            self._menu_btn.state(["!disabled"])
        else:
            self._account_var.set("Sign In")
            self._menu.add_command(label="Sign in with Google", command=self._on_sign_in)
            self._menu_btn.state(["!disabled"])

    def _on_sign_in(self) -> None:
        """Open sign-in dialog."""
        from src.ui.dialogs.auth import SignInDialog

        SignInDialog(
            self.winfo_toplevel(),
            self._auth_service,
            on_success=self._after_sign_in,
        )

    def _after_sign_in(self, session: object) -> None:
        """Called after successful sign-in."""
        self.after(0, self._update_after_sign_in)

    def _update_after_sign_in(self) -> None:
        self.refresh()
        if self._on_auth_changed:
            self._on_auth_changed()

    def _on_sign_out(self) -> None:
        confirmed = messagebox.askyesno(
            "Sign Out",
            "Are you sure you want to sign out?\n\n"
            "Your stored credentials will be removed.",
            parent=self,
        )
        if confirmed:
            self._auth_service.sign_out(on_complete=self._after_sign_out)

    def _after_sign_out(self) -> None:
        self.after(0, self._update_after_sign_out)

    def _update_after_sign_out(self) -> None:
        self.refresh()
        if self._on_auth_changed:
            self._on_auth_changed()
