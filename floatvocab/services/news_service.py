from __future__ import annotations

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

    def refresh_latest_briefs(self, language_code: str = DEFAULT_LANGUAGE_CODE, limit: int = 10):
        with self.connection_factory(self.db_path) as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            return self.news_digest.refresh_latest_briefs(conn, language_code=language_code, limit=limit)

    def list_latest_briefs(self, language_code: str = DEFAULT_LANGUAGE_CODE, limit: int = 10):
        with self.connection_factory(self.db_path) as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            return self.news_digest.latest_briefs(conn, language_code=language_code, limit=limit)

    def list_favorite_articles(self, language_code: str = DEFAULT_LANGUAGE_CODE):
        with self.connection_factory(self.db_path) as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            return self.news_digest.favorite_articles(conn, language_code=language_code)

    def get_favorite_article(self, article_id: int, language_code: str = DEFAULT_LANGUAGE_CODE):
        with self.connection_factory(self.db_path) as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            return self.news_digest.favorite_article_by_id(conn, article_id, language_code=language_code)

    def get_brief(self, brief_id: int, language_code: str = DEFAULT_LANGUAGE_CODE):
        with self.connection_factory(self.db_path) as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM daily_briefs WHERE id = ? AND language_code = ?",
                (brief_id, language_code),
            ).fetchone()

    def save_brief_to_favorites(self, brief_id: int, language_code: str = DEFAULT_LANGUAGE_CODE):
        with self.connection_factory(self.db_path) as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            return self.news_digest.save_brief_to_favorites(conn, brief_id, language_code=language_code)
