"""Shared path-boundary rules for media-server paths and playback mappings.

This is deliberately a small pure helper module, not a service. Keeping the
rule here prevents provider adapters and playback resolution from disagreeing
about whether one directory is inside another.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def normalize_path(path: str | None) -> str:
    """Apply HCC's existing separator normalization without changing case."""
    return str(path or "").replace("\\\\", "\\").replace("\\", "/")


def path_prefix_matches(item_path: str | None, source_path: str | None) -> bool:
    """Return whether ``source_path`` is a complete directory prefix."""
    item = normalize_path(item_path)
    source = normalize_path(source_path).rstrip("/")
    if not item or not source:
        return False
    return item == source or item.startswith(source + "/")


def longest_matching_mapping(
    item_path: str | None,
    mappings: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    """Return the most specific mapping for an item path, independent of order."""
    item = normalize_path(item_path)
    matches = [
        mapping
        for mapping in mappings
        if path_prefix_matches(item, mapping.get("source_path"))
    ]
    return max(
        matches,
        key=lambda mapping: len(normalize_path(mapping.get("source_path")).rstrip("/")),
        default=None,
    )
