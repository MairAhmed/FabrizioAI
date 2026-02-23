"""
scraper.py – Transfer news web scraping engine
Scrapes trusted football transfer sources and returns structured article dicts.
"""
import re
import time
import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# ── Source registry ────────────────────────────────────────────────────────
# Each entry: { url, name, article_selector, title_sel, body_sel, league_tags }
SOURCES = [
    {
        "name": "BBC Sport Transfers",
        "url": "https://www.bbc.com/sport/football/transfers",
        "type": "generic",
        "article_selector": "a[href*='/sport/football/']",
        "title_sel": "h1, h2",
        "body_sel": "article p",
        "league_tags": ["All"],
    },
    {
        "name": "Goal.com Transfers",
        "url": "https://www.goal.com/en/transfer-news",
        "type": "generic",
        "article_selector": "a[href*='/en/news/']",
        "title_sel": "h1",
        "body_sel": ".article-content p",
        "league_tags": ["All"],
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 5  # seconds - fail fast, don't block the whole pipeline
MAX_ARTICLES_PER_SOURCE = 5


class TransferScraper:
    """
    Scrapes transfer news from multiple sources.
    Returns a list of article dicts.
    """

    def scrape(
        self,
        query: str = "",
        league_filter: list[str] | None = None,
    ) -> list[dict]:
        """
        Main entry point. Scrapes relevant sources concurrently.
        """
        results = []
        sources_to_scrape = self._filter_sources(league_filter)

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def scrape_one(source):
            try:
                articles = self._scrape_source(source)
                if query:
                    articles = self._filter_by_relevance(articles, query)
                return articles[:MAX_ARTICLES_PER_SOURCE]
            except Exception as e:
                print(f"[Scraper] Failed on {source['name']}: {e}")
                return []

        # Scrape all sources in parallel (max 5 threads)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(scrape_one, source): source for source in sources_to_scrape}
            for future in as_completed(futures, timeout=15):  # 15s max total
                try:
                    results.extend(future.result())
                except Exception:
                    continue

        return results

    # ── Internal ───────────────────────────────────────────────────────────
    def _filter_sources(self, league_filter: list[str] | None) -> list[dict]:
        if not league_filter or "All" in league_filter:
            return SOURCES
        return [
            s for s in SOURCES
            if "All" in s["league_tags"]
            or any(lg in s["league_tags"] for lg in league_filter)
        ]

    def _scrape_source(self, source: dict) -> list[dict]:
        return self._scrape_generic(source)

    def _scrape_generic(self, source: dict) -> list[dict]:
        """Generic scraper for news sites."""
        resp = requests.get(source["url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        article_links = []
        for a in soup.select(source.get("article_selector", "a"))[:10]:
            href = a.get("href", "")
            if href:
                full_url = urljoin(source["url"], href)
                if urlparse(full_url).netloc == urlparse(source["url"]).netloc:
                    article_links.append(full_url)

        articles = []
        for url in list(set(article_links))[:MAX_ARTICLES_PER_SOURCE]:
            try:
                article = self._fetch_article(url, source)
                if article:
                    articles.append(article)
                time.sleep(0.3)
            except Exception:
                continue

        return articles

    def _fetch_article(self, url: str, source: dict) -> dict | None:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title_el = soup.select_one(source.get("title_sel", "h1"))
        title = title_el.get_text(strip=True) if title_el else "No title"

        body_els = soup.select(source.get("body_sel", "p"))
        text = " ".join(el.get_text(separator=" ", strip=True) for el in body_els[:8])

        if not text.strip():
            return None

        confidence = self._estimate_confidence(title + " " + text)
        return {
            "title": title,
            "text": text,
            "source": source["name"],
            "url": url,
            "date": datetime.date.today().isoformat(),
            "league_tags": source["league_tags"],
            "confidence": confidence,
        }

    def _estimate_confidence(self, text: str) -> int:
        """Heuristic confidence scoring based on transfer language."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["here we go", "medical", "contract signed", "official", "done deal", "confirmed"]):
            return 5
        if any(kw in text_lower for kw in ["agreement reached", "personal terms agreed", "fee agreed", "deal agreed"]):
            return 4
        if any(kw in text_lower for kw in ["negotiations", "talks ongoing", "in talks", "bid submitted", "offer made"]):
            return 3
        if any(kw in text_lower for kw in ["interest", "monitoring", "scouted", "considering", "target"]):
            return 2
        return 1

    def _filter_by_relevance(self, articles: list[dict], query: str) -> list[dict]:
        """Simple keyword match to filter articles by query relevance."""
        query_words = set(re.sub(r"[^\w\s]", "", query.lower()).split())
        if len(query_words) < 2:
            return articles  # Query too short to filter meaningfully

        scored = []
        for article in articles:
            haystack = (article["title"] + " " + article["text"]).lower()
            score = sum(1 for w in query_words if w in haystack)
            scored.append((score, article))

        scored.sort(key=lambda x: x[0], reverse=True)
        # Return all if nothing matches well, else return top matches
        top = [a for s, a in scored if s > 0]
        return top if top else articles