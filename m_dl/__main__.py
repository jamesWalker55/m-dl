from .log import setup_logging

setup_logging()

from datetime import datetime
from .config import config
from .db import Database
from .ytapi import YTApi, PlaylistItem


def new_liked_videos(db: Database):
    """Return videos in the YouTube playlist that isn't in the database yet"""

    api = YTApi(
        client_id=config.get("client_id", None),
        client_secret=config.get("client_secret", None),
        refresh_token=config.get("refresh_token", None),
    )

    playlist_id = config.get("playlist_id", "LL")

    has_url_count = 0

    new_videos: list[PlaylistItem] = []

    for item in api.iter_playlist_items(playlist_id):
        if db.has_url(item.url):
            has_url_count += 1
        else:
            new_videos.append(item)

        if has_url_count > 50:
            # we've passed through 50 seen videos now, it's safe to say the remaining videos have already been seen before
            break

    return new_videos


def main():
    path = R"D:\Soundtracks\Downloaded Playlist\database.sqlite"
    with Database(path) as db:
        # print(db.add_url('the url', title='the title', artist='james', added_at=datetime.now(), processed=True))
        # print(db.mark_processed("the url", True))
        # print(db.con.cursor().execute("SELECT * FROM music_v2").fetchall())
        # print(db.con.cursor().execute("SELECT * FROM music_v2").fetchall())
        # print(db.con.cursor().execute("SELECT * FROM music_v2").fetchall())
        new_videos = new_liked_videos(db)
        print(new_videos)
        print(new_videos)
        print(new_videos)
        print(new_videos)


if __name__ == "__main__":
    main()
