"""
pages/1_📰_News_Feed.py – Live Transfer News Feed
Card-based browsable ticker of all scraped articles,
with league filters, confidence filter, and sort controls.
"""

import sys
import time
from pathlib import Path
from datetime import datetime

import streamlit as st

# ── Path setup ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # app/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))  # scripts/

from processor import TransferProcessor
from scraper import TransferScraper, SOURCES

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FabrizioAI – News Feed",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared instances (cached so they survive reruns) ──────────────────────
@st.cache_resource
def get_processor():
    return TransferProcessor()

@st.cache_resource
def get_scraper():
    return TransferScraper()

_processor = get_processor()
_scraper   = get_scraper()

# ── League palette (mirrors main.py) ─────────────────────────────────────
LEAGUE_COLORS = {
    "Premier League": {"bg": "#3d195b", "text": "#c8a2e8", "border": "#6a2e9e"},
    "La Liga":        {"bg": "#9b1c1c", "text": "#fca5a5", "border": "#dc2626"},
    "Serie A":        {"bg": "#1e3a5f", "text": "#93c5fd", "border": "#2563eb"},
    "Bundesliga":     {"bg": "#1a1a00", "text": "#fde047", "border": "#ca8a04"},
    "Ligue 1":        {"bg": "#003153", "text": "#7dd3fc", "border": "#0369a1"},
    "All":            {"bg": "#1e2a1e", "text": "#86efac", "border": "#16a34a"},
}

CONF_COLORS = {1: "#ef4444", 2: "#f97316", 3: "#f59e0b", 4: "#3b82f6", 5: "#22c55e"}
CONF_LABELS = {
    1: "Rumour 🌫️",
    2: "Interest 👀",
    3: "Talks 🗣️",
    4: "Deal Close 🤝",
    5: "HERE WE GO! 🎉",
}

SOURCE_LEAGUE_MAP = {
    "Fabrizio Romano (Twitter/X)":       "All",
    "Fabrizio Romano (Caught Offside)":  "All",
    "ESPN Soccer":           "All",
    "BBC Sport Transfers":   "All",
    "Goal.com Transfers":    "All",
    "Sky Sports Transfers":  "Premier League",
    "Transfermarkt News":    "All",
    "Calciomercato":         "Serie A",
    "Marca Transfers":       "La Liga",
    "L'Equipe Football":     "Ligue 1",
    "Kicker Transfers":      "Bundesliga",
    "MLS Soccer":            "MLS",
    "Saudi Pro League News": "Saudi Pro League",
}

