from home_cinema_control.config.manager import (
    active_media_server_config,
    clear_smb_credentials,
    merge_existing_secrets,
    sanitize_config_for_web,
)
from home_cinema_control.config.models import (
    AppConfig,
    AvConfig,
    HccConfig,
    MediaServerProviderConfig,
    OppoConfig,
    TvConfig,
)
from home_cinema_control.media_servers.common.models import MediaServerProviderType


class WebConfigService:
    def __init__(self, *, runtime, config_file):
        self._runtime = runtime
        self._config_file = config_file

    def load_config(self):
        return self._runtime.load_config()

    def load_model(self, config=None) -> HccConfig:
        source = config if config is not None else self.load_config()
        return HccConfig.model_validate(source)

    def app(self, config=None) -> AppConfig:
        return self.load_model(config).app

    def with_app_updates(self, config: dict, **updates) -> dict:
        app_config = self.app(config).model_copy(update=updates)
        return {**config, "app": app_config.model_dump()}

    def av_receiver(self, config=None) -> AvConfig:
        return self.load_model(config).av

    def tv(self, config=None) -> TvConfig:
        return self.load_model(config).tv

    def oppo(self, config=None) -> OppoConfig:
        return self.load_model(config).oppo

    def active_media_server(self, config=None) -> MediaServerProviderConfig:
        return active_media_server_config(self.load_model(config))

    def active_media_server_type(self, config=None) -> MediaServerProviderType:
        return self.load_model(config).media_servers.active

    def sanitized_config(self):
        return self.sanitize(self.load_config())

    def sanitize(self, config):
        return sanitize_config_for_web(config)

    def prepare_submitted_config(self, submitted_config):
        return merge_existing_secrets(self._config_file, submitted_config)

    def save_config(self, config):
        self._runtime.save_config(config)

    def clear_smb_credentials(self):
        clear_smb_credentials(self._config_file)
