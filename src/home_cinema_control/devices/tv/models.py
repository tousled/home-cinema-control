from dataclasses import dataclass


@dataclass(frozen=True)
class TvInputTarget:
    input_id: str
    confirmation_app_id: str | None = None
