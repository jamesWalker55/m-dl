from .log import setup_logging, log

setup_logging()

from .config import config
from .db import Database
from .ytapi import YTApi, PlaylistItem
from .download import download_and_get_path
from .tagger import tag_file


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
        for vid in new_liked_videos(db):
            log.info("New video from playlist: %s", vid.title)
            db.add_url(
                vid.url,
                title=vid.title,
                artist=vid.artist,
                added_at=vid.added_at,
                processed=False,
            )
        for item in db.unprocessed_items():
            log.info("Processing: %s", item)
            try:
                output_path = download_and_get_path(item.url, config["path"])
                tag_file(
                    output_path,
                    {
                        "title": item.title,
                        "artist": item.artist,
                        "url": item.url,
                        "added_at": item.added_at,
                    },
                )
                db.mark_processed(item.url, True)
            except KeyboardInterrupt as e:
                log.info("Received KeyboardInterrupt, exiting...")
                break
            except Exception as e:
                log.error("Item failed to process", exc_info=e)


if __name__ == "__main__":
    main()
