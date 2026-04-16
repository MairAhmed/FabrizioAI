"""
processor.py – Persistent article store for transfer news.
Uses SQLite for cross-session persistence with an in-memory cache for speed.
Also manages the watchlist (players/clubs to track).
"""
import re
import json
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / ".chroma_db" / "articles.db"


class TransferProcessor:
    """
    SQLite-backed store for scraped transfer articles.
    In-memory dict acts as a fast cache; SQLite persists between sessions.
    Also handles watchlist storage.
    """

    def __init__(self):
        self._articles: dict[str, dict] = {}
        self._db_path = DB_PATH
        self._init_db()
        self._load_from_db()

    # ── DB bootstrap ───────────────────────────────────────────────────────
    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id          TEXT PRIMARY KEY,
                    title       TEXT,
                    text        TEXT,
                    source      TEXT,
                    url         TEXT,
                    date        TEXT,
                    league_tags TEXT,
                    confidence  INTEGER DEFAULT 1,
                    created_at  TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT UNIQUE,
                    type       TEXT DEFAULT 'player',
                    created_at TEXT
                )
            """)
            conn.commit()

    def _load_from_db(self) -> None:
        """Load the 500 most-recent articles from SQLite into the in-memory cache."""
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, title, text, source, url, date, league_tags, confidence "
                "FROM articles ORDER BY created_at DESC LIMIT 500"
            ).fetchall()
        for row in rows:
            article = {
                "title":       row[1],
                "text":        row[2],
                "source":      row[3],
                "url":         row[4],
                "date":        row[5],
                "league_tags": json.loads(row[6]) if row[6] else [],
                "confidence":  row[7],
            }
            self._articles[row[0]] = article

    # ── Public API ─────────────────────────────────────────────────────────
    def add_articles(self, articles: list[dict]) -> int:
        """Store new articles, deduplicating by URL+title hash. Returns count added."""
        new_count = 0
        with sqlite3.connect(self._db_path) as conn:
            for article in articles:
                doc_id = self._hash_id(
                    article.get("url", "") + article.get("title", "")
                )
                if doc_id not in self._articles:
                    self._articles[doc_id] = article
                    new_count += 1
                    conn.execute(
                        "INSERT OR IGNORE INTO articles "
                        "VALUES (?,?,?,?,?,?,?,?,?)",
                        (
                            doc_id,
                            article.get("title", ""),
                            article.get("text", ""),
                            article.get("source", ""),
                            article.get("url", ""),
                            article.get("date", ""),
                            json.dumps(article.get("league_tags", [])),
                            article.get("confidence", 1),
                            datetime.now().isoformat(),
                        ),
                    )
            conn.commit()
        return new_count

    def retrieve(self, query: str, top_k: int = 6) -> list[dict]:
        """Keyword-based retrieval ranked by overlap with the query."""
        if not self._articles:
            return []

        query_words = set(re.sub(r"[^\w\s]", "", query.lower()).split())
        scored = []
        for article in self._articles.values():
            haystack = (
                article.get("title", "") + " " + article.get("text", "")
            ).lower()
            score = sum(1 for w in query_words if w in haystack)
            scored.append((score, article))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [a for _, a in scored[:top_k]]

        for i, article in enumerate(results):
            article["relevance_score"] = round(
                1 - (i / max(len(results), 1)), 2
            )
        return results

    def get_recent_articles(
        self, limit: int = 30, min_confidence: int = 1
    ) -> list[dict]:
        """Return the most recent articles above a confidence threshold."""
        articles = [
            a
            for a in self._articles.values()
            if a.get("confidence", 1) >= min_confidence
        ]
        articles.sort(key=lambda x: x.get("date", ""), reverse=True)
        return articles[:limit]

    # ── Watchlist ──────────────────────────────────────────────────────────
    def get_watchlist(self) -> list[dict]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, name, type, created_at FROM watchlist ORDER BY created_at DESC"
            ).fetchall()
        return [
            {"id": r[0], "name": r[1], "type": r[2], "created_at": r[3]}
            for r in rows
        ]

    def add_to_watchlist(self, name: str, type_: str = "player") -> bool:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO watchlist (name, type, created_at) VALUES (?,?,?)",
                    (name.strip(), type_, datetime.now().isoformat()),
                )
                conn.commit()
            return True
        except Exception:
            return False

    def remove_from_watchlist(self, item_id: int) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM watchlist WHERE id=?", (item_id,))
            conn.commit()

    # ── Utility ────────────────────────────────────────────────────────────
    def clear(self) -> None:
        """Wipe the in-memory cache (does not touch SQLite)."""
        self._articles = {}

    def stats(self) -> dict:
        dates = [
            a.get("date", "")
            for a in self._articles.values()
            if a.get("date")
        ]
        last_scrape = max(dates) if dates else "Never"
        sources = sorted(
            set(a.get("source", "") for a in self._articles.values() if a.get("source"))
        )
        conf_dist = {}
        for a in self._articles.values():
            c = a.get("confidence", 1)
            conf_dist[c] = conf_dist.get(c, 0) + 1
        return {
            "total_articles": len(self._articles),
            "sources_scraped": sources,
            "last_scrape": last_scrape,
            "confidence_distribution": conf_dist,
        }

    @staticmethod
    def _hash_id(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
