from home_cinema_control.playback.player_state import (
    PlayerPlaybackLifecyclePhase,
    PlayerPlaybackStatus,
    lifecycle_phase_for_status,
)


def normalize_oppo_status(raw_status: str) -> str:
    status = _extract_status_line(raw_status)

    if status.startswith("@OK"):
        status = status[3:].strip()

    if status.startswith("@QPL OK"):
        status = status[7:].strip()

    if status.startswith("@QPW OK"):
        status = status[7:].strip()

    if not status:
        return "UNKNOWN"

    return status.upper().replace(" ", "_")


def _extract_status_line(raw_status: str) -> str:
    for line in _split_oppo_response_lines(raw_status):
        normalized_line = line.strip()
        if normalized_line.startswith("@OK"):
            return normalized_line
        if normalized_line.startswith("@QPL OK"):
            return normalized_line
        if normalized_line.startswith("@QPW OK"):
            return normalized_line

    return raw_status.strip()


def _split_oppo_response_lines(raw_status: str) -> list[str]:
    return raw_status.replace("\r\n", "\n").replace("\r", "\n").splitlines()


def parse_oppo_playback_status(raw_status: str) -> PlayerPlaybackStatus:
    normalized_status = normalize_oppo_status(raw_status)

    try:
        return PlayerPlaybackStatus(normalized_status)
    except ValueError:
        return PlayerPlaybackStatus.UNKNOWN


def classify_oppo_status(status: str | PlayerPlaybackStatus) -> PlayerPlaybackLifecyclePhase:
    playback_status = (
        status if isinstance(status, PlayerPlaybackStatus) else parse_oppo_playback_status(status)
    )
    return lifecycle_phase_for_status(playback_status)
