"""
main.py – FabrizioAI Streamlit UI (v2)
Complete overhaul with:
  • st.chat_message bubbles with timestamps
  • Confidence progress bars on every response
  • Structured per-transfer cards parsed from agent markdown
  • League-coloured source chips
  • st.status live loading panel
  • Session stats in sidebar
  • Watchlist (players / clubs to track)
  • Auto-refresh toggle with countdown
  • Export chat to .txt
  • "Here We Go!" confetti burst on confidence 5
  • Beautiful empty-state welcome screen
"""

import time
import sys
import re
from pathlib import Path
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

# ── Path setup ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from utils import FabrizioAI, CONFIDENCE_LABELS

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FabrizioAI – Transfer Intelligence",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── League palette ────────────────────────────────────────────────────────
LEAGUE_COLORS = {
    "Premier League":  {"bg": "#3d195b", "text": "#c8a2e8", "border": "#6a2e9e"},
    "La Liga":         {"bg": "#9b1c1c", "text": "#fca5a5", "border": "#dc2626"},
    "Serie A":         {"bg": "#1e3a5f", "text": "#93c5fd", "border": "#2563eb"},
    "Bundesliga":      {"bg": "#1a1a00", "text": "#fde047", "border": "#ca8a04"},
    "Ligue 1":         {"bg": "#003153", "text": "#7dd3fc", "border": "#0369a1"},
    "All":             {"bg": "#1e2a1e", "text": "#86efac", "border": "#16a34a"},
}

SOURCE_LEAGUE_MAP = {
    "BBC Sport Transfers":  "All",
    "Goal.com Transfers":   "All",
    "Sky Sports Transfers": "Premier League",
    "Transfermarkt News":   "All",
    "Calciomercato":        "Serie A",
    "Marca Transfers":      "La Liga",
    "L'Equipe Football":    "Ligue 1",
    "Kicker Transfers":     "Bundesliga",
}

