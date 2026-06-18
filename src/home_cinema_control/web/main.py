from pathlib import Path

from home_cinema_control import __version__
from home_cinema_control.config.manager import ensure_config_exists
from home_cinema_control.web.composition import (
    build_web_runtime_composition,
    prepare_runtime_for_web,
    serve_web_app,
)


def main() -> None:
    base_dir = Path.cwd()
    config_file = ensure_config_exists()
    composition = build_web_runtime_composition(
        base_dir=base_dir,
        config_file=config_file,
        version=__version__,
    )
    prepare_runtime_for_web(composition)
    serve_web_app(composition=composition)


if __name__ == "__main__":
    main()
