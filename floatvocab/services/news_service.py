from __future__ import annotations

import sqlite3
from typing import Callable

import news_digest


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

    def refresh_latest_briefs(self, limit: int = 10):
        with self.connection_factory(self.db_path) as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            return self.news_digest.refresh_latest_briefs(conn, limit=limit)

    def list_latest_briefs(self, limit: int = 10):
        with self.connection_factory(self.db_path) as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            return self.news_digest.latest_briefs(conn, limit=limit)

    def list_favorite_articles(self):
        with self.connection_factory(self.db_path) as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            return self.news_digest.favorite_articles(conn)

    def get_favorite_article(self, article_id: int):
        with self.connection_factory(self.db_path) as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            return self.news_digest.favorite_article_by_id(conn, article_id)

    def save_brief_to_favorites(self, brief_id: int):
        with self.connection_factory(self.db_path) as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            return self.news_digest.save_brief_to_favorites(conn, brief_id)
