import json
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from ssl import SSLError
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


API_BASE = "https://api.dictionaryapi.dev/api/v2/entries/en"
CACHE_DIR = Path(__file__).resolve().parent / "data" / "example_cache"
YD_BASE = "https://sentence.yourdictionary.com"


def normalize_example(text: str, word: str) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    if re.search(r"[\u0400-\u04FF]", text):
        return ""
    if " " not in text:
        return ""
    if len(text) > 220:
        text = text[:217].rstrip(" ,;:") + "..."
    if word and word.lower() not in text.lower():
        return ""
    return text


def best_example_from_payload(payload, word: str) -> str:
    candidates = []
    for entry in payload or []:
        for meaning in entry.get("meanings", []):
            for definition in meaning.get("definitions", []):
                example = normalize_example(definition.get("example", ""), word)
                if example:
                    score = 0
                    if example.lower().startswith(word.lower()):
                        score += 3
                    score -= abs(len(example) - 72) / 20
                    candidates.append((score, example))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1] if candidates else ""


def fetch_dictionary_payload(word: str, cache_dir: Path = CACHE_DIR, refresh: bool = False, retries: int = 2):
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{word.lower()}.json"
    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    request = Request(
        f"{API_BASE}/{quote(word)}",
        headers={"User-Agent": "FloatVocab-example-enricher/1.0", "Accept": "application/json"},
    )
    last_error = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as exc:
            if exc.code == 404:
                payload = []
                break
            last_error = exc
        except (URLError, SSLError) as exc:
            last_error = exc
        if attempt < retries:
            time.sleep(0.6 * (attempt + 1))
    else:
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))
        raise last_error
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def scrape_yourdictionary_example(word: str, cache_dir: Path = CACHE_DIR, refresh: bool = False):
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{word.lower()}.html"
    if cache_path.exists() and not refresh:
        html = cache_path.read_text(encoding="utf-8")
    else:
        request = Request(
            f"{YD_BASE}/{quote(word)}",
            headers={
                "User-Agent": "FloatVocab-example-enricher/1.0",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="ignore")
        cache_path.write_text(html, encoding="utf-8")
    # The page contains many bullet lines; keep only sentence-like items containing the target word.
    matches = re.findall(r"<li[^>]*>\s*([^<]{12,300})\s*</li>", html, flags=re.IGNORECASE)
    if not matches:
        matches = re.findall(r"\*\s+([A-Z][^.?!]{8,260}[.?!])", html)
    candidates = []
    for raw in matches:
        text = normalize_example(unescape(raw), word)
        if not text:
            continue
        if "Advertisement" in text or "Sign in" in text:
            continue
        score = 0
        if text.lower().startswith(word.lower()):
            score += 2
        score -= abs(len(text) - 72) / 20
        candidates.append((score, text))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1] if candidates else ""


def fetch_example_for_word(word: str, refresh: bool = False) -> tuple[str, str]:
    payload = fetch_dictionary_payload(word, refresh=refresh)
    example = best_example_from_payload(payload, word)
    if example:
        return example, "dictionaryapi.dev"
    example = scrape_yourdictionary_example(word, refresh=refresh)
    if example:
        return example, "yourdictionary"
    return "", "not-found"


