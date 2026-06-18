from home_cinema_control.config.manager import clear_smb_credentials, merge_existing_secrets, sanitize_config_for_web


class WebConfigService:
    def __init__(self, *, runtime, config_file):
        self._runtime = runtime
        self._config_file = config_file

    def load_config(self):
        return self._runtime.load_config()

    def sanitize(self, config):
        return sanitize_config_for_web(config)

    def prepare_submitted_config(self, submitted_config):
        return merge_existing_secrets(self._config_file, submitted_config)

    def save_config(self, config):
        self._runtime.save_config(config)

    def clear_smb_credentials(self):
        clear_smb_credentials(self._config_file)
