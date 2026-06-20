from __future__ import annotations

from home_cinema_control.media_servers.common.session_monitor import (
    MediaServerSessionMonitor,
)
from home_cinema_control.media_servers.emby.session_events import (
    find_monitored_session,
)


class EmbySessionMonitor(MediaServerSessionMonitor):
    def __init__(self, *, emby_session, **kwargs):
        super().__init__(
            provider_name="Emby",
            media_server_session=emby_session,
            find_monitored_session=find_monitored_session,
            **kwargs,
        )
