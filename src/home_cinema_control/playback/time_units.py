TICKS_PER_SECOND = 10_000_000


def ticks_to_seconds(ticks: int) -> int:
    return int(ticks / TICKS_PER_SECOND)


def ticks_to_hms(ticks: int) -> tuple[int, int, int]:
    total_seconds = ticks_to_seconds(ticks)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return hours, minutes, seconds


def seconds_to_ticks(seconds: int) -> int:
    return seconds * TICKS_PER_SECOND
