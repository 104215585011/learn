import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "data" / "vocab_sources"
CACHE_ROOT = ROOT / "data" / "multilingual_source_cache"
USER_AGENT = "FloatVocabMultilingualFetcher/2.0"
GOOGLE_TRANSLATE_ENDPOINT = "https://translate.googleapis.com/translate_a/single?client=gtx&sl={source}&tl=zh-CN&dt=t&q={query}"
CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
TOPIK_LEVELS = ("A", "B", "C")


@dataclass(frozen=True)
class FrequencySource:
    code: str
    label: str
    lexicon_name: str
    remote_path: str
    output_name: str

    @property
    def source_url(self) -> str:
        return f"https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/{self.code}/{self.remote_path}"


@dataclass(frozen=True)
class GradedSource:
    code: str
    label: str
    source_name: str
    source_url: str
    meaning_language: str
    level_kind: str
    output_prefix: str


CORE_LANGUAGE_SOURCES = {
    "es": FrequencySource("es", "Spanish", "Spanish Core 1000", "es_50k.txt", "spanish_core_1000.json"),
    "fr": FrequencySource("fr", "French", "French Core 1000", "fr_50k.txt", "french_core_1000.json"),
    "ko": FrequencySource("ko", "Korean", "Korean Core 1000", "ko_50k.txt", "korean_core_1000.json"),
    "ja": FrequencySource("ja", "Japanese", "Japanese Core 1000", "ja_full.txt", "japanese_core_1000.json"),
    "it": FrequencySource("it", "Italian", "Italian Core 1000", "it_50k.txt", "italian_core_1000.json"),
    "id": FrequencySource("id", "Indonesian", "Indonesian Core 1000", "id_50k.txt", "indonesian_core_1000.json"),
    "ru": FrequencySource("ru", "Russian", "Russian Core 1000", "ru_50k.txt", "russian_core_1000.json"),
    "ar": FrequencySource("ar", "Arabic", "Arabic Core 1000", "ar_50k.txt", "arabic_core_1000.json"),
    "pt": FrequencySource("pt", "Portuguese", "Portuguese Core 1000", "pt_50k.txt", "portuguese_core_1000.json"),
}


