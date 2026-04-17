import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Iterable
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - runtime dependency guard
    BeautifulSoup = None


DEFAULT_LANGUAGE_CODE = "en"
USER_AGENT = "FloatVocabNews/1.0"
GOOGLE_TRANSLATE_ENDPOINT = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q={query}"
ECONOMIST_AUTH_URL = "https://api.economist.com/eco/content/all/b2b-content-api/v1/auth/login"
ECONOMIST_BRIEF_URL = "https://api.economist.com/eco/content/all/b2b-content-api/v1/the-world-in-brief"


@dataclass
class Brief:
    source_key: str
    source_name: str
    title: str
    summary: str
    url: str
    published_at: str


RSS_SOURCES_BY_LANGUAGE = {
    "en": [
        {
            "key": "bbc_world",
            "name": "BBC World",
            "feed": "https://feeds.bbci.co.uk/news/world/rss.xml",
        },
        {
            "key": "reuters_world",
            "name": "Reuters World",
            "feed": "https://feeds.reuters.com/Reuters/worldNews",
        },
    ],
}


def ensure_schema(conn: sqlite3.Connection) -> None:
    _ensure_daily_briefs_table(conn)
    _ensure_favorite_articles_table(conn)
    conn.commit()


def _ensure_daily_briefs_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_briefs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          language_code TEXT NOT NULL DEFAULT 'en',
          source_key TEXT NOT NULL,
          source_name TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          url TEXT NOT NULL,
          published_at TEXT NOT NULL DEFAULT '',
          fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          saved INTEGER NOT NULL DEFAULT 0,
          UNIQUE(language_code, url)
        )
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(daily_briefs)").fetchall()}
    if "language_code" in columns:
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        f"""
        CREATE TABLE daily_briefs_new (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          language_code TEXT NOT NULL DEFAULT '{DEFAULT_LANGUAGE_CODE}',
          source_key TEXT NOT NULL,
          source_name TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          url TEXT NOT NULL,
          published_at TEXT NOT NULL DEFAULT '',
          fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          saved INTEGER NOT NULL DEFAULT 0,
          UNIQUE(language_code, url)
        );

        INSERT INTO daily_briefs_new (id, language_code, source_key, source_name, title, summary, url, published_at, fetched_at, saved)
        SELECT id, '{DEFAULT_LANGUAGE_CODE}', source_key, source_name, title, summary, url, published_at, fetched_at, COALESCE(saved, 0)
        FROM daily_briefs;

        DROP TABLE daily_briefs;
        ALTER TABLE daily_briefs_new RENAME TO daily_briefs;
        """
    )
    conn.execute("PRAGMA foreign_keys = ON")


def _ensure_favorite_articles_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS favorite_articles (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          brief_id INTEGER NOT NULL UNIQUE,
          language_code TEXT NOT NULL DEFAULT 'en',
          source_key TEXT NOT NULL,
          source_name TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          url TEXT NOT NULL,
          published_at TEXT NOT NULL DEFAULT '',
          content_text TEXT NOT NULL DEFAULT '',
          bilingual_text TEXT NOT NULL DEFAULT '',
          metadata_json TEXT NOT NULL DEFAULT '{}',
          saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(language_code, url),
          FOREIGN KEY (brief_id) REFERENCES daily_briefs(id) ON DELETE CASCADE
        )
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(favorite_articles)").fetchall()}
    if "language_code" in columns:
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        f"""
        CREATE TABLE favorite_articles_new (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          brief_id INTEGER NOT NULL UNIQUE,
          language_code TEXT NOT NULL DEFAULT '{DEFAULT_LANGUAGE_CODE}',
          source_key TEXT NOT NULL,
          source_name TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          url TEXT NOT NULL,
          published_at TEXT NOT NULL DEFAULT '',
          content_text TEXT NOT NULL DEFAULT '',
          bilingual_text TEXT NOT NULL DEFAULT '',
          metadata_json TEXT NOT NULL DEFAULT '{{}}',
          saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(language_code, url),
          FOREIGN KEY (brief_id) REFERENCES daily_briefs(id) ON DELETE CASCADE
        );

        INSERT INTO favorite_articles_new
        (id, brief_id, language_code, source_key, source_name, title, summary, url, published_at, content_text, bilingual_text, metadata_json, saved_at)
        SELECT id, brief_id, '{DEFAULT_LANGUAGE_CODE}', source_key, source_name, title, summary, url, published_at, content_text, bilingual_text, metadata_json, saved_at
        FROM favorite_articles;

        DROP TABLE favorite_articles;
        ALTER TABLE favorite_articles_new RENAME TO favorite_articles;
        """
    )
    conn.execute("PRAGMA foreign_keys = ON")


