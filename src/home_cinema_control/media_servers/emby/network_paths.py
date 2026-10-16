from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping


DEFAULT_CACHE_SECONDS = 300.0


def network_path_substitutions(
    virtual_folders: list[dict] | None,
) -> list[tuple[str, str]]:
    substitutions: dict[str, str] = {}
    for folder in virtual_folders or []:
        if not isinstance(folder, Mapping):
            continue
        library_options = folder.get("LibraryOptions") or {}
        if not isinstance(library_options, Mapping):
            continue
        for path_info in library_options.get("PathInfos") or []:
            if not isinstance(path_info, Mapping):
                continue
            network_path = str(path_info.get("NetworkPath") or "").strip()
            library_path = str(path_info.get("Path") or "").strip()
            if network_path and library_path and network_path != library_path:
                substitutions[network_path] = library_path

    return sorted(substitutions.items(), key=lambda pair: len(pair[0]), reverse=True)


def to_library_path(path: str | None, substitutions: list[tuple[str, str]]) -> str | None:
    if not path:
        return path

    normalized_path = _normalize_path(path)
    for network_path, library_path in substitutions:
        normalized_network_path = _normalize_path(network_path).rstrip("/")
        if not normalized_path.lower().startswith(normalized_network_path.lower()):
            continue

        rest = normalized_path[len(normalized_network_path) :]
        if rest and not rest.startswith("/"):
            continue

        normalized_library_path = _normalize_path(library_path).rstrip("/")
        return normalized_library_path + rest

    return path


class EmbyNetworkPathResolver:
    def __init__(
        self,
        fetch_virtual_folders: Callable[[], list[dict]],
        *,
        cache_seconds: float = DEFAULT_CACHE_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._fetch_virtual_folders = fetch_virtual_folders
        self._cache_seconds = cache_seconds
        self._monotonic = monotonic
        self._substitutions: list[tuple[str, str]] = []
        self._loaded_at = float("-inf")
        self._logged_paths: set[tuple[str, str]] = set()

    def to_library_path(self, path: str | None) -> str | None:
        substitutions = self._current_substitutions()
        mapped_path = to_library_path(path, substitutions)
        log_key = (str(path), str(mapped_path))
        if mapped_path != path and log_key not in self._logged_paths:
            logging.info("Emby shared network path mapped | from=%s | to=%s", path, mapped_path)
            self._logged_paths.add(log_key)
        return mapped_path

    def _current_substitutions(self) -> list[tuple[str, str]]:
        now = self._monotonic()
        if now - self._loaded_at < self._cache_seconds:
            return self._substitutions

        try:
            self._substitutions = network_path_substitutions(self._fetch_virtual_folders())
        except Exception:
            logging.warning("Could not refresh Emby shared network paths", exc_info=True)
        self._loaded_at = now
        return self._substitutions


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").rstrip("/")
