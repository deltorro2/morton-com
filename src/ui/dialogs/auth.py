"""Sign-in prompt dialog for Google OAuth2 authentication."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.auth_service import AuthService


class SignInDialog(tk.Toplevel):
    """Modal dialog prompting the user to sign in with Google."""

    def __init__(
        self,
        parent: tk.Widget,
        auth_service: AuthService,
        on_success: callable | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("Sign In Required")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self._auth_service = auth_service
        self._on_success = on_success
        self._parent = parent

        self._build_ui()
        self._center_on_parent()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Icon / message
        ttk.Label(
            frame,
            text="Sign in to access Google Cloud Storage",
            font=("TkDefaultFont", 13, "bold"),
        ).pack(pady=(0, 10))

        ttk.Label(
            frame,
            text=(
                "This app uses your gcloud credentials.\n\n"
                "If not set up, run in your terminal:\n"
                "  gcloud auth application-default login"
            ),
            justify=tk.CENTER,
        ).pack(pady=(0, 15))

        # Status label (updates during sign-in)
        self._status_var = tk.StringVar(value="")
        self._status_label = ttk.Label(frame, textvariable=self._status_var)
        self._status_label.pack(pady=(0, 10))

        # Progress bar (hidden by default)
        self._progress = ttk.Progressbar(frame, mode="indeterminate", length=250)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(5, 0))

        self._sign_in_btn = ttk.Button(
            btn_frame,
            text="Load Credentials",
            command=self._on_sign_in,
        )
        self._sign_in_btn.pack(side=tk.LEFT, padx=5)

        self._cancel_btn = ttk.Button(
            btn_frame,
            text="Cancel",
            command=self.destroy,
        )
        self._cancel_btn.pack(side=tk.LEFT, padx=5)

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        pw = self._parent.winfo_rootx() + self._parent.winfo_width() // 2
        ph = self._parent.winfo_rooty() + self._parent.winfo_height() // 2
        self.geometry(f"+{pw - w // 2}+{ph - h // 2}")

    def _on_sign_in(self) -> None:
        self._sign_in_btn.configure(state=tk.DISABLED)
        self._status_var.set("Loading credentials...")
        self._progress.pack(pady=(0, 10))
        self._progress.start(15)

        self._auth_service.sign_in(
            on_browser_opened=lambda: self.after(
                0, lambda: self._status_var.set("Authenticating...")
            ),
            on_success=lambda session: self.after(0, lambda: self._handle_success(session)),
            on_error=lambda exc: self.after(0, lambda: self._handle_error(exc)),
        )

    def _handle_success(self, session: object) -> None:
        self._progress.stop()
        self._status_var.set(f"Signed in as {session.email}")  # type: ignore[attr-defined]
        if self._on_success:
            self._on_success(session)
        self.after(1000, self.destroy)

    def _handle_error(self, exc: Exception) -> None:
        self._progress.stop()
        self._progress.pack_forget()
        self._sign_in_btn.configure(state=tk.NORMAL)
        self._status_var.set(f"Sign-in failed: {exc}")
