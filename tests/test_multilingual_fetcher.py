import importlib.util
import shutil
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "fetch_multilingual_vocab.py"
SPEC = importlib.util.spec_from_file_location("fetch_multilingual_vocab", SCRIPT_PATH)
fetcher = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(fetcher)


TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / "tests" / "_tmp_fetcher"


class MultilingualFetcherTests(unittest.TestCase):
    def test_parse_cefr_rows_keeps_level_and_japanese_reading(self):
        text = "\n".join(
            [
                "hola\t\tB1\thello",
                "hola\t\tB1\thello again",
                "adios\t\tB2\tgoodbye",
                "学校\tガッコウ\tA1\tschool",
            ]
        )

        spanish_rows = fetcher.parse_cefr_rows(text, "es")
        japanese_rows = fetcher.parse_cefr_rows(text, "ja")

        self.assertEqual([(row["word"], row["level"]) for row in spanish_rows[:2]], [("hola", "B1"), ("adios", "B2")])
        self.assertEqual(japanese_rows[-1]["phonetic"], "ガッコウ")

    def test_parse_korean_topik_rows_filters_and_buckets_levels(self):
        text = "\n".join(
            [
                "rank\tword\tpart_of_speech\thanja\texplanation\tnikl_level\ttopik_level",
                "1\t가게\t명사\t\t가게\t초급\tA",
                "2\t가격\t명사\t價格\t가격\t초급\tB",
                "3\t사과\t명사\t\t사과\t\tC",
                "4\t123\t명사\t\t숫자\t초급\tA",
            ]
        )

        rows = fetcher.parse_korean_topik_rows(text)
        bucketed = fetcher.bucket_graded_rows(rows, fetcher.TOPIK_LEVELS, per_level_limit=0)

        self.assertEqual([row["word"] for row in rows], ["가게", "가격", "사과"])
        self.assertEqual(sorted(bucketed.keys()), ["A", "B", "C"])

    def test_build_graded_vocab_rows_embeds_metadata(self):
        source = fetcher.GRADED_LANGUAGE_SOURCES["es"]
        rows = [
            {"word": "hola", "phonetic": "", "level": "B1", "source_meaning": "hello"},
            {"word": "adios", "phonetic": "", "level": "B1", "source_meaning": "goodbye"},
        ]

        vocab_rows = fetcher.build_graded_vocab_rows(source, "B1", rows, batch_size=10, skip_translate=True)

        self.assertEqual(vocab_rows[0]["lexicon_name"], "Spanish CEFR B1")
        self.assertEqual(vocab_rows[0]["language_code"], "es")
        self.assertEqual(vocab_rows[1]["meaning"], "goodbye")

    def test_write_vocab_pack_persists_json(self):
        TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
        temp_dir = TEST_TMP_ROOT / "write_vocab_pack_case"
        temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))

        output_path = fetcher.write_vocab_pack(
            temp_dir,
            "sample.json",
            [{"word": "hola", "meaning": "你好", "language_code": "es", "lexicon_name": "Spanish CEFR B1"}],
        )

        self.assertTrue(output_path.exists())
        self.assertIn("hola", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
