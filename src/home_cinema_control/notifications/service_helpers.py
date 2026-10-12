from __future__ import annotations

from home_cinema_control.notifications.models import UpdateNotification


def build_update_notification(version_info, *, language: str = "es-ES") -> UpdateNotification:
    if language.lower().startswith("en"):
        title = f"Home Cinema Control {version_info.latest_version} is available"
        message = f"HCC {version_info.latest_version} available"
    else:
        title = f"Home Cinema Control {version_info.latest_version} está disponible"
        message = f"HCC {version_info.latest_version} disponible"

    return UpdateNotification(
        current_version=version_info.current_version,
        latest_version=version_info.latest_version,
        release_url=version_info.release_url,
        title=title,
        message=message,
    )
