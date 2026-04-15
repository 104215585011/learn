from dataclasses import dataclass


@dataclass
class WordCard:
    id: int
    word: str
    phonetic: str
    meaning: str
    example: str
    status: str
    lexicon_name: str

