from pathlib import Path

from home_cinema_control import __version__
from home_cinema_control.config.manager import (
    ensure_config_exists,
    migrate_media_server_to_media_servers_on_disk,
)
from home_cinema_control.web.composition import (
    build_web_runtime_composition,
    prepare_runtime_for_web,
    serve_web_app,
)


def main() -> None:
    base_dir = Path.cwd()
    config_file = ensure_config_exists()
    # Runs once, here, at startup — not inside load_effective_config (which
    # is called repeatedly through the running process and stays a pure read).
    # Safe to wire in now: every consumer reads through
    # active_media_server_config/get_media_server_provider, which is why this
    # was deferred past checkpoints 3-4 in the first place. See
    # .agents/specs/2026-06-23-media-server-multi-provider-config-design.md.
    migrate_media_server_to_media_servers_on_disk(config_file)
    composition = build_web_runtime_composition(
        base_dir=base_dir,
        config_file=config_file,
        version=__version__,
    )
    prepare_runtime_for_web(composition)
    serve_web_app(composition=composition)


if __name__ == "__main__":
    main()
