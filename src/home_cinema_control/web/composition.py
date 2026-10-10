import logging
from dataclasses import dataclass
from pathlib import Path

from home_cinema_control.application_events import ApplicationEventBus
from home_cinema_control.composition import (
    ApplicationComposition,
    build_application_composition,
)
from home_cinema_control.runtime import (
    RuntimePaths,
    configure_logging,
)
from home_cinema_control.web.api_runtime import WebApiRuntime
from home_cinema_control.web.config_service import WebConfigService
from home_cinema_control.telemetry.service import TelemetryService


@dataclass(frozen=True)
class WebRuntimeComposition:
    application: ApplicationComposition
    api_runtime: WebApiRuntime
    paths: RuntimePaths

    @property
    def runtime(self):
        return self.application.runtime

    @property
    def event_bus(self) -> ApplicationEventBus:
        return self.application.event_bus

    @property
    def event_dispatcher(self):
        """Compatibility alias for callers migrating from the old name."""
        return self.application.event_bus

    @property
    def update_monitor(self):
        return self.application.update_monitor

    @property
    def update_notifications(self):
        return self.application.update_notifications


def build_web_runtime_composition(
    *,
    base_dir: str | Path,
    config_file: str | Path,
    version: str,
) -> WebRuntimeComposition:
    application = build_application_composition(
        base_dir=base_dir,
        config_file=config_file,
        version=version,
    )
    runtime = application.runtime
    runtime_paths = application.paths
    config_service = WebConfigService(runtime=runtime, config_file=runtime_paths.config_file)
    telemetry = TelemetryService(
        config_file=runtime_paths.config_file,
        load_config=runtime.load_config,
        save_config=runtime.save_config,
    )
    api_runtime = WebApiRuntime(
        runtime=runtime,
        config_service=config_service,
        config_file=runtime_paths.config_file,
        log_file=runtime_paths.log_file,
        frontend_dist_dir=runtime_paths.base_dir / "frontend" / "dist",
        telemetry=telemetry,
        home_assistant_delivery_status=application.home_assistant_delivery_status,
    )
    return WebRuntimeComposition(
        application=application,
        api_runtime=api_runtime,
        paths=runtime_paths,
    )


def prepare_runtime_for_web(composition: WebRuntimeComposition) -> None:
    config = composition.runtime.load_config()
    configure_logging(config, composition.paths.log_file)
    composition.api_runtime.telemetry.emit("app_started", config=config)
    composition.runtime.start_playback_listener_if_configured()
    composition.update_monitor.start()


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
