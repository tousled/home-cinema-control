import json
import shutil
from pathlib import Path

from home_cinema_control.config.manager import (
    EXAMPLE_CONFIG_FILE,
    save_effective_config,
)
from home_cinema_control.config.migration import (
    LEGACY_DETECTION_KEYS,
    NESTED_OPPO_LEGACY_KEYS,
    apply_all_migrations,
)
from home_cinema_control.media_servers.emby.web_config import (
    authenticate_legacy_credentials,
)


def _looks_like_legacy_config(raw: dict) -> bool:
    if LEGACY_DETECTION_KEYS & set(raw.keys()):
        return True

    if str(raw.get("emby_server", "")).strip():
        return True

    oppo = raw.get("oppo")
    return isinstance(oppo, dict) and bool(NESTED_OPPO_LEGACY_KEYS & set(oppo.keys()))


def is_migration_available(config_path: Path | str) -> bool:
    config_path = Path(config_path)

    if not config_path.exists():
        return False

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    return _looks_like_legacy_config(raw)


def _migrate_and_save(raw: dict, config_path: Path | str) -> None:
    """Transform raw in place and save it, with a best-effort live Emby login
    for any XNOPPO-era username/password found before they're discarded.

    apply_all_migrations stays a pure, network-free dict transform (see
    config/migration.py) so it can't perform that login itself; this is the
    one layer free to depend on both config/manager.py and
    media_servers/emby/web_config.py without a circular import. The login is
    best-effort: on failure the provider is simply left unauthenticated, the
    same state as a freshly added, not-yet-connected provider — it does not
    abort the rest of the migration.
    """
    legacy_user_name = str(raw.get("user_name", "")).strip()
    legacy_password = str(raw.get("user_password", "")).strip()

    apply_all_migrations(raw)

    if legacy_user_name and legacy_password:
        provider = raw.get("media_servers", {}).get("providers", {}).get("emby", {})
        server_url = str(provider.get("server_url", "")).strip()
        if server_url:
            auth_response = authenticate_legacy_credentials(
                server_url, legacy_user_name, legacy_password
            )
            if auth_response:
                user = auth_response.get("User") or {}
                provider["access_token"] = auth_response.get("AccessToken", "")
                provider["user_id"] = user.get("Id", "")
                if user.get("Name"):
                    provider["display_name"] = user["Name"]

    save_effective_config(config_path, raw)


def apply_migration(config_path: Path | str) -> None:
    config_path = Path(config_path)
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    _migrate_and_save(raw, config_path)


def import_legacy_config(config_path: Path | str, uploaded: dict) -> None:
    """Replace config_path's content with an uploaded XNOPPO-era config.json,
    migrated into the current shape. For the fresh-install case: there is no
    real data to preserve in the default config_path already wrote, so this
    overwrites it outright. Raises ValueError if uploaded doesn't look like a
    legacy config, so an unrelated file can't wipe a fresh install.
    """
    config_path = Path(config_path)

    if not isinstance(uploaded, dict) or not _looks_like_legacy_config(uploaded):
        raise ValueError("Not a recognizable legacy config")

    _migrate_and_save(uploaded, config_path)


def start_fresh(config_path: Path | str) -> None:
    config_path = Path(config_path)
    example_path = Path.cwd() / EXAMPLE_CONFIG_FILE

    if not example_path.exists():
        raise FileNotFoundError(f"Missing {EXAMPLE_CONFIG_FILE}; cannot create default config")

    shutil.copyfile(example_path, config_path)
