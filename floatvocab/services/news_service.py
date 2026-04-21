from __future__ import annotations

from contextlib import contextmanager
from contextlib import closing
import sqlite3
from typing import Callable

import news_digest
from floatvocab.db import DEFAULT_LANGUAGE_CODE


class NewsService:
    def __init__(
        self,
        db_path,
        connection_factory: Callable[[str], sqlite3.Connection] = sqlite3.connect,
        news_digest_module=news_digest,
    ):
        self.db_path = db_path
        self.connection_factory = connection_factory
        self.news_digest = news_digest_module

    @contextmanager
    def _open_connection(self):
        resource = self.connection_factory(self.db_path)
        if hasattr(resource, "__enter__") and hasattr(resource, "__exit__"):
            with resource as conn:
                yield conn
            return
        with closing(resource) as conn:
            yield conn

    def _current_language_code(self) -> str:
        with self._open_connection() as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            try:
                row = conn.execute("SELECT current_language_code FROM plans WHERE id = 1").fetchone()
            except sqlite3.Error:
                return DEFAULT_LANGUAGE_CODE
        if not row:
            return DEFAULT_LANGUAGE_CODE
        value = row["current_language_code"] if hasattr(row, "keys") and "current_language_code" in row.keys() else None
        return (value or DEFAULT_LANGUAGE_CODE).strip().lower() or DEFAULT_LANGUAGE_CODE

    def refresh_latest_briefs(self, language_code: str | None = None, limit: int = 10):
        with self._open_connection() as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            normalized_language_code = language_code or self._current_language_code()
            return self.news_digest.refresh_latest_briefs(conn, language_code=normalized_language_code, limit=limit)

    def list_latest_briefs(self, language_code: str | None = None, limit: int = 10):
        with self._open_connection() as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            normalized_language_code = language_code or self._current_language_code()
            return self.news_digest.latest_briefs(conn, language_code=normalized_language_code, limit=limit)

    def list_favorite_articles(self, language_code: str | None = None):
        with self._open_connection() as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            normalized_language_code = language_code or self._current_language_code()
            return self.news_digest.favorite_articles(conn, language_code=normalized_language_code)

    def get_favorite_article(self, article_id: int, language_code: str | None = None):
        with self._open_connection() as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            normalized_language_code = language_code or self._current_language_code()
            return self.news_digest.favorite_article_by_id(conn, article_id, language_code=normalized_language_code)

    def delete_favorite_article(self, article_id: int, language_code: str | None = None):
        with self._open_connection() as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            normalized_language_code = language_code or self._current_language_code()
            return self.news_digest.delete_favorite_article(conn, article_id, language_code=normalized_language_code)

    def get_brief(self, brief_id: int, language_code: str | None = None):
        with self._open_connection() as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            normalized_language_code = language_code or self._current_language_code()
            return conn.execute(
                "SELECT * FROM daily_briefs WHERE id = ? AND language_code = ?",
                (brief_id, normalized_language_code),
            ).fetchone()

    def save_brief_to_favorites(self, brief_id: int, language_code: str | None = None):
        with self._open_connection() as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            normalized_language_code = language_code or self._current_language_code()
            return self.news_digest.save_brief_to_favorites(conn, brief_id, language_code=normalized_language_code)