def refresh_latest_briefs(
    conn: sqlite3.Connection,
    *,
    language_code: str = DEFAULT_LANGUAGE_CODE,
    limit: int = 10,
) -> list[sqlite3.Row]:
    ensure_schema(conn)
    briefs = list(fetch_briefs(language_code=language_code, limit=limit))
    for brief in briefs:
        conn.execute(
            """
            INSERT INTO daily_briefs (language_code, source_key, source_name, title, summary, url, published_at, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(language_code, url) DO UPDATE SET
              source_key = excluded.source_key,
              source_name = excluded.source_name,
              title = excluded.title,
              summary = excluded.summary,
              published_at = excluded.published_at,
              fetched_at = CURRENT_TIMESTAMP
            """,
            (language_code, brief.source_key, brief.source_name, brief.title, brief.summary, brief.url, brief.published_at),
        )
    conn.commit()
    return latest_briefs(conn, language_code=language_code, limit=limit)


def latest_briefs(
    conn: sqlite3.Connection,
    *,
    language_code: str = DEFAULT_LANGUAGE_CODE,
    limit: int = 10,
) -> list[sqlite3.Row]:
    ensure_schema(conn)
    return conn.execute(
        """
        SELECT *
        FROM daily_briefs
        WHERE language_code = ?
        ORDER BY published_at DESC, fetched_at DESC, id DESC
        LIMIT ?
        """,
        (language_code, limit),
    ).fetchall()


def favorite_articles(conn: sqlite3.Connection, *, language_code: str = DEFAULT_LANGUAGE_CODE) -> list[sqlite3.Row]:
    ensure_schema(conn)
    return conn.execute(
        """
        SELECT *
        FROM favorite_articles
        WHERE language_code = ?
        ORDER BY saved_at DESC, id DESC
        """,
        (language_code,),
    ).fetchall()


def favorite_article_by_id(
    conn: sqlite3.Connection,
    article_id: int,
    *,
    language_code: str = DEFAULT_LANGUAGE_CODE,
) -> sqlite3.Row | None:
    ensure_schema(conn)
    return conn.execute(
        "SELECT * FROM favorite_articles WHERE id = ? AND language_code = ?",
        (article_id, language_code),
    ).fetchone()


