"""
scraper.py – Transfer news web scraping engine.
Scrapes 13 sources concurrently, including Fabrizio Romano's own
Twitter/X feed (via Nitter) and his Caught Offside column.

Each source can declare multiple `urls` — the scraper tries them in order
and moves on to the next if one returns a 4xx/5xx error.  This makes the
pipeline resilient to sites that reorganise their URL structure.

Sources with `"type": "nitter"` are parsed differently: instead of
following article links, tweets are extracted directly from the listing
page and each tweet becomes an article. Romano's tweets get a +1
confidence boost because they are primary-source reports.
"""
import re
import time
import datetime
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

import requests
from bs4 import BeautifulSoup


# ── Source registry ────────────────────────────────────────────────────────
# `urls` is tried in order; first successful one wins.
SOURCES = [
    # ── PRIMARY SOURCE: Fabrizio Romano himself ──────────────────────────────
    {
        "name": "Fabrizio Romano (Twitter/X)",
        "type": "nitter",           # parsed as tweet listing, not article links
        "urls": [
            "https://nitter.privacydev.net/FabrizioRomano",
            "https://nitter.poast.org/FabrizioRomano",
            "https://nitter.unixfox.eu/FabrizioRomano",
            "https://nitter.net/FabrizioRomano",
            "https://nitter.cz/FabrizioRomano",
        ],
        "league_tags": ["All"],
    },
    {
        "name": "Fabrizio Romano (Caught Offside)",
        "urls": [
            "https://www.caughtoffside.com/author/fabrizio-romano/",
            "https://www.caughtoffside.com/category/transfer-news/",
        ],
        "article_selector": "a[href*='/20'], h2 a, h3 a",
        "title_sel": "h1",
        "body_sel": ".entry-content p, article p",
        "league_tags": ["All"],
    },
    # ── Other trusted sources ─────────────────────────────────────────────
    {
        "name": "BBC Sport Transfers",
        "urls": [
            "https://www.bbc.com/sport/football/transfers",
            "https://www.bbc.co.uk/sport/football/transfers",
        ],
        "article_selector": "a[href*='/sport/football/']",
        "title_sel": "h1, h2",
        "body_sel": "article p",
        "league_tags": ["All"],
    },
    {
        "name": "Goal.com Transfers",
        "urls": [
            "https://www.goal.com/en/transfer-news",
            "https://www.goal.com/en/news",
        ],
        "article_selector": "a[href*='/en/news/']",
        "title_sel": "h1",
        "body_sel": ".article-content p, article p",
        "league_tags": ["All"],
    },
    {
        "name": "Sky Sports Transfers",
        "urls": [
            "https://www.skysports.com/transfer-news",
            "https://www.skysports.com/football/news",
        ],
        "article_selector": "a[href*='/football/news/']",
        "title_sel": "h1",
        "body_sel": ".sdc-article-body p, .article__body p, article p",
        "league_tags": ["Premier League"],
    },
    {
        "name": "Transfermarkt News",
        "urls": [
            # Their ticker moved — try several common patterns
            "https://www.transfermarkt.com/transfers/transfers",
            "https://www.transfermarkt.com/transfers/neuzugaenge/statistik",
            "https://www.transfermarkt.com/transfers/transferticker/statistik",
            "https://www.transfermarkt.com/",
        ],
        "article_selector": "a[href*='/news/'], a[href*='/transfers/']",
        "title_sel": "h1, h2",
        "body_sel": ".tm-transfer-ticker p, article p, p",
        "league_tags": ["All"],
    },
    {
        "name": "Calciomercato",
        "urls": [
            "https://www.calciomercato.com/en/news",
            "https://www.calciomercato.com/en",
        ],
        "article_selector": "a[href*='/en/news/'], a[href*='/en/']",
        "title_sel": "h1",
        "body_sel": ".article-body p, article p",
        "league_tags": ["Serie A"],
    },
    {
        "name": "Marca Transfers",
        "urls": [
            # English section restructured — try several
            "https://www.marca.com/en/football.html",
            "https://www.marca.com/en/football/transfers.html",
            "https://www.marca.com/en/",
            "https://www.marca.com/en/football/news.html",
        ],
        "article_selector": "a[href*='/en/football/'], a[href*='/en/']",
        "title_sel": "h1",
        "body_sel": "article p, .article-content p, p",
        "league_tags": ["La Liga"],
    },
    {
        "name": "L'Equipe Football",
        "urls": [
            "https://www.lequipe.fr/Football/Transferts",
            "https://www.lequipe.fr/Football/",
        ],
        "article_selector": "a[href*='/Football/Article/']",
        "title_sel": "h1",
        "body_sel": ".article__body p, article p",
        "league_tags": ["Ligue 1"],
    },
    {
        "name": "Kicker Transfers",
        "urls": [
            "https://www.kicker.de/bundesliga/transfers",
            "https://www.kicker.de/bundesliga",
        ],
        "article_selector": "a[href*='/artikel/']",
        "title_sel": "h1",
        "body_sel": ".article__text p, article p",
        "league_tags": ["Bundesliga"],
    },
    {
        "name": "ESPN Soccer",
        "urls": [
            "https://www.espn.com/soccer/transfers",
            "https://www.espn.com/soccer/news",
            "https://www.espn.com/soccer/",
        ],
        "article_selector": "a[href*='/soccer/story/'], a[href*='/soccer/news/']",
        "title_sel": "h1",
        "body_sel": ".article-body p, .story__body p, section p",
        "league_tags": ["All"],
    },
    {
        "name": "MLS Soccer",
        "urls": [
            "https://www.mlssoccer.com/news/transfers",
            "https://www.mlssoccer.com/news/",
            "https://www.mlssoccer.com/",
        ],
        "article_selector": "a[href*='/news/'], a[href*='/post/']",
        "title_sel": "h1",
        "body_sel": ".article-body p, .mls-c-article__body p, article p",
        "league_tags": ["MLS"],
    },
    {
        "name": "Saudi Pro League News",
        "urls": [
            "https://www.arabnews.com/sport/football",
            "https://www.arabnews.com/taxonomy/term/20929",
            "https://www.goal.com/en-sa/transfer-news",
        ],
        "article_selector": "a[href*='/node/'], a[href*='/en-sa/news/']",
        "title_sel": "h1",
        "body_sel": "article p, .article-body p, p",
        "league_tags": ["Saudi Pro League"],
    },
]

