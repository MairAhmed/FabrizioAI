"""
pages/3_⏱️_Timeline.py – Transfer Timeline
Chronological feed of all KB articles grouped by date,
with a visual timeline spine, confidence colour-coding,
and league/confidence filters.
"""

import sys
import re
from pathlib import Path
from collections import defaultdict

import streamlit as st

# ── Path setup ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))               # app/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))   # scripts/

from processor import TransferProcessor

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FabrizioAI – Timeline",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_resource
def get_processor():
    return TransferProcessor()

_processor = get_processor()

# ── Colour palettes ────────────────────────────────────────────────────────
CONF_COLORS = {
    1: {"bg": "#2d0a0a", "border": "#ef4444", "text": "#fca5a5", "label": "Rumour 🌫️"},
    2: {"bg": "#2d1a00", "border": "#f97316", "text": "#fdba74", "label": "Interest 👀"},
    3: {"bg": "#1c1500", "border": "#f59e0b", "text": "#fcd34d", "label": "Talks 🗣️"},
    4: {"bg": "#0a1a2d", "border": "#3b82f6", "text": "#93c5fd", "label": "Deal Close 🤝"},
    5: {"bg": "#052e0f", "border": "#22c55e", "text": "#86efac", "label": "HERE WE GO! 🎉"},
}

LEAGUE_COLORS = {
    "Premier League":   {"bg": "#3d195b", "text": "#c8a2e8", "border": "#6a2e9e"},
    "La Liga":          {"bg": "#9b1c1c", "text": "#fca5a5", "border": "#dc2626"},
    "Serie A":          {"bg": "#1e3a5f", "text": "#93c5fd", "border": "#2563eb"},
    "Bundesliga":       {"bg": "#1a1a00", "text": "#fde047", "border": "#ca8a04"},
    "Ligue 1":          {"bg": "#003153", "text": "#7dd3fc", "border": "#0369a1"},
    "MLS":              {"bg": "#002f6c", "text": "#7fb3f5", "border": "#1a56a0"},
    "Saudi Pro League": {"bg": "#003d1a", "text": "#6ee09a", "border": "#00a651"},
    "All":              {"bg": "#1e2a1e", "text": "#86efac", "border": "#16a34a"},
}

