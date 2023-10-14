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
