import shutil
import traceback
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path

from m_dl.ytdlpitem import YTDLPItem

from .config import config, load_config
from .db import Database
from .download import download_and_get_path
from .log import log, setup_logging
from .tagger import tag_file
from .ytapi import PlaylistItem, VideoInaccessibleError, YTApi


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
        if isinstance(item, VideoInaccessibleError):
            print("ERROR: FAILED TO ACCESS VIDEO")
            print("".join(traceback.format_exception(item)))
            continue

        if db.has_url(item.url):
            has_url_count += 1
        else:
            new_videos.append(item)

        if has_url_count > 50:
            # we've passed through 50 seen videos now, it's safe to say the remaining videos have already been seen before
            break

    return new_videos


def backup_database():
    db_path: Path = Path(config["path"]) / config["filenames"]["database"]

    backup_dir: Path = Path(config["path"]) / config["filenames"]["database_backup_dir"]
    backup_name = datetime.now().strftime("backup_%Y-%m-%d %H_%M_%S.db")
    backup_path = backup_dir / backup_name

    log.info("Backing up database to: %s", backup_path)
    shutil.copy2(db_path, backup_path)


def parse_args():
    parser = ArgumentParser("m-dl")

    parser.add_argument("-u", "--url", dest="urls", action="append", default=[])
    parser.add_argument("--skip-youtube", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--allow-duplicate", action="store_true")
    parser.add_argument(
        "--tag",
        nargs=4,
        help="tag a file with some settings: title, artist, url",
        metavar=("PATH", "TITLE", "ARTIST", "URL"),
    )

    return parser.parse_args()


def main():
    setup_logging()

    args = parse_args()

    load_config(args.config)

    if args.tag is not None:
        path, title, artist, url = args.tag
        path = Path(path)
        # current time in UTC
        added_at = datetime.now(timezone.utc)

        tags = {
            "title": title,
            "artist": artist,
            "url": url,
            "added_at": added_at,
        }

        log.info(f"Tagging {path.name!r} with the following tags:")
        log.info(tags)

        tag_file(
            path,
            {
                "title": title,
                "artist": artist,
                "url": url,
                "added_at": added_at,
            },
        )
        return

    backup_database()

    db_path = Path(config["path"]) / config["filenames"]["database"]

    with Database(db_path) as db:
        for url in args.urls:
            log.info("Processing manual URL: %s", url)
            item = YTDLPItem.from_url(url)
            if not args.allow_duplicate and db.has_url(item.url):
                log.info("Database already contains this URL, skipping it: %s", url)
            else:
                log.info("New video from manual: %s", item.title)
                db.add_url(
                    item.url,
                    title=item.title,
                    artist=item.artist,
                    added_at=item.added_at,
                    processed=False,
                )

        if not args.skip_youtube:
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