def save_brief_to_favorites(
    conn: sqlite3.Connection,
    brief_id: int,
    *,
    language_code: str = DEFAULT_LANGUAGE_CODE,
) -> sqlite3.Row:
    ensure_schema(conn)
    brief = conn.execute(
        "SELECT * FROM daily_briefs WHERE id = ? AND language_code = ?",
        (brief_id, language_code),
    ).fetchone()
    if not brief:
        raise ValueError("Daily brief not found.")
    existing = conn.execute(
        """
        SELECT *
        FROM favorite_articles
        WHERE language_code = ? AND (brief_id = ? OR url = ?)
        ORDER BY CASE WHEN brief_id = ? THEN 0 ELSE 1 END, id
        LIMIT 1
        """,
        (language_code, brief_id, brief["url"], brief_id),
    ).fetchone()
    if existing:
        conn.execute("UPDATE daily_briefs SET saved = 1 WHERE id = ?", (brief_id,))
        conn.commit()
        return existing
    metadata = {
        "saved_from_brief_id": brief_id,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "language_code": language_code,
    }
    used_summary_fallback = False
    try:
        content_text = fetch_article_content(brief["source_key"], brief["url"])
    except Exception as exc:
        content_text = build_fallback_content(brief)
        used_summary_fallback = True
        metadata["content_error"] = str(exc)
        metadata["content_mode"] = "summary_fallback"

    if used_summary_fallback:
        bilingual_text = content_text
    else:
        try:
            bilingual_text = to_bilingual_text(content_text)
        except Exception as exc:
            bilingual_text = content_text
            metadata["translation_error"] = str(exc)
            metadata["translation_mode"] = "source_only"
    conn.execute(
        """
        INSERT INTO favorite_articles
        (brief_id, language_code, source_key, source_name, title, summary, url, published_at, content_text, bilingual_text, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            brief["id"],
            language_code,
            brief["source_key"],
            brief["source_name"],
            brief["title"],
            brief["summary"],
            brief["url"],
            brief["published_at"],
            content_text,
            bilingual_text,
            json.dumps(metadata, ensure_ascii=False),
        ),
    )
    conn.execute("UPDATE daily_briefs SET saved = 1 WHERE id = ?", (brief_id,))
    conn.commit()
    return conn.execute(
        "SELECT * FROM favorite_articles WHERE brief_id = ? AND language_code = ?",
        (brief_id, language_code),
    ).fetchone()


def build_fallback_content(brief: sqlite3.Row) -> str:
    parts = [brief["title"].strip()]
    summary = (brief["summary"] or "").strip()
    if summary:
        parts.append(summary)
    url = (brief["url"] or "").strip()
    if url:
        parts.append(f"原文链接：{url}")
    return "\n\n".join(parts)


def fetch_briefs(*, language_code: str, limit: int) -> Iterable[Brief]:
    items: list[Brief] = []
    items.extend(fetch_rss_briefs(language_code))
    if language_code == DEFAULT_LANGUAGE_CODE:
        items.extend(fetch_economist_briefs())
    items.sort(key=lambda item: item.published_at or "", reverse=True)
    seen: set[str] = set()
    for item in items:
        if item.url in seen:
            continue
        seen.add(item.url)
        yield item
        if len(seen) >= limit:
            return


def fetch_rss_briefs(language_code: str) -> list[Brief]:
    briefs: list[Brief] = []
    for source in RSS_SOURCES_BY_LANGUAGE.get(language_code, []):
        try:
            root = ET.fromstring(fetch_text(source["feed"]))
        except Exception:
            continue
        for item in root.findall(".//item"):
            title = text_of(item.find("title"))
            summary = strip_html(text_of(item.find("description")))
            url = text_of(item.find("link"))
            published_at = normalize_pub_date(text_of(item.find("pubDate")))
            if not title or not url:
                continue
            briefs.append(
                Brief(
                    source_key=source["key"],
                    source_name=source["name"],
                    title=title,
                    summary=summary,
                    url=url,
                    published_at=published_at,
                )
            )
    return briefs


def fetch_economist_briefs() -> list[Brief]:
    client_id = os.getenv("ECONOMIST_CLIENT_ID", "").strip()
    client_secret = os.getenv("ECONOMIST_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return []
    auth_body = json.dumps({"client_id": client_id, "client_secret": client_secret}).encode("utf-8")
    request = Request(
        ECONOMIST_AUTH_URL,
        data=auth_body,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    token = json.loads(read_url(request))["data"]["access_token"]
    brief_request = Request(
        ECONOMIST_BRIEF_URL,
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
    )
    payload = json.loads(read_url(brief_request))
    data = payload.get("data", {})
    published_at = normalize_iso_date(data.get("datePublished", ""))
    url = data.get("url", "https://www.economist.com/the-world-in-brief")
    briefs: list[Brief] = []
    for component in data.get("components", []):
        if component.get("type") != "CHUNK":
            continue
        title = strip_html(component.get("headline", "")).strip()
        paragraphs = [child.get("content", "").strip() for child in component.get("components", []) if child.get("type") == "PARAGRAPH"]
        summary = " ".join(paragraphs[:2]).strip()
        if not title:
            continue
        briefs.append(
            Brief(
                source_key="economist_world_in_brief",
                source_name="The Economist",
                title=title,
                summary=summary,
                url=url,
                published_at=published_at,
            )
        )
    return briefs


def fetch_article_content(source_key: str, url: str) -> str:
    if BeautifulSoup is None:
        raise RuntimeError("Missing beautifulsoup4 dependency. Please install requirements.txt first.")
    html = fetch_text(url)
    if source_key == "economist_world_in_brief":
        return strip_html(html)
    soup = BeautifulSoup(html, "html.parser")
    selectors = {
        "bbc_world": [
            "main article p",
            "article [data-component='text-block'] p",
            "main [data-component='text-block'] p",
        ],
        "reuters_world": [
            "article p",
            "[data-testid='paragraph']",
            "main p",
        ],
    }
    paragraphs = extract_paragraphs(soup, selectors.get(source_key, ["article p", "main p", "p"]))
    if not paragraphs:
        paragraphs = extract_paragraphs(soup, ["p"])
    if not paragraphs:
        raise ValueError("Failed to extract article body.")
    return "\n\n".join(paragraphs)


def extract_paragraphs(soup: BeautifulSoup, selectors: list[str]) -> list[str]:
    paragraphs: list[str] = []
    seen: set[str] = set()
    for selector in selectors:
        for node in soup.select(selector):
            text = clean_text(node.get_text(" ", strip=True))
            if not text or len(text) < 40 or text in seen:
                continue
            if text.lower().startswith("copyright ") or text.lower().startswith("all rights reserved"):
                continue
            seen.add(text)
            paragraphs.append(text)
        if paragraphs:
            return paragraphs
    return paragraphs


def to_bilingual_text(content_text: str) -> str:
    paragraphs = [part.strip() for part in content_text.split("\n\n") if part.strip()]
    bilingual_parts: list[str] = []
    for paragraph in paragraphs:
        translated = translate_text(paragraph)
        bilingual_parts.append(f"{paragraph}\n{translated}")
    return "\n\n".join(bilingual_parts)


def translate_text(text: str) -> str:
    url = GOOGLE_TRANSLATE_ENDPOINT.format(query=quote_plus(text))
    payload = json.loads(fetch_text(url))
    return "".join(segment[0] for segment in payload[0] if segment and segment[0]).strip()


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    return read_url(request)


def read_url(request: Request) -> str:
    with urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def normalize_pub_date(value: str) -> str:
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, IndexError):
        return value


def normalize_iso_date(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return value


def text_of(element) -> str:
    return element.text.strip() if element is not None and element.text else ""


def strip_html(value: str) -> str:
    return clean_text(BeautifulSoup(unescape(value or ""), "html.parser").get_text(" ", strip=True))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()
