import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from home_cinema_control.web.composition import (
    build_web_runtime_composition,
    serve_web_app,
)


class WebCompositionTest(unittest.TestCase):
    def test_build_web_runtime_composition_wires_api_runtime_and_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            config_file = base_dir / "config.json"
            config_file.write_text("{}", "utf-8")

            composition = build_web_runtime_composition(
                base_dir=base_dir,
                config_file=config_file,
                version="9.9.9",
            )

        self.assertEqual("9.9.9", composition.runtime.version)
        self.assertEqual(config_file, composition.paths.config_file)
        self.assertIs(composition.runtime, composition.api_runtime.runtime)
        self.assertEqual(config_file, composition.api_runtime.config_file)
        self.assertEqual(base_dir / "emby_xnoppo_client_logging.log", composition.api_runtime.log_file)
        self.assertEqual(base_dir / "frontend" / "dist", composition.api_runtime.frontend_dist_dir)

    def test_serve_web_app_uses_fastapi_app_not_legacy_handler(self):
        composition = MagicMock()
        fastapi_app = object()

        with patch(
                "home_cinema_control.web.api_app.create_api_app",
                return_value=fastapi_app,
        ) as create_api_app, patch("uvicorn.run") as run:
            serve_web_app(composition=composition, host="127.0.0.1", port=9999)

        create_api_app.assert_called_once_with(composition.api_runtime)
        run.assert_called_once_with(
            fastapi_app,
            host="127.0.0.1",
            port=9999,
            log_level="warning",
        )


if __name__ == "__main__":
    unittest.main()
