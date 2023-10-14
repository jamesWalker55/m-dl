from dataclasses import dataclass
from datetime import datetime
from yt_dlp import YoutubeDL
import pytz


@dataclass
class YTDLPItem:
    title: str
    source_id: str
    url: str

    artist: str

    added_at: datetime

    @classmethod
    def from_url(cls, url: str):
        with YoutubeDL() as ydl:
            info = ydl.extract_info(url, download=False)
        assert isinstance(info, dict)

        title = info["title"]
        assert isinstance(title, str)

        source_id = info["id"]
        assert isinstance(source_id, str)

        url = info["webpage_url"]
        assert isinstance(url, str)

        artist = info["uploader"]
        assert isinstance(artist, str)

        added_at = datetime.now(pytz.UTC)

        return cls(
            title,
            source_id,
            url,
            artist,
            added_at,
        )
