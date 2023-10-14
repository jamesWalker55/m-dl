from datetime import datetime
from sqlite3 import Connection


class Database:
    def __init__(self, path) -> None:
        self.con = Connection(path, isolation_level=None)
        self.setup_connection(self.con)
        self.migrate()

    @staticmethod
    def setup_connection(con: Connection):
        con.execute("PRAGMA foreign_keys = 1")

    def migrate(self):
        execute = self.con.execute

        execute("CREATE INDEX IF NOT EXISTS index_music_title ON music(title)")
        execute("CREATE INDEX IF NOT EXISTS index_music_artist ON music(artist)")
        execute("CREATE INDEX IF NOT EXISTS index_music_url ON music(url)")

        execute(
            """
            CREATE TABLE IF NOT EXISTS music_v2 (
                title TEXT NOT NULL,
                artist TEXT NOT NULL,
                url TEXT NOT NULL,
                added_at DATETIME NOT NULL,
                processed INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        execute("CREATE INDEX IF NOT EXISTS index_music_v2_title ON music_v2(title)")
        execute("CREATE INDEX IF NOT EXISTS index_music_v2_artist ON music_v2(artist)")
        execute("CREATE INDEX IF NOT EXISTS index_music_v2_url ON music_v2(url)")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.con.close()

    def _has_url_v1(self, url: str):
        """Return if the legacy table contains the given URL"""

        result = (
            self.con.cursor()
            .execute(
                "SELECT id FROM music WHERE url = ?",
                (url,),
            )
            .fetchone()
        )
        return result is not None

    def _has_url_v2(self, url: str):
        """Return if the new table contains the given URL"""

        result = (
            self.con.cursor()
            .execute(
                "SELECT rowid FROM music_v2 WHERE url = ?",
                (url,),
            )
            .fetchone()
        )
        return result is not None

    def has_url(self, url: str):
        return self._has_url_v2(url) or self._has_url_v1(url)

    def add_url(
        self,
        url: str,
        *,
        title: str | None = None,
        artist: str | None = None,
        added_at: datetime | None = None,
        processed: bool = False,
    ):
        if title is None:
            raise ValueError("title must be provided")
        if artist is None:
            raise ValueError("artist must be provided")
        if added_at is None:
            raise ValueError("added_at must be provided")

        sql = """
            INSERT INTO music_v2 (title, artist, url, added_at, processed)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (title, artist, url, added_at, 1 if processed else 0)
        self.con.execute(sql, params)

    def mark_processed(self, url: str, processed: bool):
        sql = """
            UPDATE music_v2
            SET processed = ?
            WHERE url = ?
        """
        params = (1 if processed else 0, url)
        self.con.execute(sql, params)
