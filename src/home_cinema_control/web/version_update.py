import re
import time
from dataclasses import dataclass

import requests


DEFAULT_RELEASE_REPOSITORY = "tousled/home-cinema-control"

_version_cache = None
_version_cache_time: float = 0.0
_version_cache_include_prerelease: bool | None = None


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
    global _version_cache, _version_cache_time, _version_cache_include_prerelease
    app = config.get("app") or {}
    interval_hours = app.get("version_check_interval_hours", 24)
    include_prerelease = bool(app.get("include_prerelease", False))
    age = time.time() - _version_cache_time
    prerelease_changed = include_prerelease != _version_cache_include_prerelease
    if not force and not prerelease_changed and _version_cache is not None and age < interval_hours * 3600:
        return _version_cache
    _version_cache = check_application_version(config, current_version, http_client)
    _version_cache_time = time.time()
    _version_cache_include_prerelease = include_prerelease
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

    latest_version = display_version(release["tag"])
    current_display_version = display_version(current_version)
    return VersionInfo(
        current_version=current_display_version,
        latest_version=latest_version,
        latest_tag=release["tag"],
        release_url=release["url"],
        asset_url=release["asset_url"],
        new_version=is_newer_version(latest_version, current_display_version),
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


def get_rollback_info(config, current_version="", http_client=requests):
    previous = display_version((config.get("app") or {}).get("previous_version", ""))
    if is_fallback_version(previous):
        previous = ""
    if not previous and current_version:
        previous = find_previous_version(config, current_version, http_client=http_client)
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
    release = find_release_for_channel(releases, include_prereleases)
    if release is not None:
        tag = release.get("tag_name", "")
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


def find_previous_version(config, current_version, http_client=requests):
    app = config.get("app") or {}
    repository = app.get("release_repository", DEFAULT_RELEASE_REPOSITORY)
    include_prereleases = bool(app.get("include_prerelease", False))
    timeout = app.get("version_check_timeout_seconds", 10)
    current_display = display_version(current_version)

    try:
        candidates = list_release_candidates(
            repository,
            include_prereleases=include_prereleases,
            timeout=timeout,
            http_client=http_client,
        )
    except Exception:
        return ""

    previous_candidates = [
        candidate
        for candidate in candidates
        if is_newer_version(current_display, candidate) and not is_fallback_version(candidate)
    ]
    prerelease_previous = find_previous_for_prerelease(current_display, candidates)
    if prerelease_previous:
        return prerelease_previous
    if not previous_candidates:
        return ""
    return max(previous_candidates, key=parse_version)


def list_release_candidates(
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

    candidates = []
    for release in response.json():
        if release.get("draft"):
            continue
        tag = release.get("tag_name", "")
        if tag and should_include_history_version_tag(tag, include_prereleases):
            candidates.append(display_version(tag))

    tags_url = f"https://api.github.com/repos/{repository}/tags"
    response = http_client.get(
        tags_url,
        headers={"Accept": "application/vnd.github+json"},
        timeout=timeout,
    )
    response.raise_for_status()

    seen = set(candidates)
    for entry in response.json():
        tag = display_version(entry.get("name", ""))
        if not tag or tag in seen:
            continue
        if not should_include_history_version_tag(tag, include_prereleases):
            continue
        candidates.append(tag)
        seen.add(tag)

    return candidates


def _current_version_info(current_version, *, error=""):
    current_display_version = display_version(current_version)
    return VersionInfo(
        current_version=current_display_version,
        latest_version=current_display_version,
        latest_tag=current_display_version,
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

    tags = [entry.get("name", "") for entry in response.json()]
    tag = find_tag_for_channel(tags, include_prereleases)
    if tag:
        return {
            "tag": tag,
            "url": f"https://github.com/{repository}/releases/tag/{tag}",
            "asset_url": "",
        }

    return None


def find_release_for_channel(releases, include_prereleases):
    matching_releases = [
        release
        for release in releases
        if is_available_release(release, include_prereleases=include_prereleases)
    ]
    if not matching_releases:
        return None
    return max(matching_releases, key=lambda release: parse_version(release.get("tag_name", "")))


def is_available_release(release, *, include_prereleases):
    if release.get("draft"):
        return False
    tag = release.get("tag_name", "")
    return bool(tag) and should_include_available_version_tag(tag, include_prereleases)


def find_tag_for_channel(tags, include_prereleases):
    matching_tags = [
        tag
        for tag in tags
        if tag and should_include_available_version_tag(tag, include_prereleases)
    ]
    if not matching_tags:
        return None
    return max(matching_tags, key=parse_version)


def is_prerelease_tag(tag):
    return parse_version(tag)[3] < _STABLE_RANK


def should_include_available_version_tag(tag, include_prereleases):
    return include_prereleases or not is_prerelease_tag(tag)


def should_include_history_version_tag(tag, include_prereleases):
    return include_prereleases or not is_prerelease_tag(tag)


def is_newer_version(candidate, current):
    return parse_version(candidate) > parse_version(current)


def find_previous_for_prerelease(current_version, candidates):
    current_parsed = parse_version(current_version)
    current_base = current_parsed[:3]
    current_rank = current_parsed[3]
    current_number = current_parsed[4]
    if current_rank >= _STABLE_RANK:
        return ""

    same_line_prereleases = [
        candidate
        for candidate in candidates
        if parse_version(candidate)[:3] == current_base
           and parse_version(candidate)[3] == current_rank
           and parse_version(candidate)[4] < current_number
           and not is_fallback_version(candidate)
    ]
    if same_line_prereleases:
        return max(same_line_prereleases, key=parse_version)

    same_line_stable = [
        candidate
        for candidate in candidates
        if parse_version(candidate)[:3] == current_base
           and parse_version(candidate)[3] == _STABLE_RANK
           and not is_fallback_version(candidate)
    ]
    if same_line_stable:
        return max(same_line_stable, key=parse_version)

    return ""


def normalize_version(version):
    return str(version).strip().removeprefix("v").removeprefix("V")


def display_version(version):
    normalized = normalize_version(version)
    replacements = (
        (r"^(\d+\.\d+\.\d+)rc(\d+)$", r"\1-rc.\2"),
        (r"^(\d+\.\d+\.\d+)b(\d+)$", r"\1-beta.\2"),
        (r"^(\d+\.\d+\.\d+)a(\d+)$", r"\1-alpha.\2"),
        (r"^(\d+\.\d+\.\d+)\.dev(\d+)$", r"\1-dev.\2"),
    )
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized)
    return normalized


def is_fallback_version(version):
    normalized = display_version(version)
    return normalized in {"dev", "0.0.0-dev.0", "0.0.0dev.0", "0.0.0.dev0"}


_PRERELEASE_RANKS = {
    "dev": 0,
    "alpha": 1,
    "a": 1,
    "beta": 2,
    "b": 2,
    "rc": 3,
}
_STABLE_RANK = 4


def parse_version(version):
    normalized = display_version(version)
    match = re.match(
        r"^(\d+)\.(\d+)\.(\d+)(?:[-.]?([A-Za-z]+)\.?(\d+)?)?$",
        normalized,
    )
    if match:
        major, minor, patch, label, prerelease_number = match.groups()
        rank = _STABLE_RANK if label is None else _PRERELEASE_RANKS.get(label.lower(), 0)
        return (
            int(major),
            int(minor),
            int(patch),
            rank,
            int(prerelease_number or 0),
        )

    numbers = [int(part) for part in re.findall(r"\d+", normalized)]
    padded_numbers = [*numbers[:3], 0, 0, 0][:3]
    return (*padded_numbers, _STABLE_RANK, 0)
