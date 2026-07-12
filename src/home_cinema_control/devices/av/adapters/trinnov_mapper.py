import re

from home_cinema_control.config.models import AvInputSource

PROFILE_COMMAND_RE = re.compile(r"^(?:profile\s+)?(?P<source>\d+)$", re.IGNORECASE)
PROFILE_NAME_RE = re.compile(
    r"^(?:profile_name|PROFILE_NAME|get_profile_name)?\s*(?P<source>\d+)?\s*(?P<name>.+)$"
)


def normalize_profile_command(value: str) -> str:
    text = str(value or "").strip()
    match = PROFILE_COMMAND_RE.match(text)
    if not match:
        raise ValueError(
            "Trinnov source/profile must be a non-negative number or 'profile <number>'."
        )
    return f"profile {int(match.group('source'))}\n"


def is_terminal_success(line: str) -> bool:
    return line.strip() == "OK"


def is_terminal_error(line: str) -> bool:
    return line.strip().startswith("ERROR")


def fallback_profile_sources(limit: int = 32) -> list[AvInputSource]:
    return [
        AvInputSource(
            id=source,
            name=f"Source/profile {source}",
            param=f"profile {source}\n",
        )
        for source in range(limit)
    ]


def profile_source(source: int, name: str | None = None) -> AvInputSource:
    label = (name or "").strip()
    display_name = f"Source/profile {source}"
    if label:
        display_name = f"Source/profile {source} - {label}"
    return AvInputSource(id=source, name=display_name, param=f"profile {source}\n")


def parse_profile_name(
    profile_number: int,
    response_lines: list[str],
) -> AvInputSource | None:
    for raw_line in response_lines:
        line = raw_line.strip()
        if not line or is_terminal_success(line) or is_terminal_error(line):
            continue
        if line == str(profile_number):
            continue

        name = _extract_profile_name(profile_number, line)
        if name:
            return profile_source(profile_number, name)
    return None


def _extract_profile_name(profile_number: int, line: str) -> str:
    if line.startswith('"') and line.endswith('"') and len(line) >= 2:
        return line[1:-1].strip()

    match = PROFILE_NAME_RE.match(line)
    if match:
        source = match.group("source")
        if source is None or int(source) == profile_number:
            return match.group("name").strip().strip('"')

    parts = line.split(maxsplit=1)
    if len(parts) == 2 and parts[0] == str(profile_number):
        return parts[1].strip().strip('"')

    if not line.upper().startswith(
        ("META_", "VOLUME", "MUTE", "START_RUNNING", "LABEL")
    ):
        return line.strip().strip('"')

    return ""
