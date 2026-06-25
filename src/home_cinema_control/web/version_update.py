import re
import time
from dataclasses import dataclass

import requests


DEFAULT_RELEASE_REPOSITORY = "tousled/home-cinema-control"

_version_cache = None
_version_cache_time: float = 0.0


@dataclass(frozen=True)
class VersionInfo:
    current_version: str
    latest_version: str
    latest_tag: str
    release_url: str
    asset_url: str
    new_version: bool
    error: str = ""

    def as_legacy_response(self) -> dict:
        return {
            "version": self.latest_version,
            "file": self.asset_url,
            "new_version": self.new_version,
            "current_version": self.current_version,
            "latest_tag": self.latest_tag,
            "release_url": self.release_url,
            "error": self.error,
        }


def get_cached_version_info(config, current_version, *, force=False, http_client=requests):
    global _version_cache, _version_cache_time
    interval_hours = (config.get("app") or {}).get("version_check_interval_hours", 24)
    age = time.time() - _version_cache_time
    if not force and _version_cache is not None and age < interval_hours * 3600:
        return _version_cache
    _version_cache = check_application_version(config, current_version, http_client)
    _version_cache_time = time.time()
    return _version_cache


def check_application_version(config, current_version, http_client=requests):
    app = config.get("app") or {}
    repository = app.get("release_repository", DEFAULT_RELEASE_REPOSITORY)
    include_prereleases = bool(app.get("include_prerelease", False))
    timeout = app.get("version_check_timeout_seconds", 10)

    try:
        release = find_latest_release(
            repository,
            include_prereleases=include_prereleases,
            timeout=timeout,
            http_client=http_client,
        )
    except Exception as exc:
        return _current_version_info(current_version, error=str(exc))

    if release is None:
        return _current_version_info(current_version)

    latest_version = normalize_version(release["tag"])
    return VersionInfo(
        current_version=current_version,
        latest_version=latest_version,
        latest_tag=release["tag"],
        release_url=release["url"],
        asset_url=release["asset_url"],
        new_version=is_newer_version(latest_version, current_version),
    )


def trigger_configured_update(config, current_version, http_client=requests):
    app = config.get("app") or {}
    webhook_url = app.get("update_webhook_url", "").strip()
    timeout = app.get("version_check_timeout_seconds", 10)

    if not webhook_url:
        return {
            "success": False,
            "webhook_configured": False,
            "instructions": "docker compose pull && docker compose up -d",
        }

    try:
        response = http_client.post(webhook_url, timeout=timeout)
        response.raise_for_status()
        return {"success": True, "webhook_configured": True}
    except Exception as exc:
        return {"success": False, "webhook_configured": True, "error": str(exc)}


def get_rollback_info(config):
    previous = (config.get("app") or {}).get("previous_version", "").strip()
    if not previous:
        return {"available": False}
    return {
        "available": True,
        "previous_version": previous,
        "instructions": (
            f"HCC_VERSION={previous} docker compose pull"
            f" && HCC_VERSION={previous} docker compose up -d"
        ),
    }


def find_latest_release(
    repository,
    *,
    include_prereleases,
    timeout,
    http_client=requests,
):
    releases_url = f"https://api.github.com/repos/{repository}/releases"
    response = http_client.get(
        releases_url,
        headers={"Accept": "application/vnd.github+json"},
        timeout=timeout,
    )
    response.raise_for_status()

    releases = response.json()
    for release in releases:
        if release.get("draft"):
            continue
        if release.get("prerelease") and not include_prereleases:
            continue

        tag = release.get("tag_name", "")
        if not tag:
            continue

        assets = release.get("assets", [])
        asset_url = assets[0].get("browser_download_url", "") if assets else ""
        return {
            "tag": tag,
            "url": release.get("html_url", ""),
            "asset_url": asset_url,
        }

    return find_latest_tag(
        repository,
        include_prereleases=include_prereleases,
        timeout=timeout,
        http_client=http_client,
    )


def _current_version_info(current_version, *, error=""):
    return VersionInfo(
        current_version=current_version,
        latest_version=current_version,
        latest_tag=current_version,
        release_url="",
        asset_url="",
        new_version=False,
        error=error,
    )


def find_latest_tag(repository, *, include_prereleases, timeout, http_client=requests):
    tags_url = f"https://api.github.com/repos/{repository}/tags"
    response = http_client.get(
        tags_url,
        headers={"Accept": "application/vnd.github+json"},
        timeout=timeout,
    )
    response.raise_for_status()

    for entry in response.json():
        tag = entry.get("name", "")
        if not tag:
            continue
        if is_prerelease_tag(tag) and not include_prereleases:
            continue

        return {
            "tag": tag,
            "url": f"https://github.com/{repository}/releases/tag/{tag}",
            "asset_url": "",
        }

    return None


def is_prerelease_tag(tag):
    return "-" in normalize_version(tag)


def is_newer_version(candidate, current):
    return parse_version(candidate) > parse_version(current)


def normalize_version(version):
    return str(version).strip().removeprefix("v").removeprefix("V")


def parse_version(version):
    normalized = normalize_version(version)
    numbers = [int(part) for part in re.findall(r"\d+", normalized)]
    return tuple(numbers or [0])