# ── CSS ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  h1, h2, h3, h4 { font-family: 'Oswald', sans-serif; letter-spacing: 0.03em; }
  .stApp { background: #0d0d0d; color: #f0f0f0; }

  .feed-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-bottom: 3px solid #e94560;
    padding: 1.2rem 2rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
  }
  .feed-header h1 { color: #fff; font-size: 2rem; margin: 0; }
  .feed-header .sub { color: #e94560; font-size: 0.82rem; letter-spacing: 0.15em; text-transform: uppercase; }

  .news-card {
    background: linear-gradient(135deg, #111827 0%, #1e293b 100%);
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s, box-shadow 0.2s;
    height: 100%;
  }
  .news-card:hover {
    border-color: #e94560;
    box-shadow: 0 2px 20px rgba(233,69,96,0.12);
  }

  .card-title {
    font-family: 'Oswald', sans-serif;
    font-size: 1.02rem;
    color: #f1f5f9;
    margin: 0 0 0.4rem 0;
    line-height: 1.35;
  }
  .card-body {
    font-size: 0.83rem;
    color: #94a3b8;
    line-height: 1.55;
    margin: 0.4rem 0 0.6rem;
    display: -webkit-box;
    -webkit-line-clamp: 4;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .card-meta {
    font-size: 0.72rem;
    color: #475569;
    margin-top: 0.4rem;
  }

  .conf-pill {
    display: inline-block;
    font-family: 'Oswald', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 0.07em;
    padding: 1px 9px;
    border-radius: 12px;
    margin-right: 6px;
  }

  .league-tag {
    display: inline-block;
    font-size: 0.68rem;
    padding: 1px 7px;
    border-radius: 5px;
    border-width: 1px;
    border-style: solid;
  }

  .conf-bar-wrap {
    background: #1e293b;
    border-radius: 4px;
    height: 5px;
    overflow: hidden;
    margin: 6px 0 4px;
  }
  .conf-bar-fill { height: 100%; border-radius: 4px; }

  .source-link {
    color: #60a5fa;
    text-decoration: none;
    font-size: 0.75rem;
  }
  .source-link:hover { text-decoration: underline; }

  .empty-feed {
    text-align: center;
    padding: 4rem 2rem;
    color: #4b5563;
  }
  .empty-feed h3 { color: #6b7280; }

  section[data-testid="stSidebar"] {
    background: #0a0a0a;
    border-right: 1px solid #1e1e2e;
  }

  .stat-box {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 0.6rem 0.9rem;
    margin: 0.3rem 0;
    text-align: center;
  }
  .stat-box .val { font-family:'Oswald',sans-serif; font-size:1.4rem; color:#e2e8f0; }
  .stat-box .lbl { font-size: 0.72rem; color: #64748b; }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="feed-header">
  <h1>📰 Transfer News Feed</h1>
  <div class="sub">Live ticker · All scraped articles · Sorted by confidence</div>
</div>
""", unsafe_allow_html=True)


# ── Sidebar controls ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎛️ Feed Filters")

    league_filter = st.multiselect(
        "Leagues",
        ["All", "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1", "MLS", "Saudi Pro League"],
        default=["All"],
    )
    min_conf = st.slider("Min. confidence", 1, 5, 1,
                         help="1 = show all · 5 = confirmed only")
    sort_by  = st.radio("Sort by", ["Confidence ↓", "Date ↓", "Source A–Z"])
    cols_n   = st.radio("Columns", [1, 2, 3], index=1, horizontal=True)

    st.divider()
    st.markdown("### 🔄 Refresh Feed")
    scrape_query = st.text_input("Topic to scrape (optional)", placeholder="e.g. Arsenal striker")
    scrape_leagues = st.multiselect(
        "Leagues to scrape",
        ["All", "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1", "MLS", "Saudi Pro League"],
        default=["All"],
    )
    if st.button("🌐 Scrape Now", use_container_width=True, type="primary"):
        with st.spinner("Scraping 13 sources…"):
            try:
                articles = _scraper.scrape(
                    query=scrape_query or "",
                    league_filter=scrape_leagues,
                )
                added = _processor.add_articles(articles)
                st.success(f"✅ {added} new articles added ({len(articles)} total scraped).")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Scrape error: {e}")

    st.divider()

    # Stats
    stats = _processor.stats()
    st.markdown("### 📊 Knowledge Base")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div class="stat-box"><div class="val">{stats["total_articles"]}</div>'
            f'<div class="lbl">Articles</div></div>', unsafe_allow_html=True,
        )
    with c2:
        src_count = len(stats["sources_scraped"])
        st.markdown(
            f'<div class="stat-box"><div class="val">{src_count}</div>'
            f'<div class="lbl">Sources</div></div>', unsafe_allow_html=True,
        )
    st.caption(f"Last scrape: {stats['last_scrape']}")

    if st.button("← Back to Chat", use_container_width=True):
        st.switch_page("main.py")



# ── Language & sport display filters (safety net for existing KB articles) ─
_NON_ENG = frozenset({
    "les","des","une","dans","avec","pour","mais","très","selon","depuis",
    "lors","cette","aussi","même","tout","après","avant","dont","jamais",
    "encore","toujours","peut","être","quand","sous","vers",            # FR
    "los","las","para","también","pero","están","cuando","donde","aunque",
    "desde","hasta","nunca","siempre","después","sobre","siendo","según",  # ES
    "und","nicht","sich","aber","wird","kann","oder","wenn","nach","über",
    "beim","durch","gegen","ohne","unter","zwischen","dann","schon","dass", # DE
    "della","dello","degli","delle","nella","sono","hanno","anche","molto",
    "tutto","dopo","prima","perché","però","ogni","questi","queste",        # IT
})
_OTHER_SPORTS = frozenset({
    "nba","nfl","nhl","mlb","wnba","basketball","american football",
    "baseball","softball","ice hockey","cricket","test match",
    "tennis","wimbledon","golf","masters tournament","pga tour",
    "formula 1","formula one","f1 race","grand prix","motogp","nascar",
    "rugby union","rugby league","six nations","swimming","athletics",
    "track and field","cycling","tour de france","boxing","ufc","mma",
    "volleyball","handball","olympic games","olympics",
})

def _is_english(title: str, text: str) -> bool:
    combined = (title + " " + text).lower()
    words = [w for w in combined.split() if len(w) > 2]
    if len(words) < 10:
        return True
    hits = sum(1 for w in words if w in _NON_ENG)
    return (hits / len(words)) < 0.06

def _is_football(title: str, text: str) -> bool:
    combined = (title + " " + text[:500]).lower()
    return not any(term in combined for term in _OTHER_SPORTS)

# ── Fetch & filter articles ────────────────────────────────────────────────
all_articles = [
    a for a in _processor.get_recent_articles(limit=200, min_confidence=min_conf)
    if _is_english(a.get("title", ""), a.get("text", ""))
    and _is_football(a.get("title", ""), a.get("text", ""))
]

# League filter
def article_matches_league(article: dict, filters: list[str]) -> bool:
    if "All" in filters:
        return True
    tags = article.get("league_tags", ["All"])
    if "All" in tags:
        return True
    return any(f in tags for f in filters)

filtered = [a for a in all_articles if article_matches_league(a, league_filter)]

# Sort
if sort_by == "Confidence ↓":
    filtered.sort(key=lambda a: a.get("confidence", 1), reverse=True)
elif sort_by == "Date ↓":
    filtered.sort(key=lambda a: a.get("date", ""), reverse=True)
else:
    filtered.sort(key=lambda a: a.get("source", ""))


# ── Render ────────────────────────────────────────────────────────────────
if not filtered:
    st.markdown("""
    <div class="empty-feed">
      <h3>📭 No articles yet</h3>
      <p>Click <strong>Scrape Now</strong> in the sidebar to pull live transfer news,<br>
         or ask a question in the <strong>Chat</strong> to populate the knowledge base.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.caption(f"Showing **{len(filtered)}** articles")

    # Split into column chunks
    chunks = [filtered[i::cols_n] for i in range(cols_n)]
    col_objs = st.columns(cols_n)

    for col_obj, chunk in zip(col_objs, chunks):
        with col_obj:
            for article in chunk:
                conf      = article.get("confidence", 1)
                conf_col  = CONF_COLORS.get(conf, "#6b7280")
                conf_lbl  = CONF_LABELS.get(conf, "")
                conf_pct  = int((conf / 5) * 100)

                src       = article.get("source", "Unknown")
                league    = SOURCE_LEAGUE_MAP.get(src, "All")
                pal       = LEAGUE_COLORS.get(league, LEAGUE_COLORS["All"])

                title     = article.get("title", "No title")
                body      = article.get("text", "")[:280]
                url       = article.get("url", "#")
                date      = article.get("date", "")

                st.markdown(f"""
                <div class="news-card">
                  <div class="card-title">{title}</div>
                  <div class="conf-bar-wrap">
                    <div class="conf-bar-fill" style="width:{conf_pct}%;background:{conf_col};"></div>
                  </div>
                  <span class="conf-pill" style="background:{conf_col}22;color:{conf_col};border:1px solid {conf_col}44;">
                    {conf_lbl}
                  </span>
                  <span class="league-tag"
                    style="background:{pal['bg']};color:{pal['text']};border-color:{pal['border']};">
                    {league}
                  </span>
                    <div class="card-body">{body}…</div>
                  <div class="card-meta">
                    📡 <a class="source-link" href="{url}" target="_blank">{src}</a>
                    &nbsp;·&nbsp; 📅 {date}
                  </div>
                </div>
                """, unsafe_allow_html=True)
