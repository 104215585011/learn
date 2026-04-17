from __future__ import annotations

import sqlite3

import news_digest
from floatvocab.db import DEFAULT_LANGUAGE_CODE


class NewsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_latest_briefs(self, language_code: str = DEFAULT_LANGUAGE_CODE, limit: int = 10):
        news_digest.ensure_schema(self.conn)
        return news_digest.latest_briefs(self.conn, language_code=language_code, limit=limit)

    def list_favorites(self, language_code: str = DEFAULT_LANGUAGE_CODE):
        news_digest.ensure_schema(self.conn)
        return news_digest.favorite_articles(self.conn, language_code=language_code)

    def get_favorite_article(self, article_id: int, language_code: str = DEFAULT_LANGUAGE_CODE):
        news_digest.ensure_schema(self.conn)
        return news_digest.favorite_article_by_id(self.conn, article_id, language_code=language_code)

    def get_brief(self, brief_id: int, language_code: str = DEFAULT_LANGUAGE_CODE):
        news_digest.ensure_schema(self.conn)
        return self.conn.execute(
            "SELECT * FROM daily_briefs WHERE id = ? AND language_code = ?",
            (brief_id, language_code),
        ).fetchone()
