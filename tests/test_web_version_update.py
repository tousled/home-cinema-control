import unittest

import home_cinema_control.web.version_update as version_update_module
from home_cinema_control.web.version_update import (
    check_application_version,
    display_version,
    find_previous_version,
    get_cached_version_info,
    get_rollback_info,
    is_fallback_version,
    is_newer_version,
    trigger_configured_update,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttpClient:
    def __init__(self, releases, tags=None, post_status=204):
        self.releases = releases
        self.tags = tags or []
        self.post_status = post_status
        self.get_calls = []
        self.post_calls = []

    def get(self, url, headers=None, timeout=None):
        self.get_calls.append((url, headers, timeout))
        if url.endswith("/releases"):
            return FakeResponse(self.releases)
        if url.endswith("/tags"):
            return FakeResponse(self.tags)
        raise AssertionError(f"Unexpected URL: {url}")

    def post(self, url, timeout=None):
        self.post_calls.append(url)
        return FakeResponse({}, status_code=self.post_status)

class FailingHttpClient:
    def get(self, url, headers=None, timeout=None):
        raise RuntimeError("network down")


class WebVersionUpdateTest(unittest.TestCase):
    def test_version_comparison_handles_semver_numbers(self):
        self.assertTrue(is_newer_version("0.5.10", "0.5.2"))
        self.assertFalse(is_newer_version("0.5.1", "0.5.1"))
        self.assertTrue(is_newer_version("v0.6.0", "0.5.1"))
        self.assertTrue(is_newer_version("1.1.1", "1.1.1-rc.1"))
        self.assertTrue(is_newer_version("1.1.1-rc.2", "1.1.1-rc.1"))
        self.assertFalse(is_newer_version("1.1.1-rc.1", "1.1.1"))

    def test_display_version_formats_pep440_release_candidates_as_docker_tags(self):
        self.assertEqual("1.1.1-rc.1", display_version("1.1.1rc1"))
        self.assertEqual("0.0.0-dev.0", display_version("0.0.0.dev0"))

    def test_fallback_versions_are_not_real_rollback_targets(self):
        self.assertTrue(is_fallback_version("0.0.0.dev0"))
        self.assertTrue(is_fallback_version("0.0.0-dev.0"))
        self.assertFalse(is_fallback_version("1.1.0"))

    def test_check_version_uses_latest_non_prerelease_release_by_default(self):
        http = FakeHttpClient(
            releases=[
                {"tag_name": "v0.6.0-beta.1", "prerelease": True, "draft": False},
                {
                    "tag_name": "v0.5.2",
                    "prerelease": False,
                    "draft": False,
                    "html_url": "https://github/release",
                    "assets": [{"browser_download_url": "https://asset"}],
                },
            ]
        )

        result = check_application_version(
            {
                "app": {
                    "release_repository": "owner/repo",
                    "include_prerelease": False,
                    "version_check_timeout_seconds": 3,
                }
            },
            "0.5.1",
            http,
        )

        self.assertTrue(result.new_version)
        self.assertEqual("0.5.2", result.latest_version)
        self.assertEqual("v0.5.2", result.latest_tag)
        self.assertEqual("https://asset", result.asset_url)
        self.assertEqual(
            "https://api.github.com/repos/owner/repo/releases",
            http.get_calls[0][0],
        )
        self.assertEqual(3, http.get_calls[0][2])

    def test_check_version_can_include_prereleases(self):
        http = FakeHttpClient(
            releases=[
                {
                    "tag_name": "v0.6.0-beta.1",
                    "prerelease": True,
                    "draft": False,
                    "html_url": "https://github/beta",
                    "assets": [],
                },
                {"tag_name": "v0.5.2", "prerelease": False, "draft": False},
            ]
        )

        result = check_application_version(
            {"app": {"release_repository": "owner/repo", "include_prerelease": True}},
            "0.5.1",
            http,
        )

        self.assertTrue(result.new_version)
        self.assertEqual("0.6.0-beta.1", result.latest_version)
        self.assertEqual("https://github/beta", result.release_url)

    def test_check_version_falls_back_to_tags_when_no_release_matches(self):
        http = FakeHttpClient(
            releases=[{"tag_name": "v0.6.0-beta.1", "prerelease": True}],
            tags=[{"name": "v0.5.2"}],
        )

        result = check_application_version(
            {"app": {"release_repository": "owner/repo", "include_prerelease": False}},
            "0.5.1",
            http,
        )

        self.assertTrue(result.new_version)
        self.assertEqual("0.5.2", result.latest_version)
        self.assertEqual(
            "https://api.github.com/repos/owner/repo/tags",
            http.get_calls[1][0],
        )

    def test_check_version_skips_prerelease_tags_when_no_releases_exist(self):
        # Regression: repo has no GitHub Releases (release.yml only pushes Docker
        # images), so the tags fallback is the only path ever taken. It must not
        # surface a "1.1.0-rc.1"-style tag when include_prerelease is False.
        http = FakeHttpClient(
            releases=[],
            tags=[{"name": "1.1.0-rc.1"}, {"name": "1.0.5"}, {"name": "1.0.4"}],
        )

        result = check_application_version(
            {"app": {"release_repository": "owner/repo", "include_prerelease": False}},
            "1.0.5",
            http,
        )

        self.assertEqual("1.0.5", result.latest_version)
        self.assertFalse(result.new_version)

    def test_check_version_can_surface_prerelease_tags_when_enabled(self):
        http = FakeHttpClient(
            releases=[],
            tags=[{"name": "1.1.0-rc.1"}, {"name": "1.0.5"}],
        )

        result = check_application_version(
            {"app": {"release_repository": "owner/repo", "include_prerelease": True}},
            "1.0.5",
            http,
        )

        self.assertEqual("1.1.0-rc.1", result.latest_version)
        self.assertTrue(result.new_version)

    def test_check_version_formats_current_pep440_version_for_display(self):
        http = FakeHttpClient(releases=[], tags=[{"name": "1.1.1-rc.1"}])

        result = check_application_version(
            {"app": {"release_repository": "owner/repo", "include_prerelease": True}},
            "1.1.1rc1",
            http,
        )

        self.assertEqual("1.1.1-rc.1", result.current_version)
        self.assertEqual("1.1.1-rc.1", result.latest_version)
        self.assertFalse(result.new_version)

    def test_check_version_reports_errors_without_breaking_web_response(self):
        result = check_application_version(
            {"app": {"release_repository": "owner/repo"}},
            "0.5.1",
            FailingHttpClient(),
        )

        self.assertFalse(result.new_version)
        self.assertEqual("0.5.1", result.latest_version)
        self.assertEqual("network down", result.error)

    def test_update_without_webhook_returns_instructions(self):
        http = FakeHttpClient(
            releases=[
                {"tag_name": "v0.5.2", "prerelease": False, "draft": False},
            ]
        )

        result = trigger_configured_update(
            {"app": {"release_repository": "owner/repo"}},
            "0.5.1",
            http,
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["webhook_configured"])
        self.assertIn("docker compose pull", result["instructions"])
        self.assertEqual([], http.post_calls)

    def test_update_with_webhook_posts_and_returns_success(self):
        http = FakeHttpClient(releases=[])

        result = trigger_configured_update(
            {"app": {"update_webhook_url": "https://example.com/webhook"}},
            "0.5.1",
            http,
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["webhook_configured"])
        self.assertEqual(["https://example.com/webhook"], http.post_calls)


    def test_cache_is_invalidated_when_include_prerelease_changes(self):
        # Regression: cache was keyed only by time, so toggling include_prerelease
        # had no effect until the cache expired (default 24 h) or container restart.
        version_update_module._version_cache = None
        version_update_module._version_cache_time = 0.0
        version_update_module._version_cache_include_prerelease = None

        tags_only = [{"name": "1.1.0-rc.1"}, {"name": "1.0.5"}]
        http = FakeHttpClient(releases=[], tags=tags_only)

        config_no_pre = {"app": {"release_repository": "owner/repo", "include_prerelease": False}}
        result1 = get_cached_version_info(config_no_pre, "1.0.4", http_client=http)
        self.assertEqual("1.0.5", result1.latest_version)
        calls_after_first = len(http.get_calls)

        # Same setting → cache hit, no new HTTP call.
        get_cached_version_info(config_no_pre, "1.0.4", http_client=http)
        self.assertEqual(calls_after_first, len(http.get_calls))

        # Toggle include_prerelease → cache must be invalidated.
        config_with_pre = {"app": {"release_repository": "owner/repo", "include_prerelease": True}}
        result2 = get_cached_version_info(config_with_pre, "1.0.4", http_client=http)
        self.assertGreater(len(http.get_calls), calls_after_first)
        self.assertEqual("1.1.0-rc.1", result2.latest_version)

    def test_rollback_info_not_available_when_no_previous_version(self):
        result = get_rollback_info({"app": {}})
        self.assertFalse(result["available"])

    def test_rollback_info_returns_compose_command_with_version_env_var(self):
        result = get_rollback_info({"app": {"previous_version": "0.8.0"}})
        self.assertTrue(result["available"])
        self.assertEqual("0.8.0", result["previous_version"])
        self.assertIn("HCC_VERSION=0.8.0", result["instructions"])
        self.assertIn("docker compose pull", result["instructions"])
        self.assertIn("docker compose up -d", result["instructions"])

    def test_rollback_info_formats_stored_pep440_previous_version(self):
        result = get_rollback_info({"app": {"previous_version": "1.1.1rc1"}})

        self.assertTrue(result["available"])
        self.assertEqual("1.1.1-rc.1", result["previous_version"])
        self.assertIn("HCC_VERSION=1.1.1-rc.1", result["instructions"])

    def test_rollback_info_derives_previous_stable_version_when_config_has_fallback(self):
        http = FakeHttpClient(
            releases=[
                {"tag_name": "1.1.1-rc.1", "prerelease": True, "draft": False},
                {"tag_name": "1.1.0", "prerelease": False, "draft": False},
            ],
            tags=[{"name": "1.1.1-rc.1"}, {"name": "1.1.0"}, {"name": "1.0.9"}],
        )

        result = get_rollback_info(
            {
                "app": {
                    "previous_version": "0.0.0.dev0",
                    "release_repository": "owner/repo",
                    "include_prerelease": False,
                }
            },
            "1.1.1rc1",
            http,
        )

        self.assertTrue(result["available"])
        self.assertEqual("1.1.0", result["previous_version"])

    def test_find_previous_version_can_include_prerelease_tags(self):
        http = FakeHttpClient(
            releases=[],
            tags=[
                {"name": "1.1.1-rc.1"},
                {"name": "1.1.0"},
                {"name": "1.1.0-rc.5"},
                {"name": "1.1.0-rc.4"},
            ],
        )

        result = find_previous_version(
            {"app": {"release_repository": "owner/repo", "include_prerelease": True}},
            "1.1.1rc1",
            http,
        )

        self.assertEqual("1.1.0", result)

    def test_find_previous_version_uses_latest_prerelease_when_no_stable_exists(self):
        http = FakeHttpClient(
            releases=[],
            tags=[
                {"name": "1.1.1-rc.1"},
                {"name": "1.1.0-rc.5"},
                {"name": "1.1.0-rc.4"},
            ],
        )

        result = find_previous_version(
            {"app": {"release_repository": "owner/repo", "include_prerelease": True}},
            "1.1.1rc1",
            http,
        )

        self.assertEqual("1.1.0-rc.5", result)


if __name__ == "__main__":
    unittest.main()
