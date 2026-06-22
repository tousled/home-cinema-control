from __future__ import annotations

from enum import Enum


class MediaContentKind(Enum):
    """HCC's own classification of what's playing.

    Independent of any media server's vocabulary — mapped once from Emby's
    `Type` (or Jellyfin's equivalent `BaseItemKind`) at the adapter edge, so
    policy code never compares against a media-server-specific string.
    """

    MOVIE = "movie"
    EPISODE = "episode"
    CONCERT = "concert"
    LIVE_TV = "live_tv"
    OTHER = "other"
