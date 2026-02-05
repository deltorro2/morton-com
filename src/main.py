"""Application entry point for Morton file manager.

Run with: python -m src.main
"""

from __future__ import annotations

import logging
import sys


def main() -> None:
    """Initialize services and launch the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    from src.platform import get_platform
    from src.services.auth_service import AuthService
    from src.services.config_manager import ConfigManager
    from src.services.credential_storage import CredentialStorage
    from src.services.gcs_client import GCSClient
    from src.services.local_filesystem import LocalFilesystem
    from src.ui.app import App

    platform_service = get_platform()
    config_manager = ConfigManager()
    local_fs = LocalFilesystem()
    credential_storage = CredentialStorage()
    auth_service = AuthService(credential_storage=credential_storage)
    gcs_client = GCSClient()

    app = App(
        config_manager=config_manager,
        local_fs=local_fs,
        auth_service=auth_service,
        platform_service=platform_service,
        gcs_client=gcs_client,
    )
    app.run()


if __name__ == "__main__":
    main()