GRADED_LANGUAGE_SOURCES = {
    "ar": GradedSource(
        "ar",
        "Arabic",
        "gamescomputersplay/vocabulary-test",
        "https://raw.githubusercontent.com/gamescomputersplay/vocabulary-test/main/public/vocabapi/v3/wordsdata_ar.txt",
        "en",
        "cefr",
        "arabic_cefr",
    ),
    "es": GradedSource(
        "es",
        "Spanish",
        "gamescomputersplay/vocabulary-test",
        "https://raw.githubusercontent.com/gamescomputersplay/vocabulary-test/main/public/vocabapi/v3/wordsdata_es.txt",
        "en",
        "cefr",
        "spanish_cefr",
    ),
    "fr": GradedSource(
        "fr",
        "French",
        "gamescomputersplay/vocabulary-test",
        "https://raw.githubusercontent.com/gamescomputersplay/vocabulary-test/main/public/vocabapi/v3/wordsdata_fr.txt",
        "en",
        "cefr",
        "french_cefr",
    ),
    "it": GradedSource(
        "it",
        "Italian",
        "gamescomputersplay/vocabulary-test",
        "https://raw.githubusercontent.com/gamescomputersplay/vocabulary-test/main/public/vocabapi/v3/wordsdata_it.txt",
        "en",
        "cefr",
        "italian_cefr",
    ),
    "ja": GradedSource(
        "ja",
        "Japanese",
        "gamescomputersplay/vocabulary-test",
        "https://raw.githubusercontent.com/gamescomputersplay/vocabulary-test/main/public/vocabapi/v3/wordsdata_jp.txt",
        "en",
        "cefr",
        "japanese_cefr",
    ),
    "ko": GradedSource(
        "ko",
        "Korean",
        "julienshim/combined_korean_vocabulary_list",
        "https://raw.githubusercontent.com/julienshim/combined_korean_vocabulary_list/master/results.tsv",
        "ko",
        "topik",
        "korean_topik",
    ),
    "pt": GradedSource(
        "pt",
        "Portuguese",
        "gamescomputersplay/vocabulary-test",
        "https://raw.githubusercontent.com/gamescomputersplay/vocabulary-test/main/public/vocabapi/v3/wordsdata_pt.txt",
        "en",
        "cefr",
        "portuguese_cefr",
    ),
    "ru": GradedSource(
        "ru",
        "Russian",
        "gamescomputersplay/vocabulary-test",
        "https://raw.githubusercontent.com/gamescomputersplay/vocabulary-test/main/public/vocabapi/v3/wordsdata_ru.txt",
        "en",
        "cefr",
        "russian_cefr",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch multilingual vocab packs for FloatVocab.")
    parser.add_argument(
        "--languages",
        nargs="+",
        choices=sorted({*CORE_LANGUAGE_SOURCES.keys(), *GRADED_LANGUAGE_SOURCES.keys()}),
        default=sorted({*CORE_LANGUAGE_SOURCES.keys(), *GRADED_LANGUAGE_SOURCES.keys()}),
        help="Languages to fetch. Defaults to every supported non-English language.",
    )
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=("core", "graded"),
        default=("core", "graded"),
        help="Which pack families to build. Default: core graded",
    )
    parser.add_argument("--limit", type=int, default=1000, help="How many core high-frequency entries to keep per language.")
    parser.add_argument("--per-level-limit", type=int, default=0, help="Optional cap per graded level. 0 means keep all source rows.")
    parser.add_argument("--batch-size", type=int, default=80, help="How many strings to send per translation request.")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT, help=f"Output root. Default: {OUTPUT_ROOT}")
    parser.add_argument("--cache-dir", type=Path, default=CACHE_ROOT, help=f"Cache directory. Default: {CACHE_ROOT}")
    parser.add_argument("--refresh", action="store_true", help="Refetch remote source files even if cached copies exist.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary only without writing output files.")
    parser.add_argument("--skip-translate", action="store_true", help="Keep source-language definitions instead of translating to Chinese.")
    parser.add_argument("--import-db", type=Path, default=None, help="Optional SQLite database path. If set, generated JSON packs are imported into the app database.")
    return parser.parse_args()


