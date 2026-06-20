import json
import os
import shutil
from pathlib import Path

from home_cinema_control.config.migration import _remove_legacy_flat_keys
from home_cinema_control.config.models import HccConfig


CONFIG_ENV_VAR = "HCC_CONFIG_FILE"
SECRETS_ENV_VAR = "HCC_SECRETS_FILE_PATH"

DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_SECRETS_FILE = "secrets.json"

EXAMPLE_CONFIG_FILE = "config.example.json"

SECRET_PATHS = {
    ("user_password",),
    ("media_server", "access_token"),
    ("media_server", "user_id"),
    ("smb", "password"),
}

SENSITIVE_WEB_CONFIG_PATHS = set(SECRET_PATHS)


def merge_existing_secrets(config_path: Path | str, config: dict) -> dict:
    """
    Return config with persisted secrets filled in for any secret path
    that is absent or empty in the submitted config.

    Submitted non-empty values always win so that newly entered credentials
    are not overwritten by the empty placeholders stored on first install.
    """
    config_path = Path(config_path)
    secrets = load_secrets(config_path)

    merged_config = _deep_merge({}, config)
    for path in SECRET_PATHS:
        submitted = str(_get_nested(merged_config, path, "") or "").strip()
        if not submitted:
            existing = str(_get_nested(secrets, path, "") or "").strip()
            if existing:
                _set_nested(merged_config, path, existing)

    _remove_legacy_flat_keys(merged_config)
    return merged_config


def sanitize_config_for_web(config: dict) -> dict:
    """
    Remove sensitive values before returning config to the web UI.

    The UI receives media_server.access_token_configured so it can show that
    Emby token authentication is configured without receiving the token or user id.

    smb.username is not a secret and is returned as-is so the UI can show which
    account is configured. smb.password_configured reports whether a password is
    stored, without exposing it, so the UI can distinguish the three SMB
    credential states: none, username only, or username + password.
    """
    safe_config = _deep_merge({}, config)

    media_server = safe_config.setdefault("media_server", {})
    media_server["access_token_configured"] = bool(
        str(_get_nested(config, ("media_server", "access_token"), "")).strip()
        or media_server.get("access_token_configured") is True
    )

    password_configured = bool(
        str(_get_nested(config, ("smb", "password"), "")).strip()
    )

    for path in SENSITIVE_WEB_CONFIG_PATHS:
        _pop_nested(safe_config, path)

    safe_smb = safe_config.setdefault("smb", {})
    safe_smb["username"] = str(_get_nested(config, ("smb", "username"), "") or "")
    safe_smb["password_configured"] = password_configured

    _remove_legacy_flat_keys(safe_config)

    return safe_config


def is_smb_active(config: dict) -> bool:
    """True when SMB/CIFS is the user-selected network protocol for the OPPO mount.

    Credentials are optional: the OPPO supports anonymous SMB shares, so the
    with-id vs. without-id mount choice is made separately, downstream, based
    on whether credentials happen to be present.
    """
    return bool(config.get("oppo", {}).get("use_smb", False))


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_config_path() -> Path:
    return Path(os.environ.get(CONFIG_ENV_VAR) or DEFAULT_CONFIG_FILE)


def get_secrets_path(config_path: Path | str | None = None) -> Path:
    configured_path = os.environ.get(SECRETS_ENV_VAR)

    if configured_path:
        return Path(configured_path)

    if config_path is None:
        config_path = get_config_path()

    return Path(config_path).with_name(DEFAULT_SECRETS_FILE)


def ensure_config_exists() -> Path:
    config_path = get_config_path()

    if not config_path.exists():
        _create_config_file(config_path)

    ensure_secrets_exists(config_path)

    return config_path


def ensure_secrets_exists(config_path: Path | str | None = None) -> Path:
    if config_path is None:
        config_path = get_config_path()
    else:
        config_path = Path(config_path)

    secrets_path = get_secrets_path(config_path)

    if secrets_path.exists():
        return secrets_path

    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(secrets_path, _default_secrets())
    _chmod_private(secrets_path)

    print(f"Secrets file created at {secrets_path}. Keep this file private.")
    return secrets_path


