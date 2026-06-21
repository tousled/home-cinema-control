from __future__ import annotations

DEFAULT_NATURAL_END_TOLERANCE_SECONDS = 10
DEFAULT_NATURAL_END_MINIMUM_TOTAL_SECONDS = 300
DEFAULT_PLAYED_FRACTION_THRESHOLD = 0.90


def is_oppo_end_of_content(
    *,
        current_seconds: int,
        total_seconds: int,
        tolerance_seconds: int = DEFAULT_NATURAL_END_TOLERANCE_SECONDS,
        minimum_total_seconds: int = DEFAULT_NATURAL_END_MINIMUM_TOTAL_SECONDS,
) -> bool:
    """Report whether the OPPO has reached the end of the played content.

    The media server's runtime is not a reliable duration source (it is
    missing or zero for many ISO/Blu-ray items), so the OPPO is the single
    source of truth. ``total_seconds`` is the full title length and
    ``current_seconds`` the cumulative title position, both as reported by
    ``getplayingtime`` (``total_time`` / ``cur_time``). They are title-level
    and do not reset on chapter changes.

    ``minimum_total_seconds`` is a floor: short non-feature segments such as
    disc menus (~60s) and copyright reels (a few seconds) also drive their own
    ``cur_time`` up to their ``total_time``, so anything below the floor is not
    treated as feature content and never counts as end-of-content.
    """
    if total_seconds < max(0, minimum_total_seconds):
        return False

    return current_seconds >= total_seconds - max(0, tolerance_seconds)


def is_oppo_next_title_started(
    *,
        previous_position_seconds: int,
        previous_total_seconds: int,
        current_total_seconds: int,
        tolerance_seconds: int = DEFAULT_NATURAL_END_TOLERANCE_SECONDS,
        minimum_total_seconds: int = DEFAULT_NATURAL_END_MINIMUM_TOTAL_SECONDS,
) -> bool:
    """Report that the player rolled from a finished feature onto other content.

    Safety net for the OPPO auto-advancing to the next file in the folder once a
    feature ends: the previous title was feature-length and at/near its end, and
    the reported total has changed (a different title/file is now playing). The
    previous title is then treated as finished so playback stops before the next
    file takes over. Keyed on the total changing (not on catching the exact last
    second), so it survives a missed end-of-title reading between polls.
    """
    if current_total_seconds == previous_total_seconds:
        return False

    return is_oppo_end_of_content(
        current_seconds=previous_position_seconds,
        total_seconds=previous_total_seconds,
        tolerance_seconds=tolerance_seconds,
        minimum_total_seconds=minimum_total_seconds,
    )


def was_content_played(
    *,
        current_seconds: int,
        total_seconds: int,
        minimum_total_seconds: int = DEFAULT_NATURAL_END_MINIMUM_TOTAL_SECONDS,
        fraction_threshold: float = DEFAULT_PLAYED_FRACTION_THRESHOLD,
) -> bool:
    """Report whether enough of the content was played to mark it watched.

    Unlike :func:`is_oppo_end_of_content` (which must be near the literal end to
    auto-stop the disc without cutting credits), this decides the media-server
    "played" flag when playback stops *before* the literal end -- typically the
    user stopping with the remote during the credits. ``fraction_threshold``
    matches the media-server convention (~90%). The same ``minimum_total_seconds``
    floor excludes disc menus / short reels so their wrap-around does not count
    as a watched feature.
    """
    if total_seconds < max(0, minimum_total_seconds):
        return False

    if total_seconds <= 0:
        return False

    return (current_seconds / total_seconds) >= fraction_threshold