def fetch_text(url: str, retries: int = 3) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/plain,*/*"})
    last_error: Exception | None = None
    for _attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=60) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except URLError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Failed to fetch {url}")


def fetch_cached_text(url: str, cache_path: Path, refresh: bool) -> str:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="utf-8")
    text = fetch_text(url)
    cache_path.write_text(text, encoding="utf-8")
    return text


def is_reasonable_vocab_token(token: str) -> bool:
    token = token.strip()
    if not token:
        return False
    if any(ch.isdigit() for ch in token):
        return False
    if len(token) == 1 and token in {"-", "_", ".", ","}:
        return False
    if token.startswith(("#", "@", "http")):
        return False
    if token.count(" ") > 2:
        return False
    return bool(re.search(r"\w", token, re.UNICODE))


def parse_frequency_rows(lines: list[str], limit: int) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    for line in lines:
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        word = " ".join(parts[:-1]).strip()
        frequency = parts[-1].strip()
        normalized_key = word.casefold()
        if not is_reasonable_vocab_token(word) or normalized_key in seen:
            continue
        seen.add(normalized_key)
        rows.append({"word": word, "frequency": frequency})
        if len(rows) >= limit:
            break
    return rows


def translate_batch(texts: list[str], source_language: str) -> list[str]:
    query = quote_plus("\n".join(texts))
    url = GOOGLE_TRANSLATE_ENDPOINT.format(source=source_language, query=query)
    payload = json.loads(fetch_text(url))
    translated_text = "".join(segment[0] for segment in payload[0] if segment and segment[0]).strip()
    translated = translated_text.split("\n")
    if len(translated) != len(texts):
        return [item.strip() for item in translated] + [""] * max(0, len(texts) - len(translated))
    return [item.strip() for item in translated]


def translate_texts(texts: list[str], source_language: str, batch_size: int, skip_translate: bool) -> list[str]:
    if skip_translate:
        return list(texts)
    translated: list[str] = []
    for index in range(0, len(texts), batch_size):
        translated.extend(translate_batch(texts[index : index + batch_size], source_language))
    return translated


def build_core_vocab_rows(source: FrequencySource, rows: list[dict], batch_size: int, skip_translate: bool) -> list[dict]:
    meanings = translate_texts([row["word"] for row in rows], source.code, batch_size, skip_translate)
    vocab_rows = []
    for index, row in enumerate(rows, start=1):
        meaning = meanings[index - 1] if index - 1 < len(meanings) else ""
        if not meaning:
            meaning = f"{source.label} 高频词汇"
        vocab_rows.append(
            {
                "word": row["word"],
                "meaning": meaning,
                "phonetic": "",
                "example": "",
                "language_code": source.code,
                "source": "hermitdave/FrequencyWords",
                "lexicon_name": source.lexicon_name,
                "rank": index,
                "frequency": row["frequency"],
            }
        )
    return vocab_rows


def parse_cefr_rows(text: str, language_code: str) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for raw_line in text.splitlines():
        parts = [part.strip() for part in raw_line.split("\t")]
        if len(parts) < 4:
            continue
        word, aux_text, level, source_meaning = parts[:4]
        if level not in CEFR_LEVELS or not is_reasonable_vocab_token(word) or not source_meaning:
            continue
        key = (level, word.casefold())
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "word": word,
                "phonetic": aux_text if language_code == "ja" else "",
                "level": level,
                "source_meaning": source_meaning,
            }
        )
    return rows


def parse_korean_topik_rows(text: str) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    reader = csv.DictReader(text.splitlines(), delimiter="\t")
    for raw in reader:
        word = (raw.get("word") or "").strip()
        level = (raw.get("topik_level") or "").strip().upper()
        meaning = (raw.get("explanation") or "").strip()
        if level not in TOPIK_LEVELS or not is_reasonable_vocab_token(word):
            continue
        if not meaning:
            meaning = word
        key = (level, word.casefold())
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "word": word,
                "phonetic": (raw.get("hanja") or "").strip(),
                "level": level,
                "source_meaning": meaning,
            }
        )
    return rows


def bucket_graded_rows(rows: list[dict], levels: tuple[str, ...], per_level_limit: int) -> dict[str, list[dict]]:
    bucketed = {level: [] for level in levels}
    for row in rows:
        level = row["level"]
        if level not in bucketed:
            continue
        if per_level_limit and len(bucketed[level]) >= per_level_limit:
            continue
        bucketed[level].append(row)
    return {level: items for level, items in bucketed.items() if items}


def build_graded_vocab_rows(
    source: GradedSource,
    level: str,
    rows: list[dict],
    batch_size: int,
    skip_translate: bool,
) -> list[dict]:
    meanings = translate_texts([row["source_meaning"] for row in rows], source.meaning_language, batch_size, skip_translate)
    vocab_rows = []
    lexicon_name = f"{source.label} {'CEFR' if source.level_kind == 'cefr' else 'TOPIK'} {level}"
    for index, row in enumerate(rows, start=1):
        meaning = meanings[index - 1] if index - 1 < len(meanings) else ""
        if not meaning:
            meaning = row["source_meaning"]
        vocab_rows.append(
            {
                "word": row["word"],
                "meaning": meaning,
                "phonetic": row.get("phonetic", ""),
                "example": "",
                "language_code": source.code,
                "source": source.source_name,
                "lexicon_name": lexicon_name,
                "level": level,
                "rank": index,
            }
        )
    return vocab_rows


def write_vocab_pack(output_dir: Path, output_name: str, vocab_rows: list[dict]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_name
    output_path.write_text(json.dumps(vocab_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def import_packs_into_db(db_path: Path, pack_paths: list[Path]) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app

    db = app.FloatVocabDB(db_path)
    try:
        for pack_path in pack_paths:
            db.import_words(str(pack_path), current_language_code="en")
    finally:
        db.conn.close()


def build_core_packs(args: argparse.Namespace, generated_paths: list[Path]) -> list[str]:
    messages: list[str] = []
    for language_code in args.languages:
        source = CORE_LANGUAGE_SOURCES.get(language_code)
        if not source:
            continue
        cache_path = args.cache_dir / "core" / f"{source.code}.txt"
        lines = fetch_cached_text(source.source_url, cache_path, args.refresh).splitlines()
        cleaned_rows = parse_frequency_rows(lines, args.limit)
        vocab_rows = build_core_vocab_rows(source, cleaned_rows, args.batch_size, args.skip_translate)
        if args.dry_run:
            messages.append(f"[dry-run] core {source.code}: {len(vocab_rows)} rows from {source.source_url}")
            continue
        output_path = write_vocab_pack(args.output_root / source.code, source.output_name, vocab_rows)
        generated_paths.append(output_path)
        messages.append(f"[ok] core {source.code}: wrote {len(vocab_rows)} rows -> {output_path}")
    return messages


def build_graded_packs(args: argparse.Namespace, generated_paths: list[Path]) -> list[str]:
    messages: list[str] = []
    for language_code in args.languages:
        source = GRADED_LANGUAGE_SOURCES.get(language_code)
        if not source:
            continue
        cache_path = args.cache_dir / "graded" / f"{source.code}.txt"
        text = fetch_cached_text(source.source_url, cache_path, args.refresh)
        if source.level_kind == "cefr":
            parsed_rows = parse_cefr_rows(text, source.code)
            buckets = bucket_graded_rows(parsed_rows, CEFR_LEVELS, args.per_level_limit)
            levels = CEFR_LEVELS
        else:
            parsed_rows = parse_korean_topik_rows(text)
            buckets = bucket_graded_rows(parsed_rows, TOPIK_LEVELS, args.per_level_limit)
            levels = TOPIK_LEVELS
        for level in levels:
            rows = buckets.get(level, [])
            if not rows:
                continue
            vocab_rows = build_graded_vocab_rows(source, level, rows, args.batch_size, args.skip_translate)
            output_name = f"{source.output_prefix}_{level.lower()}.json"
            if args.dry_run:
                messages.append(f"[dry-run] graded {source.code} {level}: {len(vocab_rows)} rows from {source.source_url}")
                continue
            output_path = write_vocab_pack(args.output_root / source.code, output_name, vocab_rows)
            generated_paths.append(output_path)
            messages.append(f"[ok] graded {source.code} {level}: wrote {len(vocab_rows)} rows -> {output_path}")
    return messages


def main() -> int:
    args = parse_args()
    failures: list[tuple[str, str]] = []
    generated_paths: list[Path] = []
    actions = []
    if "core" in args.profiles:
        actions.append(build_core_packs)
    if "graded" in args.profiles:
        actions.append(build_graded_packs)
    for action in actions:
        try:
            for message in action(args, generated_paths):
                print(message)
        except Exception as exc:
            failures.append((action.__name__, str(exc)))
            print(f"[warn] {action.__name__}: {exc}")
    if args.import_db and generated_paths and not args.dry_run:
        try:
            import_packs_into_db(args.import_db, generated_paths)
            print(f"[ok] imported {len(generated_paths)} packs into {args.import_db}")
        except Exception as exc:
            failures.append(("import_db", str(exc)))
            print(f"[warn] import_db: {exc}")
    if failures:
        print("\nFailed steps:")
        for step, error in failures:
            print(f"- {step}: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