# ── Global CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  h1, h2, h3, h4 { font-family: 'Oswald', sans-serif; letter-spacing: 0.03em; }

  /* Dark base */
  .stApp { background: #0d0d0d; color: #f0f0f0; }

  /* Header banner */
  .fab-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-bottom: 3px solid #e94560;
    padding: 1.4rem 2rem;
    margin-bottom: 1.2rem;
    border-radius: 10px;
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  .fab-header h1  { color: #ffffff; font-size: 2.2rem; margin: 0; }
  .fab-header .subtitle {
    color: #e94560; font-size: 0.85rem;
    letter-spacing: 0.15em; text-transform: uppercase;
  }
  .fab-header .live-dot {
    display: inline-block; width: 9px; height: 9px;
    background: #22c55e; border-radius: 50%;
    box-shadow: 0 0 8px #22c55e;
    animation: pulse 1.8s ease-in-out infinite;
    margin-right: 5px; vertical-align: middle;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.5; transform: scale(1.3); }
  }

  /* Transfer card */
  .transfer-card {
    background: linear-gradient(135deg, #111827 0%, #1e293b 100%);
    border: 1px solid #1e3a5f;
    border-left: 4px solid #e94560;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.6rem 0;
    transition: border-color 0.2s;
  }
  .transfer-card:hover { border-left-color: #f59e0b; }
  .transfer-card h4 { color: #f1f5f9; margin: 0 0 0.4rem 0; font-size: 1.05rem; }
  .transfer-card p  { color: #cbd5e1; font-size: 0.88rem; line-height: 1.6; margin: 0.3rem 0 0; }

  /* Confidence bar label */
  .conf-label {
    font-family: 'Oswald', sans-serif;
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    color: #94a3b8;
    margin-bottom: 2px;
  }

  /* Source chip */
  .source-chip {
    display: inline-block;
    font-size: 0.72rem;
    padding: 2px 9px;
    border-radius: 6px;
    margin: 2px 3px 2px 0;
    border-width: 1px;
    border-style: solid;
    white-space: nowrap;
  }

  /* Confidence badge */
  .conf-badge {
    display: inline-block;
    font-family: 'Oswald', sans-serif;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    padding: 2px 10px;
    border-radius: 12px;
    margin-left: 8px;
  }

  /* Timestamp */
  .msg-ts {
    font-size: 0.68rem;
    color: #475569;
    margin-top: 4px;
    text-align: right;
  }

  /* Empty state */
  .empty-state {
    text-align: center;
    padding: 3rem 2rem;
    color: #64748b;
  }
  .empty-state h2 { color: #94a3b8; font-size: 1.8rem; }
  .empty-state p  { font-size: 0.95rem; max-width: 480px; margin: 0.5rem auto; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: #0a0a0a;
    border-right: 1px solid #1e1e2e;
  }

  /* Stats badge row */
  .stat-item {
    background: #1e1e2e;
    border-radius: 8px;
    padding: 0.5rem 0.8rem;
    margin: 0.3rem 0;
    font-size: 0.82rem;
    color: #94a3b8;
  }
  .stat-item strong { color: #e2e8f0; }

  /* Watchlist item */
  .watchlist-item {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    padding: 0.4rem 0.7rem;
    margin: 0.25rem 0;
    font-size: 0.82rem;
    color: #93c5fd;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  /* Quick prompt buttons */
  button[kind="secondary"] {
    background: #111827 !important;
    border: 1px solid #1e3a5f !important;
    color: #93c5fd !important;
    border-radius: 6px !important;
    font-size: 0.83rem !important;
  }
  button[kind="secondary"]:hover {
    border-color: #e94560 !important;
    color: #f1f5f9 !important;
  }

  /* Stale notice */
  .stale-notice {
    background: #1c1400;
    border: 1px solid #78350f;
    border-radius: 6px;
    padding: 0.4rem 0.8rem;
    font-size: 0.78rem;
    color: #fbbf24;
    margin-bottom: 0.5rem;
  }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────

def confidence_bar_html(confidence: int) -> str:
    """Return HTML for a coloured confidence progress bar."""
    pct = int((confidence / 5) * 100)
    if confidence <= 2:
        color = "#ef4444"
    elif confidence == 3:
        color = "#f59e0b"
    elif confidence == 4:
        color = "#3b82f6"
    else:
        color = "#22c55e"
    label = CONFIDENCE_LABELS.get(confidence, "")
    return f"""
    <div style="margin:6px 0 2px;">
      <div class="conf-label">Confidence: {label}</div>
      <div style="background:#1e293b;border-radius:6px;height:7px;overflow:hidden;">
        <div style="width:{pct}%;height:100%;background:{color};border-radius:6px;
                    transition:width 0.4s ease;"></div>
      </div>
    </div>"""


def source_chips_html(sources: list[str]) -> str:
    """Return HTML for league-coloured source chips."""
    chips = []
    for src in sources:
        league = SOURCE_LEAGUE_MAP.get(src, "All")
        pal = LEAGUE_COLORS.get(league, LEAGUE_COLORS["All"])
        chip = (
            f'<span class="source-chip" '
            f'style="background:{pal["bg"]};color:{pal["text"]};'
            f'border-color:{pal["border"]};">'
            f'🔗 {src}</span>'
        )
        chips.append(chip)
    return "<div style='margin-top:6px'>" + "".join(chips) + "</div>"


def parse_and_render_transfer_cards(answer: str) -> None:
    """
    Parse the agent's markdown answer.
    If it contains '### 🏟️' transfer headers, render each one as a card.
    Otherwise fall back to plain markdown.
    """
    sections = re.split(r"(?=###\s)", answer)
    has_cards = any(
        s.strip().startswith("###") and ("→" in s or "->" in s or "🏟️" in s)
        for s in sections
    )

    if not has_cards:
        st.markdown(answer)
        return

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if section.startswith("###") and ("→" in section or "->" in section or "🏟️" in section):
            lines = section.split("\n")
            header = lines[0].lstrip("#").strip()
            body   = "\n".join(lines[1:]).strip()
            # Render as a styled card
            body_html = body.replace("\n", "<br>")
            st.markdown(
                f'<div class="transfer-card">'
                f'  <h4>⚽ {header}</h4>'
                f'  <p>{body_html}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            # Plain intro text or other content
            st.markdown(section)


def fire_confetti() -> None:
    """Inject a one-shot confetti burst via canvas-confetti CDN."""
    components.html("""
    <script>
      (function() {
        var s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.2/dist/confetti.browser.min.js';
        s.onload = function() {
          confetti({
            particleCount: 200,
            spread: 90,
            origin: { y: 0.55 },
            colors: ['#e94560','#0f3460','#ffffff','#22c55e','#f59e0b']
          });
          setTimeout(function() {
            confetti({ particleCount: 80, angle: 60, spread: 55, origin: { x: 0 } });
            confetti({ particleCount: 80, angle: 120, spread: 55, origin: { x: 1 } });
          }, 400);
        };
        document.head.appendChild(s);
      })();
    </script>
    """, height=0)


def format_ts(ts: float | None) -> str:
    if ts is None:
        return ""
    return datetime.fromtimestamp(ts).strftime("%H:%M")


def export_chat_text(messages: list[dict]) -> str:
    lines = ["FabrizioAI — Chat Export", "=" * 40, ""]
    for msg in messages:
        role = "YOU" if msg["role"] == "user" else "FABRIZIOAI"
        ts   = format_ts(msg.get("ts"))
        lines.append(f"[{ts}] {role}:")
        lines.append(msg["content"])
        if msg.get("sources"):
            lines.append("Sources: " + ", ".join(msg["sources"]))
        lines.append("")
    return "\n".join(lines)


# ── Session state bootstrap ────────────────────────────────────────────────
if "messages"          not in st.session_state: st.session_state.messages          = []
if "fabrizio"          not in st.session_state: st.session_state.fabrizio          = FabrizioAI()
if "last_auto_refresh" not in st.session_state: st.session_state.last_auto_refresh = 0.0
if "query_count"       not in st.session_state: st.session_state.query_count       = 0
if "confetti_fired"    not in st.session_state: st.session_state.confetti_fired    = set()

_proc = st.session_state.fabrizio._graph  # just to keep the agent warm; processor accessed below
_processor = __import__("processor", fromlist=["TransferProcessor"]).TransferProcessor()


# ── Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fab-header">
  <div>
    <h1>⚽ FabrizioAI</h1>
    <div class="subtitle">
      <span class="live-dot"></span>
      Transfer Intelligence · Gemini + Live Scraping · 8 Sources
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")

    league_filter = st.multiselect(
        "Leagues to monitor",
        ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1", "All"],
        default=["All"],
    )
    confidence_threshold = st.slider(
        "Min. confidence to show",
        min_value=1, max_value=5, value=3,
        help="1 = rumour · 5 = Here We Go confirmed",
    )
    use_live_scrape = st.toggle("🌐 Live web scrape", value=True)

    # ── Auto-refresh ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🔄 Auto-Refresh")
    auto_refresh = st.toggle("Enable auto-refresh", value=False)
    refresh_mins = st.select_slider(
        "Interval (minutes)", options=[2, 5, 10, 15, 30], value=5,
        disabled=not auto_refresh,
    )

    if auto_refresh:
        elapsed    = time.time() - st.session_state.last_auto_refresh
        remaining  = max(0, refresh_mins * 60 - elapsed)
        mins, secs = int(remaining // 60), int(remaining % 60)
        st.caption(f"⏱ Next refresh in **{mins}:{secs:02d}**")

    # ── Quick Asks ────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🔥 Quick Asks")
    quick_prompts = [
        "Latest confirmed transfers today",
        "Biggest rumours this week",
        "Which clubs are most active right now?",
        "Any Premier League deadline day news?",
        "Top Serie A signings this window",
        "Bundesliga transfer latest",
    ]
    for qp in quick_prompts:
        if st.button(qp, use_container_width=True, key=f"qp_{qp}"):
            st.session_state.quick_query = qp

    # ── Watchlist ─────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 👁️ Watchlist")
    with st.form("watchlist_form", clear_on_submit=True):
        wl_name = st.text_input("Player or Club", placeholder="e.g. Mbappé, Arsenal")
        wl_type = st.radio("Type", ["player", "club"], horizontal=True)
        if st.form_submit_button("➕ Add", use_container_width=True):
            if wl_name.strip():
                _processor.add_to_watchlist(wl_name.strip(), wl_type)
                st.success(f"Added **{wl_name}** to watchlist.")

    watchlist = _processor.get_watchlist()
    if watchlist:
        for item in watchlist:
            col_l, col_r = st.columns([4, 1])
            with col_l:
                icon = "🧑" if item["type"] == "player" else "🏟️"
                st.markdown(
                    f'<div class="watchlist-item">{icon} {item["name"]}</div>',
                    unsafe_allow_html=True,
                )
            with col_r:
                if st.button("✕", key=f"del_wl_{item['id']}", help="Remove"):
                    _processor.remove_from_watchlist(item["id"])
                    st.rerun()
    else:
        st.caption("No items yet — add players or clubs above.")

    # ── Session Stats ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📊 Session Stats")
    stats = _processor.stats()
    st.markdown(
        f'<div class="stat-item">📰 <strong>{stats["total_articles"]}</strong> articles in KB</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="stat-item">💬 <strong>{st.session_state.query_count}</strong> queries this session</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="stat-item">🕐 Last scrape: <strong>{stats["last_scrape"]}</strong></div>',
        unsafe_allow_html=True,
    )
    if stats["sources_scraped"]:
        st.caption("Sources: " + " · ".join(stats["sources_scraped"][:4]))

    st.divider()

    # ── Export + Clear ────────────────────────────────────────────────────
    if st.session_state.messages:
        st.download_button(
            label="📥 Export Chat",
            data=export_chat_text(st.session_state.messages),
            file_name=f"fabrizioai_chat_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.query_count = 0
        st.rerun()

    st.markdown("""
    <div style="color:#374151;font-size:0.7rem;margin-top:1rem;line-height:1.5;">
    FabrizioAI aggregates 8 football sources with Gemini reasoning.
    Always verify with official club announcements.
    </div>
    """, unsafe_allow_html=True)


# ── Auto-refresh trigger (runs silently on schedule) ──────────────────────
if auto_refresh:
    elapsed = time.time() - st.session_state.last_auto_refresh
    if elapsed >= refresh_mins * 60:
        st.session_state.last_auto_refresh = time.time()
        with st.toast("🔄 Auto-refreshing transfer news…"):
            try:
                st.session_state.fabrizio.get_transfer_insight(
                    query="latest transfer news today",
                    league_filter=league_filter,
                    confidence_threshold=1,
                    use_live_scrape=True,
                )
            except Exception:
                pass
        st.rerun()


# ── Chat history ──────────────────────────────────────────────────────────
if not st.session_state.messages:
    # Empty-state welcome screen
    st.markdown("""
    <div class="empty-state">
      <h2>Welcome to FabrizioAI ⚽</h2>
      <p>Your personal transfer intelligence assistant. Ask me about any player, club, or transfer rumour
         and I'll scrape live sources and give you the latest — in the style of Fabrizio Romano.</p>
      <p style="color:#475569; font-size:0.85rem; margin-top:1rem;">
        Try: <em>"Any Premier League news today?"</em> or <em>"Latest on Mbappé"</em>
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Suggestion grid
    suggestions = [
        ("🔴", "Confirmed transfers today", "Latest confirmed transfers today"),
        ("👀", "Biggest rumours", "Biggest rumours this week"),
        ("📈", "Most active clubs", "Which clubs are most active right now?"),
        ("🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Premier League news", "Any Premier League deadline day news?"),
        ("🇮🇹", "Serie A signings", "Top Serie A signings this window"),
        ("🇩🇪", "Bundesliga latest", "Bundesliga transfer latest"),
    ]
    cols = st.columns(3)
    for i, (icon, label, query_text) in enumerate(suggestions):
        with cols[i % 3]:
            if st.button(f"{icon} {label}", use_container_width=True, key=f"sug_{i}"):
                st.session_state.quick_query = query_text

else:
    # Render stored chat messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
                st.markdown(
                    f'<div class="msg-ts">{format_ts(msg.get("ts"))}</div>',
                    unsafe_allow_html=True,
                )
        else:
            with st.chat_message("assistant", avatar="⚽"):
                parse_and_render_transfer_cards(msg["content"])

                confidence = msg.get("confidence", 3)
                st.markdown(
                    confidence_bar_html(confidence),
                    unsafe_allow_html=True,
                )

                if msg.get("sources"):
                    st.markdown(
                        source_chips_html(msg["sources"]),
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f'<div class="msg-ts">{format_ts(msg.get("ts"))}</div>',
                    unsafe_allow_html=True,
                )


# ── Input & query handling ─────────────────────────────────────────────────
quick_query = st.session_state.pop("quick_query", None)
user_input  = st.chat_input("Ask about any transfer, player, or club…")
query       = quick_query or user_input

if query:
    now_ts = time.time()
    st.session_state.messages.append({
        "role": "user",
        "content": query,
        "ts": now_ts,
    })
    st.session_state.query_count += 1

    with st.chat_message("user"):
        st.markdown(query)
        st.markdown(
            f'<div class="msg-ts">{format_ts(now_ts)}</div>',
            unsafe_allow_html=True,
        )

    with st.chat_message("assistant", avatar="⚽"):
        # ── Live status panel ──────────────────────────────────────────
        with st.status("🔍 Scouting sources…", expanded=True) as status:
            st.write("📚 Checking knowledge base…")
            time.sleep(0.3)

            if use_live_scrape:
                st.write("🌐 Scraping live sources (BBC, Sky, Goal, Transfermarkt…)")
            else:
                st.write("⚡ Knowledge-base-only mode (fast)")

            st.write("🤖 Reasoning with Gemini…")

            response = st.session_state.fabrizio.get_transfer_insight(
                query=query,
                league_filter=league_filter,
                confidence_threshold=confidence_threshold,
                use_live_scrape=use_live_scrape,
            )

            status.update(label="✅ Done!", state="complete", expanded=False)

        # ── Render response ────────────────────────────────────────────
        parse_and_render_transfer_cards(response["answer"])

        confidence = response.get("confidence", 3)
        st.markdown(confidence_bar_html(confidence), unsafe_allow_html=True)

        if response.get("sources"):
            st.markdown(source_chips_html(response["sources"]), unsafe_allow_html=True)

        resp_ts = time.time()
        st.markdown(
            f'<div class="msg-ts">{format_ts(resp_ts)}</div>',
            unsafe_allow_html=True,
        )

        # ── HERE WE GO confetti ────────────────────────────────────────
        if confidence == 5:
            msg_id = f"confetti_{int(resp_ts)}"
            if msg_id not in st.session_state.confetti_fired:
                st.session_state.confetti_fired.add(msg_id)
                fire_confetti()
                st.success("🎉 HERE WE GO! Deal confirmed!")

    # ── Store message ──────────────────────────────────────────────────────
    st.session_state.messages.append({
        "role":       "assistant",
        "content":    response["answer"],
        "sources":    response.get("sources", []),
        "confidence": confidence,
        "ts":         resp_ts,
    })

    # Trigger a cheap rerun so the auto-refresh countdown stays live
    time.sleep(0.05)
