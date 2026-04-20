"""
pages/3_⏱️_Timeline.py – Transfer Timeline
Player-focused chronological feed: extracts player name and clubs from
article titles, groups by date, shows joining/leaving direction with
visual from→to cards.
"""

import sys
import re
import datetime as dt
from pathlib import Path
from collections import defaultdict

import streamlit as st

# ── Path setup ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

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
    "Fabrizio Romano (Twitter/X)":       "All",
    "Fabrizio Romano (Caught Offside)":  "All",
    "ESPN Soccer":                       "All",
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


# ── Player + club extraction ──────────────────────────────────────────────

def _clean(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip().rstrip(".,!;:")


def parse_transfer(title: str, text: str = "") -> dict:
    """
    Try to extract: player, to_club, from_club, direction ('joining'/'leaving').
    Returns a dict; player=None means no individual player was identified.
    """
    result = {"player": None, "to_club": None, "from_club": None, "direction": None}
    t = title  # original case

    # ── Pattern A: "HERE WE GO! Player to Club" ───────────────────────────
    m = re.match(
        r'(?:here\s+we\s+go[!.]?\s+)?'
        r'([A-Z][a-záéíóúàèùâêîôûäëïöü\'\-]+(?:\s+(?:de\s+|van\s+|van\s+der\s+|el\s+|al\s+)?'
        r'[A-Z][a-záéíóúàèùâêîôûäëïöü\'\-]+){1,3})'
        r'\s+(?:to|joins?|signs?\s+for|signs?|moves?\s+to|heading\s+to|'
        r'set\s+to\s+join|close\s+to\s+joining|nearing\s+move\s+to|'
        r'completes?\s+move\s+to|agrees?\s+to\s+join|confirmed\s+at)\s+'
        r'([A-Z][A-Za-záéíóú\s\.\-\']+?)(?:\s*[,!;:\-]|\s+(?:on|for|in|at|with|after|as|from)\b|$)',
        t, re.IGNORECASE,
    )
    if m:
        result["player"]    = _clean(m.group(1))
        result["to_club"]   = _clean(m.group(2))
        result["direction"] = "joining"
        return result

    # ── Pattern B: "Club sign(s)/agree/complete Player" ──────────────────
    m = re.match(
        r'([A-Z][A-Za-záéíóú\s\.\-\']{3,40}?)\s+'
        r'(?:sign|signs|agree|agrees|complete|completes|confirm|confirms|land|lands|'
        r'secure|secures|announce|announces)\s+'
        r'(?:deal\s+for\s+|signing\s+of\s+|transfer\s+of\s+)?'
        r'([A-Z][a-záéíóú\'\-]+(?:\s+[A-Z][a-záéíóú\'\-]+){1,3})',
        t,
    )
    if m:
        result["to_club"]   = _clean(m.group(1))
        result["player"]    = _clean(m.group(2))
        result["direction"] = "joining"
        return result

    # ── Pattern C: "Player set to leave / leaves / exits Club" ───────────
    m = re.match(
        r'([A-Z][a-záéíóú\'\-]+(?:\s+[A-Z][a-záéíóú\'\-]+){1,3})'
        r'\s+(?:leaves?|exits?|departs?|set\s+to\s+leave|expected\s+to\s+leave|'
        r'wants?\s+to\s+leave|could\s+leave|looking\s+to\s+leave|'
        r'will\s+leave|officially\s+leaves?)'
        r'(?:\s+([A-Z][A-Za-záéíóú\s\.\-\']+?)(?:\s*[,;:\-]|$))?',
        t, re.IGNORECASE,
    )
    if m:
        result["player"]    = _clean(m.group(1))
        result["from_club"] = _clean(m.group(2)) if m.group(2) else None
        result["direction"] = "leaving"
        return result

    # ── Pattern D: "Club target/eye/want Player" ─────────────────────────
    m = re.match(
        r'([A-Z][A-Za-záéíóú\s\.\-\']{3,40}?)\s+'
        r'(?:target|targets|eye|eyes|want|wants|pursuing|consider|considers|'
        r'monitor|monitors|interested\s+in|bid\s+for|make\s+move\s+for)\s+'
        r'([A-Z][a-záéíóú\'\-]+(?:\s+[A-Z][a-záéíóú\'\-]+){1,3})',
        t,
    )
    if m:
        result["to_club"]   = _clean(m.group(1))
        result["player"]    = _clean(m.group(2))
        result["direction"] = "joining"
        return result

    # ── Pattern E: "Player from Club to Club" ────────────────────────────
    m = re.match(
        r'([A-Z][a-záéíóú\'\-]+(?:\s+[A-Z][a-záéíóú\'\-]+){1,3})'
        r'\s+from\s+([A-Z][A-Za-záéíóú\s\.\-\']+?)'
        r'\s+to\s+([A-Z][A-Za-záéíóú\s\.\-\']+?)(?:\s*[,;:\-]|$)',
        t, re.IGNORECASE,
    )
    if m:
        result["player"]    = _clean(m.group(1))
        result["from_club"] = _clean(m.group(2))
        result["to_club"]   = _clean(m.group(3))
        result["direction"] = "joining"
        return result

    return result


def article_league(article: dict) -> str:
    tags = article.get("league_tags", [])
    if tags and tags[0] != "All":
        return tags[0]
    return SOURCE_LEAGUE_MAP.get(article.get("source", ""), "All")


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
  .tl-header h1   { color: #fff; font-size: 2rem; margin: 0; }
  .tl-header .sub { color: #f59e0b; font-size: 0.82rem; letter-spacing: 0.15em; text-transform: uppercase; }

  /* Date separator */
  .date-group {
    display: flex; align-items: center; gap: 1rem;
    margin: 2.2rem 0 1rem 0;
  }
  .date-badge {
    font-family: 'Oswald', sans-serif;
    font-size: 1rem; color: #f59e0b;
    background: #1c1500; border: 1px solid #78350f;
    border-radius: 8px; padding: 4px 14px;
    white-space: nowrap; flex-shrink: 0;
  }
  .date-line {
    flex: 1; height: 1px;
    background: linear-gradient(to right, #78350f55, transparent);
  }

  /* Timeline row */
  .tl-row {
    display: flex; gap: 0;
    margin: 0 0 0.6rem 1.4rem;
  }
  .tl-spine {
    display: flex; flex-direction: column;
    align-items: center; width: 26px; flex-shrink: 0;
  }
  .tl-dot {
    width: 12px; height: 12px;
    border-radius: 50%; border: 2px solid;
    flex-shrink: 0; margin-top: 6px;
  }
  .tl-vline {
    width: 2px; flex: 1; min-height: 18px;
    background: #1e293b; margin-top: 3px;
  }

  /* ── PLAYER TRANSFER CARD ── */
  .ptcard {
    flex: 1; margin-left: 10px;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border: 1px solid;
    border-radius: 10px;
    padding: 0.85rem 1.1rem;
    transition: transform 0.15s;
  }
  .ptcard:hover { transform: translateX(3px); }

  /* Player name row */
  .ptcard-name {
    font-family: 'Oswald', sans-serif;
    font-size: 1.15rem; font-weight: 600;
    color: #f1f5f9; margin: 0 0 0.45rem 0;
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  }

  /* From → To clubs row */
  .clubs-row {
    display: flex; align-items: center; gap: 8px;
    margin: 0 0 0.5rem 0; flex-wrap: wrap;
  }
  .club-pill {
    display: inline-block;
    font-size: 0.82rem; font-weight: 500;
    padding: 3px 11px; border-radius: 6px;
    border: 1px solid #334155;
    color: #cbd5e1; background: #1e293b;
  }
  .club-arrow {
    font-size: 1rem; color: #f59e0b; font-weight: 700;
  }
  .dir-badge-join {
    display: inline-block;
    font-family: 'Oswald', sans-serif;
    font-size: 0.65rem; letter-spacing: 0.08em;
    padding: 2px 8px; border-radius: 10px;
    background: #052e0f; color: #86efac;
    border: 1px solid #22c55e55;
  }
  .dir-badge-leave {
    display: inline-block;
    font-family: 'Oswald', sans-serif;
    font-size: 0.65rem; letter-spacing: 0.08em;
    padding: 2px 8px; border-radius: 10px;
    background: #2d0a0a; color: #fca5a5;
    border: 1px solid #ef444455;
  }

  /* Confidence bar */
  .mini-bar-bg {
    background: #0f172a; border-radius: 3px;
    height: 4px; overflow: hidden; margin: 6px 0 5px;
  }
  .mini-bar-fill { height: 100%; border-radius: 3px; }

  /* Meta row */
  .ptcard-meta {
    display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
    margin-top: 4px;
  }
  .meta-chip {
    display: inline-block; font-size: 0.68rem;
    padding: 1px 7px; border-radius: 5px;
    border: 1px solid;
  }
  .conf-pill {
    display: inline-block;
    font-family: 'Oswald', sans-serif; font-size: 0.65rem;
    letter-spacing: 0.06em; padding: 1px 8px;
    border-radius: 10px; border: 1px solid;
  }
  .src-link {
    font-size: 0.70rem; color: #60a5fa; text-decoration: none;
  }
  .src-link:hover { text-decoration: underline; }

  /* Generic news card (no player parsed) */
  .news-card {
    flex: 1; margin-left: 10px;
    background: #111827;
    border: 1px solid #1e2a3a;
    border-radius: 8px;
    padding: 0.65rem 1rem;
    transition: transform 0.15s;
    opacity: 0.72;
  }
  .news-card:hover { transform: translateX(2px); opacity: 1; }
  .news-title {
    font-size: 0.88rem; color: #94a3b8; line-height: 1.4;
    margin: 0 0 4px 0;
  }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: #0a0a0a; border-right: 1px solid #1e1e2e;
  }
  .stat-box {
    background: #111827; border: 1px solid #1e3a5f;
    border-radius: 8px; padding: 0.5rem 0.8rem;
    margin: 0.3rem 0; text-align: center;
  }
  .stat-box .val { font-family:'Oswald',sans-serif; font-size:1.3rem; color:#e2e8f0; }
  .stat-box .lbl { font-size:0.70rem; color:#64748b; }

  .empty-tl { text-align:center; padding:4rem 2rem; color:#4b5563; }
  .empty-tl h3 { color:#6b7280; }
</style>
""", unsafe_allow_html=True)


# ── Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="tl-header">
  <h1>⏱️ Transfer Timeline</h1>
  <div class="sub">Player movements · Joining &amp; leaving · Grouped by date</div>
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
    min_conf = st.slider("Min. confidence", 1, 5, 1,
                         help="1 = all · 5 = confirmed only")
    direction_filter = st.radio(
        "Direction",
        ["All moves", "Joining ✈️", "Leaving 🚪"],
        horizontal=True,
    )
    search_term = st.text_input(
        "Search player / club",
        placeholder="e.g. Bellingham, Arsenal",
    )
    max_days = st.slider("Days to show", 1, 30, 7)
    show_news = st.toggle(
        "Show general news (no player)", value=False,
        help="Show articles where no specific player was identified",
    )

    st.divider()
    stats = _processor.stats()
    st.markdown("### 📊 Knowledge Base")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div class="stat-box"><div class="val">{stats["total_articles"]}</div>'
            f'<div class="lbl">Articles</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<div class="stat-box"><div class="val">{len(stats["sources_scraped"])}</div>'
            f'<div class="lbl">Sources</div></div>', unsafe_allow_html=True)

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

# ── Fetch + parse articles ──────────────────────────────────────────────────
all_articles = _processor.get_recent_articles(limit=500, min_confidence=min_conf)
cutoff = (dt.date.today() - dt.timedelta(days=max_days)).isoformat()

enriched = []
for a in all_articles:
    if a.get("date", "9999-12-31") < cutoff:
        continue

    # Language + sport filter
    if not _is_english(a.get("title", ""), a.get("text", "")):
        continue
    if not _is_football(a.get("title", ""), a.get("text", "")):
        continue

    # League filter
    league = article_league(a)
    if "All" not in league_filter:
        if league not in league_filter and league != "All":
            continue

    # Parse player info
    info = parse_transfer(a.get("title", ""), a.get("text", ""))
    a["_player"]    = info["player"]
    a["_to_club"]   = info["to_club"]
    a["_from_club"] = info["from_club"]
    a["_direction"] = info["direction"]
    a["_league"]    = league
    a["_has_player"] = info["player"] is not None

    # Direction filter
    if direction_filter == "Joining ✈️" and info["direction"] not in (None, "joining"):
        continue
    if direction_filter == "Leaving 🚪" and info["direction"] != "leaving":
        continue

    # Search filter
    if search_term.strip():
        haystack = (
            (info["player"] or "") + " " +
            (info["to_club"] or "") + " " +
            (info["from_club"] or "") + " " +
            a.get("title", "")
        ).lower()
        if search_term.lower() not in haystack:
            continue

    # Skip general news unless toggled
    if not info["player"] and not show_news:
        continue

    enriched.append(a)

# Group by date descending
by_date: dict[str, list] = defaultdict(list)
for a in enriched:
    by_date[a.get("date", "Unknown")].append(a)
sorted_dates = sorted(by_date.keys(), reverse=True)


# ── Summary counts ─────────────────────────────────────────────────────────
player_articles = [a for a in enriched if a["_has_player"]]
joining = sum(1 for a in player_articles if a["_direction"] == "joining")
leaving = sum(1 for a in player_articles if a["_direction"] == "leaving")

if enriched:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total entries", len(enriched))
    c2.metric("Players tracked", len({a["_player"] for a in player_articles if a["_player"]}))
    c3.metric("Joining ✈️", joining)
    c4.metric("Leaving 🚪", leaving)
    st.divider()


# ── Render ──────────────────────────────────────────────────────────────────
if not enriched:
    st.markdown("""
    <div class="empty-tl">
      <h3>📭 No transfer movements found</h3>
      <p>Try adjusting the filters, expanding the date range,<br>
         or scraping fresh articles from the <strong>📰 News Feed</strong> page.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for date_str in sorted_dates:
        articles = by_date[date_str]

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

        n = len(articles)
        st.markdown(
            f'<div class="date-group">'
            f'  <div class="date-badge">📅 {label} &nbsp;·&nbsp; '
            f'    {n} move{"s" if n != 1 else ""}'
            f'  </div>'
            f'  <div class="date-line"></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for idx, a in enumerate(articles):
            conf      = a.get("confidence", 1)
            cp        = CONF_COLORS.get(conf, CONF_COLORS[1])
            conf_pct  = int((conf / 5) * 100)
            lp        = LEAGUE_COLORS.get(a["_league"], LEAGUE_COLORS["All"])
            is_last   = (idx == len(articles) - 1)
            vline     = "" if is_last else '<div class="tl-vline"></div>'
            url       = a.get("url", "#")
            source    = a.get("source", "Unknown")
            title     = a.get("title", "No title")

            if a["_has_player"]:
                # ── Player transfer card ─────────────────────────────────
                player    = a["_player"]
                to_club   = a["_to_club"]
                from_club = a["_from_club"]
                direction = a["_direction"]

                # Clubs row HTML
                if direction == "joining":
                    dir_badge = '<span class="dir-badge-join">✈️ JOINING</span>'
                    if from_club and to_club:
                        clubs_html = (
                            f'<span class="club-pill">🏟️ {from_club}</span>'
                            f'<span class="club-arrow">→</span>'
                            f'<span class="club-pill" style="border-color:{cp["border"]}55;'
                            f'color:{cp["text"]};">'
                            f'🎯 {to_club}</span>'
                        )
                    elif to_club:
                        clubs_html = (
                            f'<span class="club-pill" style="border-color:{cp["border"]}55;'
                            f'color:{cp["text"]};">'
                            f'🎯 {to_club}</span>'
                        )
                    else:
                        clubs_html = ""
                else:
                    dir_badge = '<span class="dir-badge-leave">🚪 LEAVING</span>'
                    if from_club:
                        clubs_html = (
                            f'<span class="club-pill" style="border-color:#ef444455;'
                            f'color:#fca5a5;">🏟️ {from_club}</span>'
                            f'<span class="club-arrow" style="color:#ef4444;">→</span>'
                            f'<span class="club-pill">❓ Destination TBD</span>'
                        )
                    else:
                        clubs_html = ""

                clubs_section = (
                    f'<div class="clubs-row">{clubs_html}</div>'
                    if clubs_html else ""
                )
                st.markdown(
                    f'<div class="tl-row">'
                    f'  <div class="tl-spine">'
                    f'    <div class="tl-dot" style="border-color:{cp["border"]};background:{cp["bg"]};"></div>'
                    f'    {vline}'
                    f'  </div>'
                    f'  <div class="ptcard" style="border-color:{cp["border"]}44;">'
                    f'    <div class="ptcard-name">'
                    f'      👤 {player}'
                    f'      {dir_badge}'
                    f'    </div>'
                    f'    {clubs_section}'
                    f'    <div class="mini-bar-bg">'
                    f'      <div class="mini-bar-fill" style="width:{conf_pct}%;background:{cp["border"]};"></div>'
                    f'    </div>'
                    f'    <div class="ptcard-meta">'
                    f'      <span class="conf-pill" style="background:{cp["bg"]};color:{cp["text"]};'
                    f'             border-color:{cp["border"]}66;">{cp["label"]}</span>'
                    f'      <span class="meta-chip" style="background:{lp["bg"]};color:{lp["text"]};'
                    f'             border-color:{lp["border"]};">{a["_league"]}</span>'
                    f'      <a class="src-link" href="{url}" target="_blank">📡 {source}</a>'
                    f'    </div>'
                    f'  </div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                # ── Generic news card ────────────────────────────────────
                st.markdown(
                    f'<div class="tl-row">'
                    f'  <div class="tl-spine">'
                    f'    <div class="tl-dot" style="border-color:#334155;background:#1e293b;"></div>'
                    f'    {vline}'
                    f'  </div>'
                    f'  <div class="news-card">'
                    f'    <div class="news-title">📰 {title}</div>'
                    f'    <div class="ptcard-meta">'
                    f'      <span class="conf-pill" style="background:{cp["bg"]};color:{cp["text"]};'
                    f'             border-color:{cp["border"]}66;">{cp["label"]}</span>'
                    f'      <a class="src-link" href="{url}" target="_blank">📡 {source}</a>'
                    f'    </div>'
                    f'  </div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
