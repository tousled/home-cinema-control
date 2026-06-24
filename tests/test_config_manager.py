import json
import os
import tempfile
import unittest
from pathlib import Path

from home_cinema_control.config.manager import (
    active_media_server_config,
    active_media_server_type,
    get_media_server_provider,
    load_effective_config,
    merge_existing_secrets,
    migrate_media_server_to_media_servers,
    migrate_media_server_to_media_servers_on_disk,
    save_effective_config,
    sanitize_config_for_web,
    upsert_media_server_provider,
    is_configured,
    is_smb_active,
)


class ConfigManagerTest(unittest.TestCase):
    def test_sanitize_config_for_web_removes_media_server_token_values(self):
        sanitized = sanitize_config_for_web(
            {
                "media_servers": {
                    "active": "emby",
                    "providers": {
                        "emby": {
                            "server_url": "http://emby",
                            "display_name": "Pedro",
                            "access_token": "token",
                            "user_id": "user1",
                        }
                    },
                },
                "app": {"release_repository": "tousled/home-cinema-control"},
            }
        )

        provider = sanitized["media_servers"]["providers"]["emby"]
        self.assertEqual("http://emby", provider["server_url"])
        self.assertEqual("Pedro", provider["display_name"])
        self.assertNotIn("access_token", provider)
        self.assertNotIn("user_id", provider)
        self.assertTrue(provider["access_token_configured"])
        self.assertEqual(
            "tousled/home-cinema-control", sanitized["app"]["release_repository"]
        )

    def test_sanitize_config_for_web_removes_legacy_flat_emby_keys(self):
        sanitized = sanitize_config_for_web(
            {
                "media_server": {
                    "type": "emby",
                    "server_url": "http://emby",
                    "access_token": "token",
                    "user_id": "user1",
                },
                "emby_server": "http://legacy",
                "user_name": "legacy-user",
                "user_password": "legacy-password",
                "user_password_configured": True,
            }
        )

        self.assertNotIn("emby_server", sanitized)
        self.assertNotIn("user_name", sanitized)
        self.assertNotIn("user_password", sanitized)
        self.assertNotIn("user_password_configured", sanitized)

    def test_load_effective_config_merges_config_and_nested_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"
            config_file.write_text(
                json.dumps(
                    {
                        "media_server": {
                            "type": "emby",
                            "server_url": "http://emby",
                            "display_name": "Pedro",
                            "access_token_configured": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            secrets_file.write_text(
                json.dumps(
                    {
                        "media_server": {
                            "access_token": "token",
                            "user_id": "user1",
                        }
                    }
                ),
                encoding="utf-8",
            )

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                effective_config = load_effective_config(config_file)
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

        self.assertEqual("http://emby", effective_config["media_server"]["server_url"])
        self.assertEqual("Pedro", effective_config["media_server"]["display_name"])
        self.assertEqual("token", effective_config["media_server"]["access_token"])
        self.assertEqual("user1", effective_config["media_server"]["user_id"])

    def test_save_effective_config_preserves_existing_nested_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"
            config_file.write_text(
                json.dumps(
                    {
                        "media_server": {
                            "type": "emby",
                            "server_url": "http://old",
                            "display_name": "Pedro",
                            "access_token_configured": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            secrets_file.write_text(
                json.dumps(
                    {
                        "media_server": {
                            "access_token": "token",
                            "user_id": "user1",
                        }
                    }
                ),
                encoding="utf-8",
            )

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                save_effective_config(
                    config_file,
                    {
                        "media_server": {
                            "type": "emby",
                            "server_url": "http://new",
                            "display_name": "Pedro",
                            "access_token_configured": True,
                        }
                    },
                )
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

            public_config = json.loads(config_file.read_text(encoding="utf-8"))
            secrets = json.loads(secrets_file.read_text(encoding="utf-8"))

        self.assertEqual("http://new", public_config["media_server"]["server_url"])
        self.assertNotIn("access_token", public_config["media_server"])
        self.assertNotIn("user_id", public_config["media_server"])
        self.assertTrue(public_config["media_server"]["access_token_configured"])
        self.assertEqual("token", secrets["media_server"]["access_token"])
        self.assertEqual("user1", secrets["media_server"]["user_id"])

    def test_is_configured_accepts_token_based_media_server_config(self):
        self.assertTrue(
            is_configured(
                {
                    "media_servers": {
                        "active": "emby",
                        "providers": {
                            "emby": {
                                "server_url": "http://emby",
                                "access_token": "token",
                                "user_id": "user1",
                            }
                        },
                    }
                }
            )
        )

    def test_is_configured_rejects_missing_token(self):
        self.assertFalse(
            is_configured(
                {
                    "media_servers": {
                        "active": "emby",
                        "providers": {
                            "emby": {"server_url": "http://emby", "user_id": "user1"}
                        },
                    }
                }
            )
        )

    def test_is_smb_active_true_when_enabled_without_credentials(self):
        # Anonymous/guest SMB shares are valid; the toggle alone must decide.
        self.assertTrue(
            is_smb_active({"oppo": {"use_smb": True}, "smb": {"username": "", "password": ""}})
        )

    def test_is_smb_active_true_when_enabled_with_credentials(self):
        self.assertTrue(
            is_smb_active(
                {"oppo": {"use_smb": True}, "smb": {"username": "nas_user", "password": "nas_pass"}}
            )
        )

    def test_is_smb_active_false_when_disabled_even_with_credentials(self):
        self.assertFalse(
            is_smb_active(
                {"oppo": {"use_smb": False}, "smb": {"username": "nas_user", "password": "nas_pass"}}
            )
        )

    def test_is_smb_active_false_when_oppo_section_missing(self):
        self.assertFalse(is_smb_active({}))


class MediaServersProvidersTest(unittest.TestCase):
    """Checkpoint 1 of the multi-provider media-server config spec:
    media_servers.providers is a dict keyed by provider type, not a single
    media_server block. See
    .agents/specs/2026-06-23-media-server-multi-provider-config-design.md.
    """

    def test_sanitize_strips_token_from_every_provider_not_just_active(self):
        sanitized = sanitize_config_for_web(
            {
                "media_servers": {
                    "active": "jellyfin",
                    "providers": {
                        "emby": {
                            "server_url": "http://emby",
                            "access_token": "emby-token",
                            "user_id": "emby-user",
                        },
                        "jellyfin": {
                            "server_url": "http://jf",
                            "access_token": "jf-token",
                            "user_id": "jf-user",
                        },
                    },
                }
            }
        )

        providers = sanitized["media_servers"]["providers"]
        self.assertEqual("http://emby", providers["emby"]["server_url"])
        self.assertNotIn("access_token", providers["emby"])
        self.assertNotIn("user_id", providers["emby"])
        self.assertTrue(providers["emby"]["access_token_configured"])
        self.assertNotIn("access_token", providers["jellyfin"])
        self.assertTrue(providers["jellyfin"]["access_token_configured"])

    def test_sanitize_provider_without_token_is_not_configured(self):
        sanitized = sanitize_config_for_web(
            {
                "media_servers": {
                    "active": "emby",
                    "providers": {"jellyfin": {"server_url": "http://jf"}},
                }
            }
        )

        self.assertFalse(
            sanitized["media_servers"]["providers"]["jellyfin"][
                "access_token_configured"
            ]
        )

    def test_load_effective_config_merges_providers_dict_by_key(self):
        # load_effective_config needs no provider-specific code: _deep_merge
        # already merges nested dicts key-by-key, and providers is just another
        # nested dict.
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"
            config_file.write_text(
                json.dumps(
                    {
                        "media_servers": {
                            "active": "jellyfin",
                            "providers": {
                                "emby": {"server_url": "http://emby"},
                                "jellyfin": {"server_url": "http://jf"},
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            secrets_file.write_text(
                json.dumps(
                    {
                        "media_servers": {
                            "providers": {
                                "emby": {
                                    "access_token": "emby-token",
                                    "user_id": "emby-user",
                                },
                                "jellyfin": {
                                    "access_token": "jf-token",
                                    "user_id": "jf-user",
                                },
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                effective_config = load_effective_config(config_file)
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

        providers = effective_config["media_servers"]["providers"]
        self.assertEqual("http://emby", providers["emby"]["server_url"])
        self.assertEqual("emby-token", providers["emby"]["access_token"])
        self.assertEqual("http://jf", providers["jellyfin"]["server_url"])
        self.assertEqual("jf-token", providers["jellyfin"]["access_token"])
        self.assertEqual("jf-user", providers["jellyfin"]["user_id"])

    def test_save_effective_config_splits_each_provider_into_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                save_effective_config(
                    config_file,
                    {
                        "media_servers": {
                            "active": "jellyfin",
                            "providers": {
                                "emby": {
                                    "server_url": "http://emby",
                                    "access_token": "emby-token",
                                    "user_id": "emby-user",
                                },
                                "jellyfin": {
                                    "server_url": "http://jf",
                                    "access_token": "jf-token",
                                    "user_id": "jf-user",
                                },
                            },
                        }
                    },
                )
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

            public_config = json.loads(config_file.read_text(encoding="utf-8"))
            secrets = json.loads(secrets_file.read_text(encoding="utf-8"))

        public_providers = public_config["media_servers"]["providers"]
        self.assertEqual("http://emby", public_providers["emby"]["server_url"])
        self.assertNotIn("access_token", public_providers["emby"])
        self.assertNotIn("user_id", public_providers["emby"])
        self.assertTrue(public_providers["emby"]["access_token_configured"])
        self.assertTrue(public_providers["jellyfin"]["access_token_configured"])

        secret_providers = secrets["media_servers"]["providers"]
        self.assertEqual("emby-token", secret_providers["emby"]["access_token"])
        self.assertEqual("emby-user", secret_providers["emby"]["user_id"])
        self.assertEqual("jf-token", secret_providers["jellyfin"]["access_token"])
        self.assertEqual("jf-user", secret_providers["jellyfin"]["user_id"])

    def test_save_effective_config_preserves_other_provider_secret_when_one_unconfigured(
            self,
    ):
        # Configuring/saving Emby must never touch Jellyfin's already-stored
        # secret — the whole point of per-provider persistence.
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"
            secrets_file.write_text(
                json.dumps(
                    {
                        "media_servers": {
                            "providers": {
                                "jellyfin": {
                                    "access_token": "jf-token",
                                    "user_id": "jf-user",
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                save_effective_config(
                    config_file,
                    {
                        "media_servers": {
                            "active": "emby",
                            "providers": {
                                "emby": {
                                    "server_url": "http://emby",
                                    "access_token": "emby-token",
                                    "user_id": "emby-user",
                                }
                            },
                        }
                    },
                )
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

            secrets = json.loads(secrets_file.read_text(encoding="utf-8"))

        secret_providers = secrets["media_servers"]["providers"]
        self.assertEqual("emby-token", secret_providers["emby"]["access_token"])
        self.assertEqual("jf-token", secret_providers["jellyfin"]["access_token"])
        self.assertEqual("jf-user", secret_providers["jellyfin"]["user_id"])

    def test_merge_existing_secrets_fills_blank_provider_token_from_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"
            secrets_file.write_text(
                json.dumps(
                    {
                        "media_servers": {
                            "providers": {
                                "emby": {
                                    "access_token": "stored-token",
                                    "user_id": "stored-user",
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                merged = merge_existing_secrets(
                    config_file,
                    {
                        "media_servers": {
                            "active": "emby",
                            "providers": {
                                "emby": {"server_url": "http://emby", "access_token": ""}
                            },
                        }
                    },
                )
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

        provider = merged["media_servers"]["providers"]["emby"]
        self.assertEqual("stored-token", provider["access_token"])
        self.assertEqual("stored-user", provider["user_id"])

    def test_merge_existing_secrets_does_not_touch_provider_with_no_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"
            secrets_file.write_text(json.dumps({}), encoding="utf-8")

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                merged = merge_existing_secrets(
                    config_file,
                    {
                        "media_servers": {
                            "active": "jellyfin",
                            "providers": {"jellyfin": {"server_url": "http://jf"}},
                        }
                    },
                )
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

        provider = merged["media_servers"]["providers"]["jellyfin"]
        self.assertNotIn("access_token", provider)


class MigrateMediaServerToMediaServersTest(unittest.TestCase):
    """Checkpoint 2: the pure transform function, plus the file-level wrapper
    with backups. Neither is wired into web/main.py yet — see
    .agents/specs/2026-06-23-media-server-multi-provider-config-design.md.
    """

    def test_migrates_old_shape_into_new_shape(self):
        public_config = {
            "media_server": {
                "type": "jellyfin",
                "server_url": "http://jf",
                "display_name": "Pedro",
                "access_token_configured": True,
            }
        }
        secrets = {
            "media_server": {"access_token": "jf-token", "user_id": "jf-user"}
        }

        migrated = migrate_media_server_to_media_servers(public_config, secrets)

        self.assertTrue(migrated)
        self.assertNotIn("media_server", public_config)
        self.assertEqual("jellyfin", public_config["media_servers"]["active"])
        provider = public_config["media_servers"]["providers"]["jellyfin"]
        self.assertEqual("http://jf", provider["server_url"])
        self.assertEqual("Pedro", provider["display_name"])

        self.assertNotIn("media_server", secrets)
        secret_provider = secrets["media_servers"]["providers"]["jellyfin"]
        self.assertEqual("jf-token", secret_provider["access_token"])
        self.assertEqual("jf-user", secret_provider["user_id"])

    def test_defaults_to_emby_when_type_missing(self):
        public_config = {"media_server": {"server_url": "http://emby"}}
        secrets = {}

        migrate_media_server_to_media_servers(public_config, secrets)

        self.assertEqual("emby", public_config["media_servers"]["active"])
        self.assertIn("emby", public_config["media_servers"]["providers"])

    def test_migrates_even_when_media_servers_already_present_but_empty(self):
        # Real bug, found testing against a real Docker volume: media_servers
        # is a declared field with its own Pydantic default, so an unrelated
        # save before this function was wired in could already have written
        # the bare default ({"active": "emby", "providers": {}}) to disk.
        # Gating on "media_servers present" would treat that as "already
        # migrated" forever and strand the real data in media_server.
        public_config = {
            "media_servers": {"active": "emby", "providers": {}},
            "media_server": {
                "type": "jellyfin",
                "server_url": "http://real-jellyfin",
                "display_name": "tousled",
            },
        }
        secrets = {}

        migrated = migrate_media_server_to_media_servers(public_config, secrets)

        self.assertTrue(migrated)
        self.assertNotIn("media_server", public_config)
        self.assertEqual("jellyfin", public_config["media_servers"]["active"])
        self.assertEqual(
            "http://real-jellyfin",
            public_config["media_servers"]["providers"]["jellyfin"]["server_url"],
        )

    def test_does_not_overwrite_active_when_another_provider_already_has_real_data(self):
        # If media_servers already holds real data for a different provider
        # (shouldn't normally happen post-migration, but defends against it
        # anyway), draining a legacy leftover must not silently flip away
        # from it.
        public_config = {
            "media_servers": {
                "active": "jellyfin",
                "providers": {"jellyfin": {"server_url": "http://real-jellyfin"}},
            },
            "media_server": {
                "type": "emby",
                "server_url": "http://leftover-emby",
            },
        }
        secrets = {}

        migrated = migrate_media_server_to_media_servers(public_config, secrets)

        self.assertTrue(migrated)
        self.assertEqual("jellyfin", public_config["media_servers"]["active"])
        self.assertEqual(
            "http://leftover-emby",
            public_config["media_servers"]["providers"]["emby"]["server_url"],
        )

    def test_noop_when_media_server_has_no_real_data_left(self):
        public_config = {
            "media_servers": {"active": "emby", "providers": {}},
            "media_server": {"type": "emby", "server_url": "", "display_name": ""},
        }
        secrets = {}

        migrated = migrate_media_server_to_media_servers(public_config, secrets)

        self.assertFalse(migrated)

    def test_noop_on_fresh_install_with_no_media_server_block(self):
        public_config = {"app": {"log_level": 1}}
        secrets = {}

        migrated = migrate_media_server_to_media_servers(public_config, secrets)

        self.assertFalse(migrated)
        self.assertNotIn("media_servers", public_config)

    def test_noop_when_secrets_have_no_media_server_block(self):
        public_config = {"media_server": {"type": "emby", "server_url": "http://x"}}
        secrets = {}

        migrate_media_server_to_media_servers(public_config, secrets)

        self.assertNotIn("media_servers", secrets)

    def test_on_disk_wrapper_writes_backups_and_migrates(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"
            config_file.write_text(
                json.dumps(
                    {
                        "media_server": {
                            "type": "emby",
                            "server_url": "http://emby",
                            "display_name": "Pedro",
                        }
                    }
                ),
                encoding="utf-8",
            )
            secrets_file.write_text(
                json.dumps(
                    {"media_server": {"access_token": "tok", "user_id": "usr"}}
                ),
                encoding="utf-8",
            )

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                migrated = migrate_media_server_to_media_servers_on_disk(config_file)
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

            self.assertTrue(migrated)

            config_backup = Path(str(config_file) + ".bak-migrate")
            secrets_backup = Path(str(secrets_file) + ".bak-migrate")
            self.assertTrue(config_backup.exists())
            self.assertTrue(secrets_backup.exists())

            backed_up_public = json.loads(config_backup.read_text(encoding="utf-8"))
            self.assertEqual(
                "http://emby", backed_up_public["media_server"]["server_url"]
            )

            new_public = json.loads(config_file.read_text(encoding="utf-8"))
            self.assertNotIn("media_server", new_public)
            self.assertEqual("http://emby", new_public["media_servers"]["providers"]["emby"]["server_url"])

            new_secrets = json.loads(secrets_file.read_text(encoding="utf-8"))
            self.assertEqual(
                "tok", new_secrets["media_servers"]["providers"]["emby"]["access_token"]
            )

    def test_on_disk_wrapper_is_noop_on_second_call(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"
            config_file.write_text(
                json.dumps({"media_server": {"type": "emby", "server_url": "http://emby"}}),
                encoding="utf-8",
            )
            secrets_file.write_text(json.dumps({}), encoding="utf-8")

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                first = migrate_media_server_to_media_servers_on_disk(config_file)
                second = migrate_media_server_to_media_servers_on_disk(config_file)
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

        self.assertTrue(first)
        self.assertFalse(second)

    def test_on_disk_wrapper_recovers_real_install_with_premature_empty_media_servers(
            self,
    ):
        # Exact shape found on a real Docker volume: media_servers already
        # present with the bare Pydantic default (from an unrelated save
        # before this function was wired into web/main.py), real data still
        # sitting in media_server. Must still migrate, not no-op.
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"
            config_file.write_text(
                json.dumps(
                    {
                        "media_server": {
                            "type": "jellyfin",
                            "server_url": "http://192.168.50.110:28096",
                            "display_name": "tousled",
                        },
                        "media_servers": {"active": "emby", "providers": {}},
                    }
                ),
                encoding="utf-8",
            )
            secrets_file.write_text(
                json.dumps(
                    {"media_server": {"access_token": "tok", "user_id": "usr"}}
                ),
                encoding="utf-8",
            )

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                migrated = migrate_media_server_to_media_servers_on_disk(config_file)
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

            new_public = json.loads(config_file.read_text(encoding="utf-8"))
            new_secrets = json.loads(secrets_file.read_text(encoding="utf-8"))

        self.assertTrue(migrated)
        self.assertNotIn("media_server", new_public)
        self.assertEqual("jellyfin", new_public["media_servers"]["active"])
        self.assertEqual(
            "http://192.168.50.110:28096",
            new_public["media_servers"]["providers"]["jellyfin"]["server_url"],
        )
        self.assertEqual(
            "tok",
            new_secrets["media_servers"]["providers"]["jellyfin"]["access_token"],
        )


class MediaServerProviderHelpersTest(unittest.TestCase):
    """Checkpoint 3: active_media_server_config / get_media_server_provider /
    upsert_media_server_provider, plus is_configured migrated to use them.
    """

    def test_get_media_server_provider_reads_migrated_shape(self):
        config = {
            "media_servers": {
                "active": "jellyfin",
                "providers": {
                    "jellyfin": {"server_url": "http://jf", "access_token": "tok"}
                },
            }
        }

        provider = get_media_server_provider(config, "jellyfin")

        self.assertEqual("http://jf", provider.server_url)
        self.assertEqual("tok", provider.access_token)

    def test_get_media_server_provider_returns_empty_when_absent(self):
        provider = get_media_server_provider({}, "jellyfin")
        self.assertEqual("", provider.server_url)
        self.assertEqual("", provider.access_token)

    def test_active_media_server_config_resolves_active_pointer(self):
        config = {
            "media_servers": {
                "active": "jellyfin",
                "providers": {
                    "emby": {"server_url": "http://emby"},
                    "jellyfin": {"server_url": "http://jf"},
                },
            }
        }

        self.assertEqual("http://jf", active_media_server_config(config).server_url)

    def test_active_media_server_type_migrated_reads_active_pointer(self):
        config = {
            "media_servers": {
                "active": "jellyfin",
                "providers": {"jellyfin": {"server_url": "http://jf"}},
            }
        }
        self.assertEqual("jellyfin", active_media_server_type(config))

    def test_upsert_media_server_provider_partial_update_preserves_other_fields(self):
        config = {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"server_url": "http://emby", "display_name": "Pedro"}
                },
            }
        }

        updated = upsert_media_server_provider(config, "emby", access_token="new-tok")

        emby = updated.media_servers.providers["emby"]
        self.assertEqual("http://emby", emby.server_url)
        self.assertEqual("Pedro", emby.display_name)
        self.assertEqual("new-tok", emby.access_token)

    def test_upsert_media_server_provider_creates_entry_when_absent(self):
        updated = upsert_media_server_provider({}, "jellyfin", server_url="http://jf")

        self.assertEqual(
            "http://jf", updated.media_servers.providers["jellyfin"].server_url
        )

    def test_upsert_media_server_provider_does_not_touch_other_providers(self):
        config = {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"server_url": "http://emby"},
                    "jellyfin": {"server_url": "http://jf", "access_token": "jf-tok"},
                },
            }
        }

        updated = upsert_media_server_provider(config, "emby", access_token="new-tok")

        jellyfin = updated.media_servers.providers["jellyfin"]
        self.assertEqual("http://jf", jellyfin.server_url)
        self.assertEqual("jf-tok", jellyfin.access_token)

    def test_is_configured_reads_migrated_shape(self):
        self.assertTrue(
            is_configured(
                {
                    "media_servers": {
                        "active": "jellyfin",
                        "providers": {
                            "jellyfin": {
                                "server_url": "http://jf",
                                "access_token": "tok",
                                "user_id": "user1",
                            }
                        },
                    }
                }
            )
        )

if __name__ == "__main__":
    unittest.main()