from dataclasses import dataclass
from pathlib import Path

from home_cinema_control.runtime import HomeCinemaControlRuntime
from home_cinema_control.web.config_service import WebConfigService


@dataclass(frozen=True)
class WebApiRuntime:
    runtime: HomeCinemaControlRuntime
    config_service: WebConfigService
    config_file: Path
    log_file: Path
    frontend_dist_dir: Path
