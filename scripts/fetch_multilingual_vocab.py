import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "data" / "vocab_sources"
USER_AGENT = "FloatVocabMultilingualFetcher/1.0"
GOOGLE_TRANSLATE_ENDPOINT = "https://translate.googleapis.com/translate_a/single?client=gtx&sl={source}&tl=zh-CN&dt=t&q={query}"


@dataclass(frozen=True)
class LanguageSource:
    code: str
    label: str
    lexicon_name: str
    remote_path: str
    output_name: str

    @property
    def source_url(self) -> str:
        return f"https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/{self.code}/{self.remote_path}"


LANGUAGE_SOURCES = {
    "es": LanguageSource("es", "Spanish", "Spanish Core 1000", "es_50k.txt", "spanish_core_1000.json"),
    "fr": LanguageSource("fr", "French", "French Core 1000", "fr_50k.txt", "french_core_1000.json"),
    "ko": LanguageSource("ko", "Korean", "Korean Core 1000", "ko_50k.txt", "korean_core_1000.json"),
    "ja": LanguageSource("ja", "Japanese", "Japanese Core 1000", "ja_full.txt", "japanese_core_1000.json"),
    "it": LanguageSource("it", "Italian", "Italian Core 1000", "it_50k.txt", "italian_core_1000.json"),
    "id": LanguageSource("id", "Indonesian", "Indonesian Core 1000", "id_50k.txt", "indonesian_core_1000.json"),
    "ru": LanguageSource("ru", "Russian", "Russian Core 1000", "ru_50k.txt", "russian_core_1000.json"),
    "ar": LanguageSource("ar", "Arabic", "Arabic Core 1000", "ar_50k.txt", "arabic_core_1000.json"),
    "pt": LanguageSource("pt", "Portuguese", "Portuguese Core 1000", "pt_50k.txt", "portuguese_core_1000.json"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch multilingual high-frequency vocab packs for FloatVocab.")
    parser.add_argument(
        "--languages",
        nargs="+",
        choices=sorted(LANGUAGE_SOURCES.keys()),
        default=sorted(LANGUAGE_SOURCES.keys()),
        help="Languages to fetch. Defaults to all non-English supported languages.",
    )
    parser.add_argument("--limit", type=int, default=1000, help="How many cleaned high-frequency entries to keep per language.")
    parser.add_argument("--batch-size", type=int, default=80, help="How many words to send per translation request.")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT, help=f"Output root. Default: {OUTPUT_ROOT}")
    parser.add_argument("--refresh", action="store_true", help="Refetch remote frequency files even if cached copies exist.")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "multilingual_source_cache", help="Cache directory for remote word lists.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary only without writing output files.")
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


def cached_frequency_lines(source: LanguageSource, cache_dir: Path, refresh: bool) -> list[str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{source.code}.txt"
    if cache_path.exists() and not refresh:
        text = cache_path.read_text(encoding="utf-8")
    else:
        text = fetch_text(source.source_url)
        cache_path.write_text(text, encoding="utf-8")
    return text.splitlines()


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


def translate_batch(words: list[str], source_language: str) -> list[str]:
    query = quote_plus("\n".join(words))
    url = GOOGLE_TRANSLATE_ENDPOINT.format(source=source_language, query=query)
    payload = json.loads(fetch_text(url))
    translated_text = "".join(segment[0] for segment in payload[0] if segment and segment[0]).strip()
    translations = translated_text.split("\n")
    if len(translations) != len(words):
        return [item.strip() for item in translations] + [""] * max(0, len(words) - len(translations))
    return [item.strip() for item in translations]


def build_vocab_rows(source: LanguageSource, rows: list[dict], batch_size: int) -> list[dict]:
    words = [row["word"] for row in rows]
    translated: list[str] = []
    for index in range(0, len(words), batch_size):
        translated.extend(translate_batch(words[index : index + batch_size], source.code))
    vocab_rows = []
    for index, row in enumerate(rows, start=1):
        meaning = translated[index - 1] if index - 1 < len(translated) else ""
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


def write_vocab_pack(source: LanguageSource, output_root: Path, vocab_rows: list[dict]) -> Path:
    output_dir = output_root / source.code
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / source.output_name
    output_path.write_text(json.dumps(vocab_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> int:
    args = parse_args()
    failures: list[tuple[str, str]] = []
    for language_code in args.languages:
        source = LANGUAGE_SOURCES[language_code]
        try:
            lines = cached_frequency_lines(source, args.cache_dir, args.refresh)
            cleaned_rows = parse_frequency_rows(lines, args.limit)
            vocab_rows = build_vocab_rows(source, cleaned_rows, args.batch_size)
            if args.dry_run:
                print(f"[dry-run] {source.code}: {len(vocab_rows)} rows from {source.source_url}")
                continue
            output_path = write_vocab_pack(source, args.output_root, vocab_rows)
            print(f"[ok] {source.code}: wrote {len(vocab_rows)} rows -> {output_path}")
        except Exception as exc:
            failures.append((source.code, str(exc)))
            print(f"[warn] {source.code}: {exc}")
    if failures:
        print("\nFailed languages:")
        for code, error in failures:
            print(f"- {code}: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
