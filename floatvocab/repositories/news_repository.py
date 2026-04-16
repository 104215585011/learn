from __future__ import annotations

import sqlite3

import news_digest


class NewsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_latest_briefs(self, limit: int = 10):
        news_digest.ensure_schema(self.conn)
        return self.conn.execute(
            """
            SELECT *
            FROM daily_briefs
            ORDER BY published_at DESC, fetched_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    def list_favorites(self):
        news_digest.ensure_schema(self.conn)
        return self.conn.execute(
            """
            SELECT *
            FROM favorite_articles
            ORDER BY saved_at DESC, id DESC
            """
        ).fetchall()

    def get_favorite_article(self, article_id: int):
        news_digest.ensure_schema(self.conn)
        return self.conn.execute("SELECT * FROM favorite_articles WHERE id = ?", (article_id,)).fetchone()

    def get_brief(self, brief_id: int):
        news_digest.ensure_schema(self.conn)
        return self.conn.execute("SELECT * FROM daily_briefs WHERE id = ?", (brief_id,)).fetchone()
