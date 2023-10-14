import os
import time
import tempfile
from typing import TypedDict
from yt_dlp import YoutubeDL
from pathlib import Path

from .log import log
from .config import config


class Auth(TypedDict):
    username: str
    password: str


def auth_config() -> dict[str, Auth]:
    auth = config.get("auth", {})

    assert isinstance(auth, dict)

    for k, v in auth.items():
        assert isinstance(k, str)
        assert isinstance(v, dict)
        assert "username" in v and isinstance(v["username"], str)
        assert "password" in v and isinstance(v["password"], str)

    return auth


class NicoVideoBusyException(Exception):
    def __init__(self) -> None:
        super().__init__("NicoVideo is currently busy, please try again later")


def check_nico_quality(url: str, options):
    if "nicovideo" not in url.lower():
        return

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    any_audio_unavailable = any(
        not audio["isAvailable"]
        for audio in info["_api_data"]["media"]["delivery"]["movie"]["audios"]  # type: ignore
    )
    any_video_unavailable = any(
        not video["isAvailable"]
        for video in info["_api_data"]["media"]["delivery"]["movie"]["videos"]  # type: ignore
    )

    if any_audio_unavailable or any_video_unavailable:
        raise NicoVideoBusyException()


def download(url: str, folder_path):
    options = {
        "format": "bestaudio/best",
        "updatetime": False,
        "outtmpl": str(Path(folder_path) / "%(title)s %(id)s.%(ext)s"),
        "postprocessors": [
            {  # --extract-audio
                "key": "FFmpegExtractAudio",
                "preferredcodec": "best",
                "preferredquality": "3",  # 0 (best) - 10 (worst)
            }
        ],
    }

    log.debug("Downloading '%s' with options: %s", url, options)

    # check nicovideo quality before proceeding
    # don't add password yet since it needs to do mfa
    check_nico_quality(url, options)

    # add password if needed
    for suburl, auth in auth_config().items():
        if suburl.lower() not in url.lower():
            continue

        log.info(
            "Url '%s' matches auth site '%s', adding authentication options",
            url,
            suburl,
        )
        options["username"] = auth["username"]
        options["password"] = auth["password"]

        break

    with YoutubeDL(options) as ydl:
        ydl.download(url)


def download_and_get_path(url: str, folder_path):
    with tempfile.TemporaryDirectory(dir=folder_path) as tempdir:
        download(url, tempdir)

        # sleep a bit to wait for disk IO to settle
        if len(os.listdir(tempdir)) != 1:
            time.sleep(1)

        # there should only be 1 file in this folder
        files = os.listdir(tempdir)
        if len(files) != 1:
            raise FileNotFoundError(
                f"There should be exactly 1 file after downloading, but found {len(files)} files"
            )

        temp_path = Path(files[0])
        output_path = Path(folder_path) / temp_path.name

        # if output path already exists, then this is a duplicate
        # only move the file if it doesn't exist yet
        if output_path.exists():
            log.warn(
                "Output path %s already exists, discarding downloaded file", output_path
            )
        else:
            temp_path.rename(output_path)

    return output_path