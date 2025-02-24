import os
import re
import tempfile
import time
from pathlib import Path
from typing import TypedDict

from yt_dlp import YoutubeDL

from .config import config
from .log import log


class Auth(TypedDict):
    username: str
    password: str


def auth_patterns() -> dict[str, Auth]:
    patterns = config.get("auth_patterns", {})

    assert isinstance(patterns, dict)

    for k, v in patterns.items():
        assert isinstance(k, str)
        assert isinstance(v, dict)
        assert "username" in v and isinstance(v["username"], str)
        assert "password" in v and isinstance(v["password"], str)

    return patterns


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
        for audio in info["_api_data"]["media"]["domand"]["audios"]  # type: ignore
    )
    # any_video_unavailable = any(
    #     not video["isAvailable"]
    #     for video in info["_api_data"]["media"]["domand"]["videos"]  # type: ignore
    # )

    # if any_audio_unavailable or any_video_unavailable:
    if any_audio_unavailable:
        raise NicoVideoBusyException()


def download(url: str, folder_path):
    options = {
        "format": "bestaudio/best",
        "updatetime": False,
        "outtmpl": str(Path(folder_path) / "%(title)s %(id)s.%(ext)s"),
        "windowsfilenames": True,
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
    for pattern, auth in auth_patterns().items():
        if not re.search(pattern, url, re.IGNORECASE):
            continue

        log.info(
            "Url '%s' matches auth pattern '%s', adding authentication options",
            url,
            pattern,
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
            print("======================================================")
            print("======================================================")
            print(
                f"There should be exactly 1 file after downloading, but found {len(files)} files"
            )
            print("Please choose which file you want to keep!")
            print("======================================================")
            print("======================================================")
            for i, f in enumerate(files):
                print(f"{i + 1}. {f}")

            while True:
                idx = input("  (input a number, or 'x' to skip) > ")
                if idx.strip() == "x":
                    raise FileNotFoundError(
                        f"There should be exactly 1 file after downloading, but found {len(files)} files"
                    )

                try:
                    idx = int(idx) - 1
                except ValueError:
                    print("Invalid number")
                    continue

                if not 0 <= idx < len(files):
                    print(f"Not in range of 1 - {len(files)}")
                    continue

                break

            files = [files[idx]]

        temp_path = Path(tempdir) / files[0]
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