SOURCE_LEAGUE_MAP = {
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

  .tl-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-bottom: 3px solid #f59e0b;
    padding: 1.2rem 2rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
  }
  .tl-header h1  { color: #fff; font-size: 2rem; margin: 0; }
  .tl-header .sub { color: #f59e0b; font-size: 0.82rem; letter-spacing: 0.15em; text-transform: uppercase; }

  /* Date group header */
  .date-group {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 2rem 0 0.8rem 0;
  }
  .date-badge {
    font-family: 'Oswald', sans-serif;
    font-size: 1rem;
    color: #f59e0b;
    background: #1c1500;
    border: 1px solid #78350f;
    border-radius: 8px;
    padding: 4px 14px;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .date-line {
    flex: 1;
    height: 1px;
    background: linear-gradient(to right, #78350f44, transparent);
  }

  /* Timeline entry */
  .tl-entry {
    display: flex;
    gap: 0;
    margin: 0 0 0.7rem 1.2rem;
    position: relative;
  }
  /* Vertical spine */
  .tl-spine {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 28px;
    flex-shrink: 0;
  }
  .tl-dot {
    width: 11px;
    height: 11px;
    border-radius: 50%;
    border: 2px solid;
    flex-shrink: 0;
    margin-top: 4px;
  }
  .tl-line {
    width: 2px;
    flex: 1;
    min-height: 20px;
    background: #1e293b;
    margin-top: 3px;
  }

  /* Card */
  .tl-card {
    flex: 1;
    background: linear-gradient(135deg, #111827 0%, #1e293b 100%);
    border: 1px solid;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-left: 8px;
    margin-bottom: 2px;
    transition: transform 0.15s;
  }
  .tl-card:hover { transform: translateX(2px); }
  .tl-title {
    font-family: 'Oswald', sans-serif;
    font-size: 0.97rem;
    color: #f1f5f9;
    line-height: 1.3;
    margin: 0 0 0.35rem 0;
  }
  .tl-body {
    font-size: 0.80rem;
    color: #94a3b8;
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin: 0 0 0.5rem 0;
  }
  .tl-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }
  .tl-chip {
    display: inline-block;
    font-size: 0.68rem;
    padding: 1px 7px;
    border-radius: 5px;
    border-width: 1px;
    border-style: solid;
  }
  .tl-conf-pill {
    display: inline-block;
    font-family: 'Oswald', sans-serif;
    font-size: 0.65rem;
    letter-spacing: 0.06em;
    padding: 1px 8px;
    border-radius: 10px;
    border-width: 1px;
    border-style: solid;
  }
  .tl-source-link {
    font-size: 0.70rem;
    color: #60a5fa;
    text-decoration: none;
  }
  .tl-source-link:hover { text-decoration: underline; }

  /* Conf bar */
  .mini-bar-bg {
    background: #1e293b;
    border-radius: 3px;
    height: 4px;
    overflow: hidden;
    margin: 5px 0 4px;
    width: 100%;
  }
  .mini-bar-fill { height: 100%; border-radius: 3px; }

  /* Empty state */
  .empty-tl {
    text-align: center;
    padding: 4rem 2rem;
    color: #4b5563;
  }
  .empty-tl h3 { color: #6b7280; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: #0a0a0a;
    border-right: 1px solid #1e1e2e;
  }

  .stat-box {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 0.5rem 0.8rem;
    margin: 0.3rem 0;
    text-align: center;
  }
  .stat-box .val { font-family:'Oswald',sans-serif; font-size:1.3rem; color:#e2e8f0; }
  .stat-box .lbl { font-size: 0.70rem; color: #64748b; }
</style>
""", unsafe_allow_html=True)


# ── Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="tl-header">
  <h1>⏱️ Transfer Timeline</h1>
  <div class="sub">Chronological history · Grouped by date · Colour-coded by confidence</div>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎛️ Timeline Filters")

    league_filter = st.multiselect(
        "Leagues",
        ["All", "Premier League", "La Liga", "Serie A", "Bundesliga",
         "Ligue 1", "MLS", "Saudi Pro League"],
        default=["All"],
    )
    min_conf = st.slider(
        "Min. confidence", 1, 5, 1,
        help="1 = show all · 5 = confirmed only",
    )
    search_term = st.text_input(
        "Search player / club",
        placeholder="e.g. Mbappe, Arsenal",
    )
    max_days = st.slider("Days to show", 1, 30, 7)

    st.divider()
    stats = _processor.stats()
    st.markdown("### 📊 Knowledge Base")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div class="stat-box"><div class="val">{stats["total_articles"]}</div>'
            f'<div class="lbl">Articles</div></div>', unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="stat-box"><div class="val">{len(stats["sources_scraped"])}</div>'
            f'<div class="lbl">Sources</div></div>', unsafe_allow_html=True,
        )

    if st.button("← Back to Chat", use_container_width=True):
        st.switch_page("main.py")


# ── Fetch + filter articles ─────────────────────────────────────────────────
all_articles = _processor.get_recent_articles(limit=300, min_confidence=min_conf)

def article_league(article: dict) -> str:
    src = article.get("source", "")
    tags = article.get("league_tags", [])
    if tags and tags[0] != "All":
        return tags[0]
    return SOURCE_LEAGUE_MAP.get(src, "All")

def article_matches_league(article: dict, filters: list) -> bool:
    if "All" in filters:
        return True
    league = article_league(article)
    if league == "All":
        return True
    return league in filters

def article_matches_search(article: dict, term: str) -> bool:
    if not term.strip():
        return True
    haystack = (article.get("title", "") + " " + article.get("text", "")).lower()
    return term.lower() in haystack

import datetime as dt
cutoff_date = (dt.date.today() - dt.timedelta(days=max_days)).isoformat()

filtered = [
    a for a in all_articles
    if article_matches_league(a, league_filter)
    and article_matches_search(a, search_term)
    and a.get("date", "9999-12-31") >= cutoff_date
]

# Group by date descending
by_date: dict[str, list] = defaultdict(list)
for a in filtered:
    by_date[a.get("date", "Unknown")].append(a)

sorted_dates = sorted(by_date.keys(), reverse=True)


# ── Render ──────────────────────────────────────────────────────────────────
if not filtered:
    st.markdown("""
    <div class="empty-tl">
      <h3>📭 No articles in this range</h3>
      <p>Adjust the filters or scrape fresh articles from the
         <strong>News Feed</strong> page.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.caption(f"Showing **{len(filtered)}** articles across **{len(sorted_dates)}** days")

    for date_str in sorted_dates:
        articles = by_date[date_str]

        # Pretty-print date
        try:
            d = dt.date.fromisoformat(date_str)
            today = dt.date.today()
            if d == today:
                label = "Today"
            elif d == today - dt.timedelta(days=1):
                label = "Yesterday"
            else:
                label = d.strftime("%A, %d %b %Y")
        except ValueError:
            label = date_str

        count = len(articles)
        st.markdown(
            f'<div class="date-group">'
            f'  <div class="date-badge">📅 {label} &nbsp;·&nbsp; {count} article{"s" if count != 1 else ""}</div>'
            f'  <div class="date-line"></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for idx, article in enumerate(articles):
            conf      = article.get("confidence", 1)
            cp        = CONF_COLORS.get(conf, CONF_COLORS[1])
            conf_pct  = int((conf / 5) * 100)

            league    = article_league(article)
            lp        = LEAGUE_COLORS.get(league, LEAGUE_COLORS["All"])

            title     = article.get("title", "No title")
            body      = article.get("text", "")[:220]
            url       = article.get("url", "#")
            source    = article.get("source", "Unknown")

            is_last   = (idx == len(articles) - 1)
            spine_line = "" if is_last else '<div class="tl-line"></div>'

            st.markdown(
                f'<div class="tl-entry">'
                f'  <div class="tl-spine">'
                f'    <div class="tl-dot" style="border-color:{cp["border"]};'
                f'         background:{cp["bg"]};"></div>'
                f'    {spine_line}'
                f'  </div>'
                f'  <div class="tl-card" style="border-color:{cp["border"]}22;">'
                f'    <div class="tl-title">{title}</div>'
                f'    <div class="mini-bar-bg">'
                f'      <div class="mini-bar-fill"'
                f'           style="width:{conf_pct}%;background:{cp["border"]};"></div>'
                f'    </div>'
                f'    <div class="tl-body">{body}{"…" if len(article.get("text","")) > 220 else ""}</div>'
                f'    <div class="tl-meta">'
                f'      <span class="tl-conf-pill"'
                f'            style="background:{cp["bg"]};color:{cp["text"]};'
                f'                   border-color:{cp["border"]}66;">'
                f'        {cp["label"]}'
                f'      </span>'
                f'      <span class="tl-chip"'
                f'            style="background:{lp["bg"]};color:{lp["text"]};'
                f'                   border-color:{lp["border"]};">'
                f'        {league}'
                f'      </span>'
                f'      <a class="tl-source-link" href="{url}" target="_blank">📡 {source}</a>'
                f'    </div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )
