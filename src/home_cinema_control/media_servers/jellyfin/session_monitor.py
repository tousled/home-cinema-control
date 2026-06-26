from __future__ import annotations

from home_cinema_control.media_servers.common.session_monitor import (
    MediaServerSessionMonitor,
)
from home_cinema_control.media_servers.jellyfin.session_events import (
    find_monitored_session,
)


class JellyfinSessionMonitor(MediaServerSessionMonitor):
    def __init__(self, *, jellyfin_session, **kwargs):
        super().__init__(
            provider_name="Jellyfin",
            media_server_session=jellyfin_session,
            find_monitored_session=find_monitored_session,
            **kwargs,
        )