def load_effective_config(config_path: Path | str | None = None) -> dict:
    """
    Load the internal runtime config.

    Internal code receives app config + secrets merged together:

    config.json:
      media_server.server_url
      media_server.display_name
      media_server.access_token_configured

    secrets.json:
      media_server.access_token
      media_server.user_id
    """
    if config_path is None:
        config_path = ensure_config_exists()
    else:
        config_path = Path(config_path)
        ensure_secrets_exists(config_path)

    public_config = _read_json(config_path)
    secrets = load_secrets(config_path)

    effective_config = _deep_merge(public_config, secrets)
    return HccConfig(**effective_config).model_dump()


def load_public_config(config_path: Path | str | None = None) -> dict:
    """
    Load config safe to expose to the web UI.
    """
    effective_config = load_effective_config(config_path)
    return sanitize_config_for_web(effective_config)


def load_secrets(config_path: Path | str | None = None) -> dict:
    """
    Load secrets from the configured secrets file.

    There is intentionally no runtime fallback to user_password or
    config.secrets.json. Emby authentication is token-only.
    """
    if config_path is None:
        config_path = get_config_path()
    else:
        config_path = Path(config_path)

    return _read_json(get_secrets_path(config_path))


def save_effective_config(config_path: Path | str, config: dict) -> None:
    """
    Save app config and secrets separately.

    Sensitive nested values are written to secrets.json. Public values are
    written to config.json. If the web UI saves only public config, existing
    secrets are preserved.
    """
    config_path = Path(config_path)
    secrets_path = ensure_secrets_exists(config_path)

    public_config = _deep_merge({}, config)
    existing_secrets = load_secrets(config_path)
    secrets = _deep_merge({}, existing_secrets)

    for path in SECRET_PATHS:
        value = _pop_nested(public_config, path)

        if value not in (None, ""):
            _set_nested(secrets, path, value)

    # smb.username moved from secrets.json to config.json (it is not a secret).
    # Drop any leftover copy so a stale secrets.json value can no longer win
    # over a fresher config.json value during load_effective_config's merge.
    _pop_nested(secrets, ("smb", "username"))

    _remove_sensitive_paths(public_config)
    _remove_legacy_flat_keys(public_config)
    _remove_legacy_flat_keys(secrets)

    media_server = public_config.setdefault("media_server", {})
    media_server["access_token_configured"] = bool(
        str(_get_nested(secrets, ("media_server", "access_token"), "")).strip()
    )

    _write_json(config_path, public_config)
    _write_json(secrets_path, secrets)
    _chmod_private(secrets_path)


def clear_smb_credentials(config_path: Path | str) -> None:
    """Explicitly wipe stored SMB credentials.

    The password lives in secrets.json; the username lives in config.json
    (it is not a secret). Both are cleared so neither resurfaces later.
    """
    config_path = Path(config_path)
    secrets_path = ensure_secrets_exists(config_path)

    secrets = load_secrets(config_path)
    _set_nested(secrets, ("smb", "password"), "")
    _pop_nested(secrets, ("smb", "username"))
    _write_json(secrets_path, secrets)
    _chmod_private(secrets_path)

    public_config = _read_json(config_path)
    _set_nested(public_config, ("smb", "username"), "")
    _write_json(config_path, public_config)


