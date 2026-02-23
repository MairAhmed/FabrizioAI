"""
processor.py – In-memory article store for transfer news
Simple, no embeddings, no ChromaDB — just stores scraped articles in memory
and does keyword-based retrieval. Fast and zero external dependencies.
"""
import re
import hashlib
from datetime import datetime


class TransferProcessor:
    """
    Lightweight in-memory store for scraped transfer articles.
    Uses keyword matching instead of vector embeddings — no API calls needed.
    """

    def __init__(self):
        self._articles: dict[str, dict] = {}  # id → article

    def add_articles(self, articles: list[dict]) -> int:
        """Store articles, deduplicated by URL+title hash."""
        new_count = 0
        for article in articles:
            doc_id = self._hash_id(article.get("url", "") + article.get("title", ""))
            if doc_id not in self._articles:
                self._articles[doc_id] = article
                new_count += 1
        return new_count

    def retrieve(self, query: str, top_k: int = 6) -> list[dict]:
        """
        Keyword-based retrieval — scores each article by how many
        query words appear in its title + text.
        """
        if not self._articles:
            return []

        query_words = set(re.sub(r"[^\w\s]", "", query.lower()).split())
        scored = []

        for article in self._articles.values():
            haystack = (article.get("title", "") + " " + article.get("text", "")).lower()
            score = sum(1 for w in query_words if w in haystack)
            scored.append((score, article))

        # Sort by score descending, return top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [a for _, a in scored[:top_k]]

        # Add relevance_score field so the rest of the code stays compatible
        for i, article in enumerate(results):
            article["relevance_score"] = round(1 - (i / max(len(results), 1)), 2)

        return results

    def clear(self) -> None:
        """Wipe all stored articles."""
        self._articles = {}

    def stats(self) -> dict:
        return {"total_articles": len(self._articles)}

    @staticmethod
    def _hash_id(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()[:32]