from dataclasses import dataclass
from datetime import datetime
import pyyoutube

from .log import log


@dataclass
class PlaylistItem:
    title: str
    video_id: str

    channel: str
    channel_id: str

    added_at: datetime

    @classmethod
    def from_pyyoutube(cls, item: pyyoutube.PlaylistItem):
        title = item.snippet.title  # type: ignore
        assert isinstance(title, str)

        video_id = item.snippet.resourceId.videoId  # type: ignore
        assert isinstance(video_id, str)

        channel = item.snippet.videoOwnerChannelTitle  # type: ignore
        assert isinstance(channel, str)

        channel_id = item.snippet.videoOwnerChannelId  # type: ignore
        assert isinstance(channel_id, str)

        added_at = item.snippet.publishedAt  # type: ignore
        assert isinstance(added_at, str)
        assert len(added_at) == 20
        assert added_at[-1] == "Z"
        added_at = datetime.fromisoformat(added_at[:-1])

        return cls(title, video_id, channel, channel_id, added_at)

    @property
    def url(self):
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @property
    def source_id(self):
        return self.video_id

    @property
    def artist(self):
        return self.channel


class YTApi:
    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        if client_id is None or client_secret is None:
            raise ValueError("Both client ID and client secret must be provided")

        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._refresh_token: str | None = refresh_token

        if refresh_token is None:
            self._new_session()
        else:
            self._refresh_session()

    def _new_session(self):
        """Create a new pair of access and refresh tokens through OAuth flow"""

        import webbrowser

        log.info("Creating a new YouTube session")

        client = pyyoutube.Client(
            client_id=self._client_id,
            client_secret=self._client_secret,
        )

        # visit oauth flow URL
        url, _ = client.get_authorize_url()
        webbrowser.open(url, new=1, autoraise=True)

        while True:
            print("Please input the authorization response:")
            auth = input("  > ").strip()

            try:
                access_token = client.generate_access_token(authorization_response=auth)

                # validate access token
                assert not isinstance(access_token, dict)
                access_token = access_token.access_token
                assert isinstance(access_token, str) and len(access_token) > 0

                # validate refresh token
                refresh_token = client.refresh_token
                assert isinstance(refresh_token, str) and len(refresh_token) > 0

                # store tokens
                self._access_token = access_token
                self._refresh_token = refresh_token

                break

            except KeyboardInterrupt as e:
                # allow exiting through Ctrl-C
                raise e

            except Exception as e:
                log.error("Error when generating access token", exc_info=e)
                print("    Invalid authorization response, please try again...")

    def _refresh_session(self):
        """Create a new pair of access and refresh tokens using a refresh token"""

        log.info("Refreshing existing YouTube session")

        if self._refresh_token is None:
            raise RuntimeError("No refresh token available")

        refresh_token = self._refresh_token

        client = pyyoutube.Client(
            client_id=self._client_id,
            client_secret=self._client_secret,
        )
        access_token = client.refresh_access_token(refresh_token)

        # validate access token
        assert not isinstance(access_token, dict)
        access_token = access_token.access_token
        assert isinstance(access_token, str) and len(access_token) > 0

        # store access token
        self._access_token = access_token

    def iter_playlist_items(self, playlist_id: str):
        """Iterate through all videos in the given playlist. This automatically handles pagination."""

        log.debug("Fetching items from playlist %s", playlist_id)

        client = pyyoutube.Client(
            client_id=self._client_id,
            client_secret=self._client_secret,
            access_token=self._access_token,
            refresh_token=self._refresh_token,
        )

        next_page_token = None

        while True:
            res = client.playlistItems.list(
                playlist_id=playlist_id,
                max_results=50,  # max value is 50
                page_token=next_page_token,
            )
            assert not isinstance(res, dict)
            assert res.items is not None

            log.debug("Fetched %d items", len(res.items))

            for item in res.items:
                yield PlaylistItem.from_pyyoutube(item)

            if res.nextPageToken is None:
                break

            next_page_token = res.nextPageToken