def clear_media_server_auth(config_path: Path | str) -> None:
    """Explicitly wipe stored media-server auth and monitored-device state.

    Called when the user switches the selected provider (Emby/Jellyfin):
    access_token/user_id live in secrets.json; display_name and
    access_token_configured live in config.json. A blank submission alone
    would not clear them — merge_existing_secrets fills blanks back in from
    secrets.json on the next save, by design, so this needs an explicit wipe
    the same way clear_smb_credentials does.

    Verified path mappings are untouched: Emby and Jellyfin may point at the
    same NAS paths, so they are preserved across a provider switch.
    """
    config_path = Path(config_path)
    secrets_path = ensure_secrets_exists(config_path)

    secrets = load_secrets(config_path)
    _set_nested(secrets, ("media_server", "access_token"), "")
    _set_nested(secrets, ("media_server", "user_id"), "")
    _write_json(secrets_path, secrets)
    _chmod_private(secrets_path)

    public_config = _read_json(config_path)
    media_server = public_config.setdefault("media_server", {})
    media_server["display_name"] = ""
    media_server["access_token_configured"] = False
    playback = public_config.setdefault("playback", {})
    playback["hcc_controlled_device"] = ""
    _write_json(config_path, public_config)


def migrate_secrets_from_config(config_path: Path | str) -> None:
    """
    No-op kept temporarily only to avoid breaking any old caller.

    The app no longer supports migrating or using user_password at runtime.
    Emby authentication is token-only through secrets.json.
    """
    return None


def is_configured(config: dict) -> bool:
    media_server = config.get("media_server") or {}

    server_url = str(media_server.get("server_url", "")).strip()
    access_token = str(media_server.get("access_token", "")).strip()
    user_id = str(media_server.get("user_id", "")).strip()

    if not server_url or not access_token or not user_id:
        return False

    return server_url.startswith(("http://", "https://"))


def _create_config_file(config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Use CWD: in Docker the process root is /app, and in development it is the
    # project checkout root; both contain config.example.json.
    base = Path.cwd()
    legacy_config_path = base / DEFAULT_CONFIG_FILE
    example_path = base / EXAMPLE_CONFIG_FILE

    if legacy_config_path.exists() and legacy_config_path.resolve() != config_path.resolve():
        shutil.copyfile(legacy_config_path, config_path)
        print(
            f"Existing config found at {legacy_config_path}. "
            f"Copied it to {config_path}. Original file was left untouched."
        )
        return

    if not example_path.exists():
        raise FileNotFoundError(f"Missing {EXAMPLE_CONFIG_FILE}; cannot create default config")

    shutil.copyfile(example_path, config_path)
    print(f"Config file created at {config_path}. Complete setup from the web UI.")


def _default_secrets() -> dict:
    return {
        "media_server": {
            "access_token": "",
            "user_id": "",
        },
        "smb": {
            "password": "",
        },
    }


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
        file.write("\n")


def _chmod_private(path: Path) -> None:
    try:
        path.chmod(0o600)
    except PermissionError:
        print(f"Could not chmod {path}; continuing without changing permissions.")


def _get_nested(data: dict, path: tuple[str, ...], default=None):
    current = data

    for key in path:
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def _set_nested(data: dict, path: tuple[str, ...], value) -> None:
    current = data

    for key in path[:-1]:
        current = current.setdefault(key, {})

    current[path[-1]] = value


def _pop_nested(data: dict, path: tuple[str, ...]):
    current = data

    for key in path[:-1]:
        current = current.get(key)

        if not isinstance(current, dict):
            return None

    return current.pop(path[-1], None)


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge two dicts into a new dict with no shared nested-dict references.

    A shallow `dict(base)` plus direct assignment would let a caller's
    in-place pop/set on the result (e.g. moving a secret out of the public
    config in save_effective_config) silently mutate the original `base` or
    `override` dict too, since they'd still share the same nested object.
    """
    merged = {
        key: _deep_merge({}, value) if isinstance(value, dict) else value
        for key, value in base.items()
    }

    for key, value in override.items():
        if isinstance(value, dict):
            existing = merged.get(key)
            merged[key] = _deep_merge(
                existing if isinstance(existing, dict) else {}, value
            )
        else:
            merged[key] = value

    return merged


def _remove_sensitive_paths(config: dict) -> None:
    for path in SENSITIVE_WEB_CONFIG_PATHS:
        _pop_nested(config, path)

