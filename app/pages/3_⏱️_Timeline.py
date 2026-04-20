"""
pages/3_⏱️_Timeline.py – Transfer Timeline
Gemini-powered extraction: sends KB articles to Gemini which identifies
ONLY actual transfer moves (not injuries, suspensions, financial news),
then displays them as player movement cards grouped by date.
"""

import sys
import re
import json
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

def article_league(article: dict) -> str:
    tags = article.get("league_tags", [])
    if tags and tags[0] != "All":
        return tags[0]
    return SOURCE_LEAGUE_MAP.get(article.get("source", ""), "All")


# ── Gemini-powered transfer extraction ───────────────────────────────────
_EXTRACTION_PROMPT = """You are a football transfer news parser. Your ONLY job is to identify actual player transfer moves.

Given the numbered list of article headlines + snippets below, extract ONLY entries that describe:
- A player joining or moving to a club (confirmed, agreed, close, targeted, linked, bid made)
- A player leaving or expected to leave a club

DO NOT include:
- Match reports or previews
- Player injuries or fitness news
- Suspensions or bans
- Financial/FFP news
- Manager appointments
- Contract extensions (unless a player is ALSO linked to another club)
- General club/league news with no specific transfer move

For each valid transfer move, output a JSON object with:
{
  "article_index": <number from the list>,
  "player": "<full player name>",
  "from_club": "<current/selling club, or null if unknown>",
  "to_club": "<destination club, or null if unknown>",
  "direction": "joining" or "leaving",
  "league": "<league of destination/current club, e.g. Premier League, or All if unclear>"
}

Return ONLY a JSON array. If no transfer moves found, return [].
No explanation text — just the JSON array."""


