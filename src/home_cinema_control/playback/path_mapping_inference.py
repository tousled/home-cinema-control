from __future__ import annotations


def infer_player_paths(
    anchor_source: str,
    anchor_share: str,
    candidates: list[str],
) -> list[tuple[str, str]]:
    """
    Infer network share paths for each candidate using the anchor mapping as template.

    Strips trailing path components from anchor_source and anchor_share simultaneously
    until the remaining suffixes match, then derives a prefix substitution rule.

    Raises ValueError if no common suffix can be found.
    """
    src_parts = _components(anchor_source)
    share_parts = _components(anchor_share)

    source_prefix: str | None = None
    share_prefix: str | None = None

    for depth in range(1, min(len(src_parts), len(share_parts)) + 1):
        if src_parts[-depth:] == share_parts[-depth:]:
            source_prefix = _prefix(anchor_source, depth)
            share_prefix = _prefix(anchor_share, depth)
            break

    if source_prefix is None:
        raise ValueError(
            f"No common suffix between '{anchor_source}' and '{anchor_share}'"
        )

    results = []
    for candidate in candidates:
        if not candidate.startswith(source_prefix):
            raise ValueError(
                f"Candidate '{candidate}' does not start with inferred prefix '{source_prefix}'"
            )
        tail = candidate[len(source_prefix):]
        results.append((candidate, share_prefix + tail))

    return results


def _components(path: str) -> list[str]:
    return [p for p in path.replace("\\", "/").split("/") if p]


def _prefix(path: str, num_strip: int) -> str:
    """Strip num_strip trailing components from path and return the prefix with trailing slash."""
    p = path.rstrip("/")
    for _ in range(num_strip):
        idx = p.rfind("/")
        if idx < 0:
            p = ""
            break
        p = p[:idx]
    return p + "/"