def enrich_database(
    db_path: Path,
    limit: int = 200,
    refresh: bool = False,
    sleep_seconds: float = 0,
    lexicon_id: int | None = None,
    max_workers: int = 8,
):
    updated = 0
    skipped = 0
    failures = []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(words)").fetchall()}
        if "example_source" not in columns:
            conn.execute("ALTER TABLE words ADD COLUMN example_source TEXT DEFAULT ''")
        if "example_updated_at" not in columns:
            conn.execute("ALTER TABLE words ADD COLUMN example_updated_at TEXT")
        if "example_attempted_at" not in columns:
            conn.execute("ALTER TABLE words ADD COLUMN example_attempted_at TEXT")
        if "example_attempts" not in columns:
            conn.execute("ALTER TABLE words ADD COLUMN example_attempts INTEGER NOT NULL DEFAULT 0")
        if lexicon_id is not None:
            query = """
                WITH latest_reviews AS (
                    SELECT word_id, MAX(reviewed_at) AS last_reviewed_at
                    FROM reviews
                    GROUP BY word_id
                ),
                progress AS (
                    SELECT MAX(id) AS anchor_id
                    FROM words
                    WHERE lexicon_id = ? AND seen_count > 0
                ),
                candidate_window AS (
                    SELECT w.id, w.word, w.example_attempted_at
                    FROM words w
                    JOIN progress p ON p.anchor_id IS NOT NULL
                    WHERE w.lexicon_id = ?
                      AND w.id <= p.anchor_id
                      AND (w.example IS NULL OR TRIM(w.example) = '')
                    ORDER BY w.id DESC
                    LIMIT ?
                )
                SELECT cw.id, cw.word
                FROM candidate_window cw
                LEFT JOIN latest_reviews lr ON lr.word_id = cw.id
                ORDER BY
                  CASE WHEN cw.example_attempted_at IS NULL THEN 0 ELSE 1 END,
                  cw.id DESC,
                  cw.example_attempted_at,
                  COALESCE(lr.last_reviewed_at, cw.id) DESC
            """
            rows = conn.execute(query, (lexicon_id, lexicon_id, limit)).fetchall()
        else:
            query = """
                WITH latest_reviews AS (
                    SELECT word_id, MAX(reviewed_at) AS last_reviewed_at
                    FROM reviews
                    GROUP BY word_id
                )
                SELECT w.id, w.word
                FROM words w
                LEFT JOIN latest_reviews lr ON lr.word_id = w.id
                WHERE (w.example IS NULL OR TRIM(w.example) = '')
                ORDER BY
                  CASE WHEN w.example_attempted_at IS NULL THEN 0 ELSE 1 END,
                  COALESCE(lr.last_reviewed_at, w.updated_at, w.created_at) DESC,
                  w.example_attempted_at,
                  w.id DESC
                LIMIT ?
            """
            rows = conn.execute(query, (limit,)).fetchall()
        pending_rows = []
        for row in rows:
            word = row["word"].strip()
            if not re.fullmatch(r"[A-Za-z][A-Za-z' -]*", word):
                conn.execute(
                    """
                    UPDATE words
                    SET example_attempted_at = CURRENT_TIMESTAMP,
                        example_attempts = example_attempts + 1,
                        example_source = 'skipped-invalid'
                    WHERE id = ?
                    """,
                    (row["id"],),
                )
                skipped += 1
                continue
            pending_rows.append({"id": row["id"], "word": word})
        future_map = {}
        worker_count = max(1, min(max_workers, len(pending_rows) or 1))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            for item in pending_rows:
                future = executor.submit(fetch_example_for_word, item["word"], refresh)
                future_map[future] = item
            for future in as_completed(future_map):
                item = future_map[future]
                try:
                    example, source = future.result()
                except Exception as exc:  # noqa: BLE001
                    conn.execute(
                        """
                        UPDATE words
                        SET example_attempted_at = CURRENT_TIMESTAMP,
                            example_attempts = example_attempts + 1,
                            example_source = 'fetch-failed'
                        WHERE id = ?
                        """,
                        (item["id"],),
                    )
                    failures.append((item["word"], str(exc)))
                    continue
                if example:
                    conn.execute(
                        """
                        UPDATE words
                        SET example = ?, example_source = ?, example_updated_at = CURRENT_TIMESTAMP,
                            example_attempted_at = CURRENT_TIMESTAMP,
                            example_attempts = example_attempts + 1
                        WHERE id = ?
                        """,
                        (example, source, item["id"]),
                    )
                    updated += 1
                else:
                    conn.execute(
                        """
                        UPDATE words
                        SET example_attempted_at = CURRENT_TIMESTAMP,
                            example_attempts = example_attempts + 1,
                            example_source = 'not-found'
                        WHERE id = ?
                        """,
                        (item["id"],),
                    )
                    skipped += 1
                if sleep_seconds:
                    time.sleep(sleep_seconds)
        conn.commit()
    return {"updated": updated, "skipped": skipped, "failures": failures, "processed": len(rows)}
