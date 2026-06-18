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


def is_migration_available(config_path: Path | str) -> bool:
    config_path = Path(config_path)

    if not config_path.exists():
        return False

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    if LEGACY_DETECTION_KEYS & set(raw.keys()):
        return True

    oppo = raw.get("oppo")
    return isinstance(oppo, dict) and bool(NESTED_OPPO_LEGACY_KEYS & set(oppo.keys()))


def apply_migration(config_path: Path | str) -> None:
    config_path = Path(config_path)
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    apply_all_migrations(raw)
    save_effective_config(config_path, raw)


def start_fresh(config_path: Path | str) -> None:
    config_path = Path(config_path)
    example_path = Path.cwd() / EXAMPLE_CONFIG_FILE

    if not example_path.exists():
        raise FileNotFoundError(f"Missing {EXAMPLE_CONFIG_FILE}; cannot create default config")

    shutil.copyfile(example_path, config_path)
