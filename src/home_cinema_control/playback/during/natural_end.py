from __future__ import annotations


def is_near_expected_end(
    *,
    position_seconds: int,
    expected_duration_seconds: int,
    tolerance_seconds: int,
) -> bool:
    if expected_duration_seconds <= 0:
        return False

    lower_bound = max(0, expected_duration_seconds - max(0, tolerance_seconds))
    return position_seconds >= lower_bound


def is_svm3_natural_end_reset(
    *,
    last_position_seconds: int,
    expected_duration_seconds: int,
    tolerance_seconds: int,
) -> bool:
    return is_near_expected_end(
        position_seconds=last_position_seconds,
        expected_duration_seconds=expected_duration_seconds,
        tolerance_seconds=tolerance_seconds,
    )


def is_polling_natural_end_reset(
    *,
    last_position_seconds: int,
    current_position_seconds: int,
    current_duration_seconds: int,
    expected_duration_seconds: int,
    tolerance_seconds: int,
) -> bool:
    if not is_near_expected_end(
        position_seconds=last_position_seconds,
        expected_duration_seconds=expected_duration_seconds,
        tolerance_seconds=tolerance_seconds,
    ):
        return False

    return (
        current_position_seconds <= max(0, tolerance_seconds)
        and current_duration_seconds > 0
        and current_duration_seconds != expected_duration_seconds
    )
