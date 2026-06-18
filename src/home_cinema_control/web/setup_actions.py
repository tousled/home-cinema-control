from __future__ import annotations

from typing import Any

from home_cinema_control.web.setup_verification import maybe_mark_section_verified


def persist_verification_if_submitted_matches_saved(
    *,
    config_service,
    submitted_config: dict[str, Any],
    section: str,
) -> tuple[dict[str, Any], bool]:
    saved_config = config_service.load_config()
    updated_config, persisted = maybe_mark_section_verified(
        saved_config,
        submitted_config,
        section,
    )
    if persisted:
        config_service.save_config(updated_config)
    return updated_config, persisted


def sanitized_submitted_section(
    *,
    config_service,
    submitted_config: dict[str, Any],
    section_key: str,
) -> dict[str, Any]:
    prepared = config_service.prepare_submitted_config(submitted_config)
    sanitized = config_service.sanitize(prepared)
    return sanitized.get(section_key, {})
