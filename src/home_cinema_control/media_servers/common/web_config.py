from __future__ import annotations

from typing import Any

from home_cinema_control.config.manager import (
    get_config_path,
    merge_existing_secrets,
)
from home_cinema_control.media_servers.common.models import MediaServerLibrary


def public_config_with_existing_secrets(config: dict) -> dict:
    """Fill the submitted config with the secrets persisted on disk."""
    return merge_existing_secrets(get_config_path(), config)


def items_from_response(response: Any) -> list[dict[str, Any]]:
    """Normalize a media-server list response (``{"Items": [...]}`` or a list)."""
    if isinstance(response, dict):
        items = response.get("Items", [])
        return items if isinstance(items, list) else []

    return response if isinstance(response, list) else []


def build_library_config(
    views: list[dict[str, Any]],
    *,
    existing_libraries: list[dict[str, Any]],
) -> list[MediaServerLibrary]:
    """Map media-server library views into ``MediaServerLibrary`` value objects,
    preserving the user's previously chosen ``active`` flag.

    Shared by every provider: Emby and Jellyfin expose the same ``{Id, Name}``
    view shape, and the result is an HCC domain contract, not a provider payload.
    """
    existing_by_id = {
        library.id: library
        for library in (
            MediaServerLibrary.model_validate(item) for item in existing_libraries
        )
        if library.id
    }

    libraries = []
    for view in views:
        view_id = str(view.get("Id", ""))
        if not view_id:
            continue

        library = MediaServerLibrary(id=view_id, name=view.get("Name", ""))
        libraries.append(library.reconciled_with(existing_by_id.get(view_id)))

    return libraries
