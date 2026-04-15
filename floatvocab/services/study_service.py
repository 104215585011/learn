from __future__ import annotations


class StudyService:
    def __init__(self, db):
        self.db = db

    def get_next_card(self):
        return self.db.next_card()

    def submit_review(self, word_id: int, rating: int):
        return self.db.review(word_id, rating)

    def get_study_stats(self):
        return self.db.stats()

    def get_recent_words(self, lexicon_id: int, limit: int = 80):
        return self.db.recent_words(lexicon_id, limit)
