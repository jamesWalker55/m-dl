from datetime import datetime
from typing import TypedDict

from mediafile import MediaFile


class Tags(TypedDict):
    title: str
    artist: str
    url: str
    added_at: datetime


def tag_file(path, tags: Tags):
    mf = MediaFile(path)

    mf.title = tags["title"]

    mf.artist = tags["artist"]

    mf.album = "Downloaded Playlist"

    mf.date = tags["added_at"]
    mf.comments = tags["added_at"].strftime("%Y-%m-%dT%H:%M:%SZ")

    mf.url = tags["url"]
    mf.label = tags["url"]

    mf.save()
