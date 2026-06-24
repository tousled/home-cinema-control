from __future__ import annotations

from types import ModuleType

from home_cinema_control.config.models import HccConfig
from home_cinema_control.media_servers.common.models import MediaServerLoginCredentials


class ModuleMediaServerSetupService:
    """Typed setup seam around provider-specific setup modules.

    Provider setup modules still own their HTTP/API details. This adapter owns
    the HCC-facing interface: validate config and credentials once at the seam,
    and return updated config dictionaries to the web layer.
    """

    def __init__(self, module: ModuleType):
        self._module = module

    def configure_token(
        self,
        config: HccConfig | dict,
        credentials: MediaServerLoginCredentials | dict,
    ) -> dict:
        return self._module.configure_token(
            _validated_config_dict(config),
            MediaServerLoginCredentials.model_validate(credentials),
        )

    def check_connection(self, config: HccConfig | dict):
        return self._module.check_connection(_validated_config_dict(config))

    def load_devices(self, config: HccConfig | dict) -> dict:
        updated = _validated_config_dict(config)
        return self._module.load_devices(updated)

    def load_libraries(self, config: HccConfig | dict) -> dict:
        updated = _validated_config_dict(config)
        return self._module.load_libraries(updated)

    def load_selectable_folders(self, config: HccConfig | dict) -> dict:
        updated = _validated_config_dict(config)
        return self._module.load_selectable_folders(updated)

    def fetch_library_paths(self, config: HccConfig | dict) -> list[dict]:
        return self._module.fetch_library_paths(_validated_config_dict(config))


def _validated_config_dict(config: HccConfig | dict) -> dict:
    if isinstance(config, HccConfig):
        return config.model_dump()
    return HccConfig(**config).model_dump()