# Expose a simple flat name→url mapping for the UI
SOURCE_NAMES = [s["name"] for s in SOURCES]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

REQUEST_TIMEOUT = 6        # seconds per individual HTTP request (fail fast)
SCRAPE_WALL_TIMEOUT = 25   # total wall-clock budget for the whole scrape run
MAX_ARTICLES_PER_SOURCE = 5
MAX_SCRAPE_THREADS = 6


class TransferScraper:
    """
    Scrapes transfer news from multiple sources concurrently.
    Each source can have multiple fallback URLs.
    Returns a list of article dicts sorted by confidence descending.
    """

    def scrape(
        self,
        query: str = "",
        league_filter: list[str] | None = None,
    ) -> list[dict]:
        results: list[dict] = []
        sources_to_scrape = self._filter_sources(league_filter)

        def scrape_one(source: dict) -> list[dict]:
            try:
                articles = self._scrape_source(source)
                if query:
                    articles = self._filter_by_relevance(articles, query)
                return articles[:MAX_ARTICLES_PER_SOURCE]
            except Exception as e:
                print(f"[Scraper] Failed on {source['name']}: {e}")
                return []

        with ThreadPoolExecutor(max_workers=MAX_SCRAPE_THREADS) as executor:
            futures = {
                executor.submit(scrape_one, src): src
                for src in sources_to_scrape
            }
            try:
                for future in as_completed(futures, timeout=SCRAPE_WALL_TIMEOUT):
                    try:
                        results.extend(future.result())
                    except Exception:
                        continue
            except FuturesTimeoutError:
                # Wall-clock budget exceeded — collect whatever already finished
                # and silently discard still-running futures.
                print(
                    f"[Scraper] Wall-clock timeout ({SCRAPE_WALL_TIMEOUT}s) reached. "
                    f"Collecting partial results from completed futures."
                )
                for future, src in futures.items():
                    if future.done():
                        try:
                            results.extend(future.result())
                        except Exception:
                            pass
                    else:
                        future.cancel()
                        print(f"[Scraper] Cancelled: {src['name']}")

        results.sort(key=lambda a: a.get("confidence", 1), reverse=True)
        return results

    # ── Source filtering ───────────────────────────────────────────────────
    def _filter_sources(self, league_filter: list[str] | None) -> list[dict]:
        if not league_filter or "All" in league_filter:
            return SOURCES
        return [
            s for s in SOURCES
            if "All" in s["league_tags"]
            or any(lg in s["league_tags"] for lg in league_filter)
        ]

    # ── Multi-URL scraping with fallback ───────────────────────────────────
    def _scrape_source(self, source: dict) -> list[dict]:
        """Try each URL in `source['urls']` until one works."""
        urls = source.get("urls", [source.get("url", "")])
        last_exc: Exception | None = None

        for url in urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                # Success — use nitter parser for tweet sources, else standard
                if source.get("type") == "nitter":
                    return self._parse_nitter(resp, url, source)
                return self._parse_listing(resp, url, source)
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else "?"
                print(f"[Scraper] {source['name']} HTTP {status} on {url} — trying next URL")
                last_exc = e
            except Exception as e:
                print(f"[Scraper] {source['name']} error on {url}: {e} — trying next URL")
                last_exc = e

        # All URLs exhausted
        if last_exc:
            raise last_exc
        return []

    # ── Nitter (Twitter/X proxy) parser ───────────────────────────────────
    def _parse_nitter(
        self, resp: requests.Response, base_url: str, source: dict
    ) -> list[dict]:
        """
        Extract tweets directly from a Nitter profile page.
        Each tweet becomes an article; retweets and replies are skipped.
        Romano's tweets get a +1 confidence boost as primary-source reports.
        """
        soup = BeautifulSoup(resp.text, "html.parser")
        articles: list[dict] = []

        # Nitter renders tweets as .timeline-item divs
        items = soup.select(".timeline-item, .tweet-body")

        for item in items:
            if len(articles) >= MAX_ARTICLES_PER_SOURCE:
                break

            # Skip retweets (they have a .retweet-header element)
            if item.select_one(".retweet-header"):
                continue

            # Skip replies (start with "@")
            content_el = item.select_one(".tweet-content, .tweet-text")
            if not content_el:
                continue
            text = content_el.get_text(separator=" ", strip=True)
            if not text or len(text) < 30:
                continue
            if text.startswith("@"):
                continue

            # Build URL — convert nitter path to real Twitter URL
            tweet_link_el = item.select_one("a.tweet-link, a[href*='/status/']")
            tweet_url = base_url  # fallback
            if tweet_link_el:
                href = tweet_link_el.get("href", "")
                if "/status/" in href:
                    # e.g. "/FabrizioRomano/status/12345" → twitter.com URL
                    tweet_url = "https://x.com" + href if href.startswith("/") else href

            # Parse date from the tooltip title on .tweet-date
            date_str = datetime.date.today().isoformat()
            date_el = item.select_one(".tweet-date a")
            if date_el:
                raw = date_el.get("title", "")  # e.g. "Jan 15, 2025 · 10:32 AM UTC"
                for fmt in ("%b %d, %Y", "%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        date_str = datetime.datetime.strptime(
                            raw.split("·")[0].strip(), fmt
                        ).date().isoformat()
                        break
                    except ValueError:
                        continue

            # Confidence: Romano's own words → +1 boost, capped at 5
            confidence = self._estimate_confidence(text)
            confidence = min(5, confidence + 1)

            # Use first ~120 chars as title
            title = text[:120] + ("…" if len(text) > 120 else "")

            articles.append({
                "title":       title,
                "text":        text,
                "source":      source["name"],
                "url":         tweet_url,
                "date":        date_str,
                "league_tags": source.get("league_tags", ["All"]),
                "confidence":  confidence,
            })

        return articles

    def _parse_listing(
        self, resp: requests.Response, base_url: str, source: dict
    ) -> list[dict]:
        soup = BeautifulSoup(resp.text, "html.parser")

        article_links: list[str] = []
        for a in soup.select(source.get("article_selector", "a"))[:15]:
            href = a.get("href", "")
            if href:
                full_url = urljoin(base_url, href)
                parsed_full = urlparse(full_url)
                parsed_base = urlparse(base_url)
                if parsed_full.netloc == parsed_base.netloc:
                    article_links.append(full_url)

        articles: list[dict] = []
        seen_urls: set[str] = set()

        for url in article_links:
            if url in seen_urls or url == base_url:
                continue
            seen_urls.add(url)
            if len(articles) >= MAX_ARTICLES_PER_SOURCE:
                break
            try:
                article = self._fetch_article(url, source)
                if article:
                    articles.append(article)
                time.sleep(0.25)
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
        text = " ".join(
            el.get_text(separator=" ", strip=True) for el in body_els[:10]
        )

        if not text.strip() or len(text) < 60:
            return None

        confidence = self._estimate_confidence(title + " " + text)
        return {
            "title":       title,
            "text":        text,
            "source":      source["name"],
            "url":         url,
            "date":        datetime.date.today().isoformat(),
            "league_tags": source["league_tags"],
            "confidence":  confidence,
        }

    # ── Confidence heuristic ───────────────────────────────────────────────
    @staticmethod
    def _estimate_confidence(text: str) -> int:
        t = text.lower()
        if any(kw in t for kw in [
            "here we go", "medical", "contract signed", "official",
            "done deal", "confirmed", "announcement",
        ]):
            return 5
        if any(kw in t for kw in [
            "agreement reached", "personal terms agreed", "fee agreed",
            "deal agreed", "terms agreed",
        ]):
            return 4
        if any(kw in t for kw in [
            "negotiations", "talks ongoing", "in talks",
            "bid submitted", "offer made", "bid accepted",
        ]):
            return 3
        if any(kw in t for kw in [
            "interest", "monitoring", "scouted", "considering", "target",
            "wants to sign", "looking at",
        ]):
            return 2
        return 1

    # ── Relevance filter ───────────────────────────────────────────────────
    @staticmethod
    def _filter_by_relevance(articles: list[dict], query: str) -> list[dict]:
        query_words = set(re.sub(r"[^\w\s]", "", query.lower()).split())
        if len(query_words) < 2:
            return articles
        scored = []
        for article in articles:
            haystack = (article["title"] + " " + article["text"]).lower()
            score = sum(1 for w in query_words if w in haystack)
            scored.append((score, article))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [a for s, a in scored if s > 0]
        return top if top else articles