@st.cache_data(ttl=600, show_spinner=False)
def extract_transfers_with_gemini(articles_json: str) -> tuple[list[dict], str]:
    """
    Send article headlines to Gemini (gemini-1.5-flash, 1500 RPD free tier) for
    structured transfer extraction. Returns (results, mode) where mode is
    "gemini" on success or "quota_exceeded" / "error" on failure.
    Cached 10 minutes to minimise API calls.
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return [], "no_key"

    articles = json.loads(articles_json)
    if not articles:
        return [], "gemini"

    # Build numbered article list
    lines = []
    for a in articles:
        lines.append(
            f"{a['index']}. [{a['source']} | {a['date']} | conf:{a['confidence']}]\n"
            f"   Headline: {a['title']}\n"
            f"   Snippet:  {a['text'][:200]}"
        )
    articles_text = "\n\n".join(lines)

    # Try gemini-1.5-flash first (1500 RPD free tier), fall back to gemini-2.0-flash
    for model_name in ["gemini-1.5-flash", "gemini-2.0-flash"]:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.1,
            )
            response = llm.invoke([
                SystemMessage(content=_EXTRACTION_PROMPT),
                HumanMessage(content=f"Extract transfer moves from these {len(articles)} articles:\n\n{articles_text}"),
            ])
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            parsed = json.loads(raw)
            return (parsed if isinstance(parsed, list) else []), "gemini"

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                continue  # try next model
            # Non-quota error — bail out
            return [], f"error:{err_str[:120]}"

    # All models quota-exhausted
    return [], "quota_exceeded"


# ── Regex fallback parser (used when Gemini quota is exhausted) ───────────
_TRANSFER_VERBS = re.compile(
    r'\b(joins?|signs?|moves?\s+to|transfers?\s+to|heading\s+to|'
    r'completes?\s+move|agrees?\s+to\s+join|confirmed\s+at|'
    r'leaves?|departs?|exits?|set\s+to\s+leave|linked\s+to|'
    r'targets?|eyes?|wants?\s+to\s+sign|bids?\s+for|'
    r'nearing\s+(?:a\s+)?(?:move|deal|transfer))\b',
    re.IGNORECASE,
)

def _clean(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip().rstrip(".,!;:")

def _regex_parse(title: str, idx: int) -> dict | None:
    """Quick regex check — only pass articles that mention transfer verbs."""
    if not _TRANSFER_VERBS.search(title):
        return None
    # Pattern A: Player → Club
    m = re.match(
        r'([A-Z][a-záéíóú\'\-]+(?:\s+[A-Z][a-záéíóú\'\-]+){1,3})'
        r'\s+(?:to|joins?|signs?\s+for|moves?\s+to|heading\s+to|'
        r'completes?\s+move\s+to|agrees?\s+to\s+join|confirmed\s+at)\s+'
        r'([A-Z][A-Za-záéíóú\s\.\-\']+?)(?:\s*[,!;:\-]|\s+(?:on|for|in|at)\b|$)',
        title, re.IGNORECASE,
    )
    if m:
        return {"article_index": idx, "player": _clean(m.group(1)),
                "to_club": _clean(m.group(2)), "from_club": None,
                "direction": "joining", "league": "All"}
    # Pattern B: Club signs Player
    m = re.match(
        r'([A-Z][A-Za-záéíóú\s\.\-\']{3,35}?)\s+'
        r'(?:sign|signs|complete|completes|confirm|confirms|land|lands|secure|secures)\s+'
        r'([A-Z][a-záéíóú\'\-]+(?:\s+[A-Z][a-záéíóú\'\-]+){1,3})',
        title,
    )
    if m:
        return {"article_index": idx, "player": _clean(m.group(2)),
                "to_club": _clean(m.group(1)), "from_club": None,
                "direction": "joining", "league": "All"}
    # Pattern C: Player leaves Club
    m = re.match(
        r'([A-Z][a-záéíóú\'\-]+(?:\s+[A-Z][a-záéíóú\'\-]+){1,3})'
        r'\s+(?:leaves?|departs?|exits?|set\s+to\s+leave|will\s+leave)'
        r'(?:\s+([A-Z][A-Za-záéíóú\s\.\-\']+?)(?:\s*[,;:\-]|$))?',
        title, re.IGNORECASE,
    )
    if m:
        return {"article_index": idx, "player": _clean(m.group(1)),
                "from_club": _clean(m.group(2)) if m.group(2) else None,
                "to_club": None, "direction": "leaving", "league": "All"}
    return None


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

  .ptcard {
    flex: 1; margin-left: 10px;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border: 1px solid;
    border-radius: 10px;
    padding: 0.85rem 1.1rem;
    transition: transform 0.15s;
  }
  .ptcard:hover { transform: translateX(3px); }

  .ptcard-name {
    font-family: 'Oswald', sans-serif;
    font-size: 1.15rem; font-weight: 600;
    color: #f1f5f9; margin: 0 0 0.45rem 0;
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  }

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
  .club-arrow { font-size: 1rem; color: #f59e0b; font-weight: 700; }

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

  .mini-bar-bg {
    background: #0f172a; border-radius: 3px;
    height: 4px; overflow: hidden; margin: 6px 0 5px;
  }
  .mini-bar-fill { height: 100%; border-radius: 3px; }

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
  .src-link { font-size: 0.70rem; color: #60a5fa; text-decoration: none; }
  .src-link:hover { text-decoration: underline; }

  .ptcard-headline {
    font-size: 0.8rem; color: #64748b;
    margin: 0 0 0.4rem 0; font-style: italic;
    line-height: 1.4;
  }

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
  <div class="sub">AI-powered · Strictly transfer moves · Grouped by date</div>
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

    st.divider()

    st.markdown("### 🤖 AI Extraction")
    if st.button("🔍 Extract Transfers (AI)", use_container_width=True, type="primary",
                 help="Ask Gemini to identify transfer moves in the KB articles. Uses gemini-1.5-flash (1500/day free)."):
        st.session_state["tl_run_gemini"] = True
        st.cache_data.clear()
        st.rerun()
    if st.button("🔄 Re-extract (force refresh)", use_container_width=True,
                 help="Clear cache and re-run Gemini extraction"):
        st.session_state["tl_run_gemini"] = True
        st.cache_data.clear()
        st.rerun()
    st.caption("Uses gemini-1.5-flash · 1,500 free calls/day")

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


# ── Language & sport display filters ──────────────────────────────────────
_NON_ENG = frozenset({
    "les","des","une","dans","avec","pour","mais","très","selon","depuis",
    "lors","cette","aussi","même","tout","après","avant","dont","jamais",
    "encore","toujours","peut","être","quand","sous","vers",
    "los","las","para","también","pero","están","cuando","donde","aunque",
    "desde","hasta","nunca","siempre","después","sobre","siendo","según",
    "und","nicht","sich","aber","wird","kann","oder","wenn","nach","über",
    "beim","durch","gegen","ohne","unter","zwischen","dann","schon","dass",
    "della","dello","degli","delle","nella","sono","hanno","anche","molto",
    "tutto","dopo","prima","perché","però","ogni","questi","queste",
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


# ── Fetch KB articles ──────────────────────────────────────────────────────
cutoff = (dt.date.today() - dt.timedelta(days=max_days)).isoformat()
kb_articles_raw = [
    a for a in _processor.get_recent_articles(limit=500, min_confidence=min_conf)
    if a.get("date", "9999-12-31") >= cutoff
    and _is_english(a.get("title", ""), a.get("text", ""))
    and _is_football(a.get("title", ""), a.get("text", ""))
]

# Build index map: index → article
indexed = {i: a for i, a in enumerate(kb_articles_raw)}

# ── Call Gemini for extraction (cached) ───────────────────────────────────
kb_count = stats.get("total_articles", 0)

if kb_count == 0:
    st.warning(
        "📭 Knowledge base is empty. Scrape articles first via **📰 News Feed → Scrape Now**.",
        icon="📭",
    )
    st.stop()

if not kb_articles_raw:
    st.info(
        f"No articles found in the last **{max_days} days** meeting the confidence filter. "
        "Try increasing the date range or lowering the confidence slider.",
        icon="ℹ️",
    )
    st.stop()

# Prepare JSON payload for caching key
articles_payload = json.dumps([
    {
        "index": i,
        "title": a.get("title", ""),
        "text":  a.get("text", "")[:300],
        "url":   a.get("url", "#"),
        "source": a.get("source", "Unknown"),
        "date":  a.get("date", ""),
        "confidence": a.get("confidence", 1),
    }
    for i, a in indexed.items()
])

# ── Extraction: Gemini (on demand) or regex fallback ──────────────────────
extraction_mode = "none"

run_gemini = st.session_state.get("tl_run_gemini", False)

if run_gemini:
    with st.spinner(f"🤖 Gemini (gemini-1.5-flash) extracting from {len(kb_articles_raw)} articles…"):
        extracted, extraction_mode = extract_transfers_with_gemini(articles_payload)

    if extraction_mode == "quota_exceeded":
        st.warning(
            "⚠️ **Gemini quota reached** for today (free tier: 1,500/day on gemini-1.5-flash). "
            "Showing **regex-based** results instead — less accurate but still useful. "
            "Quota resets at midnight PT.",
            icon="⚠️",
        )
        extraction_mode = "regex"
    elif extraction_mode.startswith("error:"):
        st.warning(f"⚠️ Gemini error: `{extraction_mode[6:]}` — falling back to regex.", icon="⚠️")
        extraction_mode = "regex"
    elif extraction_mode == "no_key":
        st.error("🔑 No GEMINI_API_KEY found in .env — using regex fallback.", icon="🔑")
        extraction_mode = "regex"
    else:
        st.session_state["tl_run_gemini"] = False  # reset so next load doesn't auto-re-run

    if extraction_mode == "regex":
        extracted = [
            r for r in (
                _regex_parse(indexed[i].get("title", ""), i)
                for i in indexed
            ) if r is not None
        ]
else:
    # Not yet run — show prompt to use the button
    extracted = []
    extraction_mode = "none"

if extraction_mode == "none" and not run_gemini:
    st.info(
        "👆 Click **Extract Transfers (AI)** in the sidebar to identify transfer moves "
        "using Gemini. Results are cached for 10 minutes.",
        icon="🤖",
    )
elif extraction_mode == "regex":
    st.caption("📐 Showing regex-extracted results (Gemini quota exceeded)")


# ── Build enriched move list ───────────────────────────────────────────────
# Merge Gemini extraction results back with full article data
moves = []
for entry in extracted:
    idx = entry.get("article_index")
    if idx is None or idx not in indexed:
        continue
    a = indexed[idx]

    direction = entry.get("direction", "joining")
    player    = (entry.get("player") or "").strip()
    to_club   = (entry.get("to_club") or "").strip() or None
    from_club = (entry.get("from_club") or "").strip() or None

    # Use Gemini's league if meaningful, else fall back to source map
    gemini_league = (entry.get("league") or "").strip()
    league = gemini_league if gemini_league and gemini_league != "All" else article_league(a)

    if not player:
        continue

    # League filter
    if "All" not in league_filter:
        if league not in league_filter and league != "All":
            continue

    # Direction filter
    if direction_filter == "Joining ✈️" and direction != "joining":
        continue
    if direction_filter == "Leaving 🚪" and direction != "leaving":
        continue

    # Search filter
    if search_term.strip():
        haystack = (player + " " + (to_club or "") + " " + (from_club or "") + " " + a.get("title", "")).lower()
        if search_term.lower() not in haystack:
            continue

    moves.append({
        "player":    player,
        "to_club":   to_club,
        "from_club": from_club,
        "direction": direction,
        "league":    league,
        "article":   a,
    })

# Group by date
by_date: dict[str, list] = defaultdict(list)
for m in moves:
    by_date[m["article"].get("date", "Unknown")].append(m)
sorted_dates = sorted(by_date.keys(), reverse=True)


# ── Summary metrics ────────────────────────────────────────────────────────
if moves:
    joining_n = sum(1 for m in moves if m["direction"] == "joining")
    leaving_n = sum(1 for m in moves if m["direction"] == "leaving")
    players_n = len({m["player"] for m in moves})

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Transfer moves", len(moves))
    c2.metric("Players tracked", players_n)
    c3.metric("Joining ✈️", joining_n)
    c4.metric("Leaving 🚪", leaving_n)
    st.divider()


# ── Render ──────────────────────────────────────────────────────────────────
if not moves:
    st.markdown("""
    <div class="empty-tl">
      <h3>📭 No transfer moves found</h3>
      <p>Gemini found no actual transfer moves in the current KB articles.<br>
         Try <strong>scraping fresh data</strong> from the 📰 News Feed page,<br>
         expanding the date range, or lowering the confidence filter.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for date_str in sorted_dates:
        day_moves = by_date[date_str]

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

        n = len(day_moves)
        st.markdown(
            f'<div class="date-group">'
            f'  <div class="date-badge">📅 {label} &nbsp;·&nbsp; '
            f'    {n} move{"s" if n != 1 else ""}'
            f'  </div>'
            f'  <div class="date-line"></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for idx, m in enumerate(day_moves):
            a         = m["article"]
            conf      = a.get("confidence", 1)
            cp        = CONF_COLORS.get(conf, CONF_COLORS[1])
            conf_pct  = int((conf / 5) * 100)
            lp        = LEAGUE_COLORS.get(m["league"], LEAGUE_COLORS["All"])
            is_last   = (idx == len(day_moves) - 1)
            vline     = "" if is_last else '<div class="tl-vline"></div>'
            url       = a.get("url", "#")
            source    = a.get("source", "Unknown")
            title     = a.get("title", "No title")

            player    = m["player"]
            to_club   = m["to_club"]
            from_club = m["from_club"]
            direction = m["direction"]
            league    = m["league"]

            if direction == "joining":
                dir_badge = '<span class="dir-badge-join">✈️ JOINING</span>'
                if from_club and to_club:
                    clubs_html = (
                        f'<span class="club-pill">🏟️ {from_club}</span>'
                        f'<span class="club-arrow">→</span>'
                        f'<span class="club-pill" style="border-color:{cp["border"]}55;'
                        f'color:{cp["text"]};">🎯 {to_club}</span>'
                    )
                elif to_club:
                    clubs_html = (
                        f'<span class="club-pill" style="border-color:{cp["border"]}55;'
                        f'color:{cp["text"]};">🎯 {to_club}</span>'
                    )
                else:
                    clubs_html = ""
            else:
                dir_badge = '<span class="dir-badge-leave">🚪 LEAVING</span>'
                if from_club and to_club:
                    clubs_html = (
                        f'<span class="club-pill" style="border-color:#ef444455;color:#fca5a5;">🏟️ {from_club}</span>'
                        f'<span class="club-arrow" style="color:#ef4444;">→</span>'
                        f'<span class="club-pill" style="border-color:{cp["border"]}55;color:{cp["text"]};">🎯 {to_club}</span>'
                    )
                elif from_club:
                    clubs_html = (
                        f'<span class="club-pill" style="border-color:#ef444455;color:#fca5a5;">🏟️ {from_club}</span>'
                        f'<span class="club-arrow" style="color:#ef4444;">→</span>'
                        f'<span class="club-pill">❓ TBD</span>'
                    )
                else:
                    clubs_html = ""

            clubs_section = f'<div class="clubs-row">{clubs_html}</div>' if clubs_html else ""

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
                f'    <div class="ptcard-headline">"{title}"</div>'
                f'    <div class="mini-bar-bg">'
                f'      <div class="mini-bar-fill" style="width:{conf_pct}%;background:{cp["border"]};"></div>'
                f'    </div>'
                f'    <div class="ptcard-meta">'
                f'      <span class="conf-pill" style="background:{cp["bg"]};color:{cp["text"]};'
                f'             border-color:{cp["border"]}66;">{cp["label"]}</span>'
                f'      <span class="meta-chip" style="background:{lp["bg"]};color:{lp["text"]};'
                f'             border-color:{lp["border"]};">{league}</span>'
                f'      <a class="src-link" href="{url}" target="_blank">📡 {source}</a>'
                f'    </div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )
