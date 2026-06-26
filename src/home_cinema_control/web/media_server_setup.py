from home_cinema_control.config.models import HccConfig


def media_server_setup_service(media_server_provider_factory, config: dict):
    validated_config = HccConfig.model_validate(config)
    return media_server_provider_factory.create(validated_config).setup_service()
