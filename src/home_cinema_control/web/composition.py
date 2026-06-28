import logging
from dataclasses import dataclass
from pathlib import Path

from home_cinema_control.runtime import (
    HomeCinemaControlRuntime,
    RuntimePaths,
    build_runtime_paths,
    configure_logging,
)
from home_cinema_control.web.api_runtime import WebApiRuntime
from home_cinema_control.web.config_service import WebConfigService
from home_cinema_control.telemetry.service import TelemetryService


@dataclass(frozen=True)
class WebRuntimeComposition:
    runtime: HomeCinemaControlRuntime
    api_runtime: WebApiRuntime
    paths: RuntimePaths


def build_web_runtime_composition(
    *,
    base_dir: str | Path,
    config_file: str | Path,
    version: str,
) -> WebRuntimeComposition:
    runtime_paths = build_runtime_paths(base_dir, config_file)
    runtime = HomeCinemaControlRuntime(paths=runtime_paths, version=version)
    config_service = WebConfigService(runtime=runtime, config_file=runtime_paths.config_file)
    api_runtime = WebApiRuntime(
        runtime=runtime,
        config_service=config_service,
        config_file=runtime_paths.config_file,
        log_file=runtime_paths.log_file,
        frontend_dist_dir=runtime_paths.base_dir / "frontend" / "dist",
    )
    return WebRuntimeComposition(runtime=runtime, api_runtime=api_runtime, paths=runtime_paths)


def prepare_runtime_for_web(composition: WebRuntimeComposition) -> None:
    config = composition.runtime.load_config()
    configure_logging(config, composition.paths.log_file)
    telemetry = TelemetryService(
        config_file=composition.paths.config_file,
        load_config=composition.runtime.load_config,
        save_config=composition.runtime.save_config,
    )
    telemetry.emit("app_started", config=config)
    telemetry.emit_heartbeat_if_due()
    composition.runtime.start_playback_listener_if_configured()


def serve_web_app(
    *,
    composition: WebRuntimeComposition,
    host: str = "0.0.0.0",
    port: int = 8090,
) -> None:
    import uvicorn
    from home_cinema_control.web.api_app import create_api_app

    logging.info("Starting FastAPI server on http://%s:%s", host, port)
    app = create_api_app(composition.api_runtime)
    uvicorn.run(app, host=host, port=port, log_level="warning")
