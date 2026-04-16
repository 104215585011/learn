from __future__ import annotations

from typing import Callable


def _missing_enrich_database(*_args, **_kwargs):
    raise NotImplementedError("enrich_database is not configured")


class EnrichmentService:
    def __init__(self, db_path, enrich_database: Callable | None = None):
        self.db_path = db_path
        self.enrich_database = enrich_database or _missing_enrich_database

    def enrich_examples(self, lexicon_id=None, limit: int = 200, refresh: bool = False):
        return self.enrich_database(self.db_path, limit=limit, refresh=refresh, lexicon_id=lexicon_id)
