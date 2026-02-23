import streamlit as st
import asyncio
from utils import FabrizioAI
from prompts import ROMANO_SYSTEM_PROMPT

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FabrizioAI – Transfer Insights",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Inter:wght@300;400;500&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  h1, h2, h3 { font-family: 'Oswald', sans-serif; letter-spacing: 0.03em; }

  .stApp { background: #0d0d0d; color: #f0f0f0; }

  /* Header banner */
  .fab-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-bottom: 3px solid #e94560;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    border-radius: 8px;
  }
  .fab-header h1 { color: #ffffff; font-size: 2.4rem; margin: 0; }
  .fab-header .subtitle { color: #e94560; font-size: 0.9rem; letter-spacing: 0.15em; text-transform: uppercase; }

  /* Chat bubbles */
  .user-msg {
    background: #1e1e2e;
    border-left: 4px solid #e94560;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
  }
  .bot-msg {
    background: #16213e;
    border-left: 4px solid #0f3460;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
  }

  /* Confidence badge */
  .confidence-badge {
    display: inline-block;
    background: #e94560;
    color: white;
    font-family: 'Oswald', sans-serif;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    padding: 2px 10px;
    border-radius: 12px;
    margin-left: 8px;
  }

  /* Source chip */
  .source-chip {
    display: inline-block;
    background: #0f3460;
    color: #a0c4ff;
    font-size: 0.72rem;
    padding: 2px 8px;
    border-radius: 6px;
    margin: 2px;
    border: 1px solid #1a4a8a;
  }

  /* Input box override */
  .stTextInput > div > div > input {
    background: #1a1a2e !important;
    color: #f0f0f0 !important;
    border: 1px solid #e94560 !important;
    border-radius: 6px !important;
  }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: #0d0d0d;
    border-right: 1px solid #1e1e2e;
  }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fab-header">
  <h1>⚽ FabrizioAI</h1>
  <div class="subtitle">Transfer Intelligence · Powered by Gemini + Live Scraping</div>
</div>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "fabrizio" not in st.session_state:
    st.session_state.fabrizio = FabrizioAI()

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")

    league_filter = st.multiselect(
        "Leagues to monitor",
        ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1", "All"],
        default=["All"],
    )

    confidence_threshold = st.slider(
        "Min. confidence to show",
        min_value=1, max_value=5, value=3,
        help="1 = rumour, 5 = Here We Go confirmed"
    )

    use_live_scrape = st.toggle("🌐 Live web scrape", value=True)

    st.divider()
    st.markdown("### 🔥 Quick Asks")
    quick_prompts = [
        "Latest confirmed transfers today",
        "Biggest rumours this week",
        "Which clubs are most active right now?",
        "Any Premier League deadline day news?",
        "Top Serie A signings this window",
    ]
    for qp in quick_prompts:
        if st.button(qp, use_container_width=True):
            st.session_state.quick_query = qp

    st.divider()
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("""
    <div style="color:#555; font-size:0.72rem; margin-top:1rem;">
    FabrizioAI scrapes trusted football sources and combines them with Gemini reasoning.
    Always verify with official club announcements.
    </div>
    """, unsafe_allow_html=True)

# ── Chat history display ──────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-msg">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bot-msg">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
        if msg.get("sources"):
            src_html = "".join([f'<span class="source-chip">🔗 {s}</span>' for s in msg["sources"]])
            st.markdown(f"<div style='margin-top:4px'>{src_html}</div>", unsafe_allow_html=True)

# ── Input ────────────────────────────────────────────────────────────────
quick_query = st.session_state.pop("quick_query", None)
user_input = st.chat_input("Ask about any transfer, player, or club...")
query = quick_query or user_input

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    st.markdown(f'<div class="user-msg">🧑 {query}</div>', unsafe_allow_html=True)

    with st.spinner("Scouting sources... 🔍"):
        response = st.session_state.fabrizio.get_transfer_insight(
            query=query,
            league_filter=league_filter,
            confidence_threshold=confidence_threshold,
            use_live_scrape=use_live_scrape,
        )

    st.session_state.messages.append({
        "role": "assistant",
        "content": response["answer"],
        "sources": response.get("sources", []),
    })

    st.markdown(f'<div class="bot-msg">🤖 {response["answer"]}</div>', unsafe_allow_html=True)
    if response.get("sources"):
        src_html = "".join([f'<span class="source-chip">🔗 {s}</span>' for s in response["sources"]])
        st.markdown(f"<div style='margin-top:4px'>{src_html}</div>", unsafe_allow_html=True)