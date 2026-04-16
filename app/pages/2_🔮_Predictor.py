"""
pages/2_🔮_Predictor.py – FabrizioAI Prediction Engine
Three-tab mini-game powered by Gemini + live KB context:
  Tab 1: ⚽ Match Predictor     — pick two teams, get a result prediction
  Tab 2: 🏆 League/Trophy Predictor — pick a competition, get title odds
  Tab 3: 🔄 Transfer Window Predictor — predict the summer/winter business
"""

import sys
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# ── Path setup ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))               # app/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))  # scripts/

from utils import FabrizioPredictor

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FabrizioAI – Predictor",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Cached predictor instance ─────────────────────────────────────────────
@st.cache_resource
def get_predictor() -> FabrizioPredictor:
    return FabrizioPredictor()

predictor = get_predictor()

# ── Club lists ────────────────────────────────────────────────────────────
PREMIER_LEAGUE = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Ipswich Town",
    "Leicester City", "Liverpool", "Manchester City", "Manchester United",
    "Newcastle United", "Nottingham Forest", "Southampton", "Tottenham Hotspur",
    "West Ham United", "Wolves",
]
LA_LIGA = [
    "Athletic Bilbao", "Atletico Madrid", "Barcelona", "Betis",
    "Celta Vigo", "Espanyol", "Getafe", "Girona", "Las Palmas",
    "Leganes", "Mallorca", "Osasuna", "Rayo Vallecano", "Real Madrid",
    "Real Sociedad", "Sevilla", "Valencia", "Valladolid", "Villarreal",
]
SERIE_A = [
    "AC Milan", "Atalanta", "Bologna", "Cagliari", "Como",
    "Empoli", "Fiorentina", "Genoa", "Inter Milan", "Juventus",
    "Lazio", "Lecce", "Monza", "Napoli", "Parma",
    "Roma", "Torino", "Udinese", "Venezia", "Verona",
]
BUNDESLIGA = [
    "Augsburg", "Bayer Leverkusen", "Bayern Munich", "Bochum", "Borussia Dortmund",
    "Borussia Mönchengladbach", "Eintracht Frankfurt", "Freiburg", "Heidenheim",
    "Hoffenheim", "Holstein Kiel", "Mainz", "RB Leipzig", "St. Pauli",
    "Stuttgart", "Union Berlin", "Werder Bremen", "Wolfsburg",
]
LIGUE_1 = [
    "Angers", "Auxerre", "Brest", "Le Havre", "Lens",
    "Lille", "Lyon", "Marseille", "Monaco", "Montpellier",
    "Nantes", "Nice", "Paris Saint-Germain", "Reims", "Rennes",
    "Saint-Etienne", "Strasbourg", "Toulouse",
]
ALL_CLUBS = sorted(set(
    PREMIER_LEAGUE + LA_LIGA + SERIE_A + BUNDESLIGA + LIGUE_1 + [
        "Ajax", "Benfica", "Porto", "Sporting CP", "Celtic",
        "Rangers", "Galatasaray", "Fenerbahce", "PSV Eindhoven",
        "Club Brugge", "Red Bull Salzburg", "Shakhtar Donetsk",
    ]
))

COMPETITIONS = [
    "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
    "UEFA Champions League", "UEFA Europa League", "UEFA Conference League",
    "FA Cup", "Copa del Rey", "Coppa Italia", "DFB-Pokal",
    "FIFA Club World Cup",
]

LEAGUE_COLORS = {
    "Premier League": "#6a2e9e",
    "La Liga": "#dc2626",
    "Serie A": "#2563eb",
    "Bundesliga": "#ca8a04",
    "Ligue 1": "#0369a1",
    "Champions League": "#1d4ed8",
    "Default": "#e94560",
}

# ── CSS ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  h1, h2, h3, h4 { font-family: 'Oswald', sans-serif; letter-spacing: 0.03em; }
  .stApp { background: #0d0d0d; color: #f0f0f0; }

  .pred-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #12122a 50%, #1a0a2e 100%);
    border-bottom: 3px solid #7c3aed;
    padding: 1.2rem 2rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
  }
  .pred-header h1  { color: #fff; font-size: 2rem; margin: 0; }
  .pred-header .sub { color: #7c3aed; font-size: 0.82rem; letter-spacing: 0.15em; text-transform: uppercase; }

  /* Match predictor VS card */
  .match-card {
    background: linear-gradient(135deg, #111827 0%, #1e1b3a 100%);
    border: 1px solid #2d2060;
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
  }
  .team-name {
    font-family: 'Oswald', sans-serif;
    font-size: 1.6rem;
    color: #f1f5f9;
    margin: 0.3rem 0;
  }
  .vs-divider {
    font-family: 'Oswald', sans-serif;
    font-size: 2rem;
    color: #e94560;
    font-weight: 700;
  }

  /* Result display */
  .result-banner {
    border-radius: 10px;
    padding: 1.2rem 1.6rem;
    margin: 1rem 0;
    text-align: center;
  }
  .result-winner {
    font-family: 'Oswald', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
  }
  .result-score {
    font-family: 'Oswald', sans-serif;
    font-size: 2.4rem;
    letter-spacing: 0.15em;
    color: #fbbf24;
  }

  /* Probability bar */
  .prob-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 5px 0;
    font-size: 0.85rem;
  }
  .prob-label { width: 120px; color: #94a3b8; text-align: right; flex-shrink: 0; }
  .prob-bar-bg {
    flex: 1;
    background: #1e293b;
    border-radius: 6px;
    height: 14px;
    overflow: hidden;
  }
  .prob-bar-fill { height: 100%; border-radius: 6px; transition: width 0.6s ease; }
  .prob-pct { width: 42px; text-align: left; color: #e2e8f0; font-weight: 600; flex-shrink: 0; }

  /* Podium */
  .podium-item {
    background: linear-gradient(135deg, #111827, #1e293b);
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 1rem;
    margin: 0.5rem 0;
    display: flex;
    align-items: flex-start;
    gap: 1rem;
  }
  .podium-rank {
    font-family: 'Oswald', sans-serif;
    font-size: 1.8rem;
    color: #7c3aed;
    min-width: 40px;
    text-align: center;
    line-height: 1;
  }
  .podium-team { font-family: 'Oswald', sans-serif; font-size: 1.1rem; color: #f1f5f9; }
  .podium-reason { font-size: 0.8rem; color: #64748b; margin-top: 3px; }

  /* Transfer prediction card */
  .transfer-pred-card {
    background: linear-gradient(135deg, #0f1a2e, #1a2642);
    border: 1px solid #1e3a5f;
    border-left: 4px solid #7c3aed;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    margin: 0.5rem 0;
  }
  .tp-player { font-family: 'Oswald', sans-serif; font-size: 1.05rem; color: #f1f5f9; }
  .tp-clubs  { font-size: 0.83rem; color: #93c5fd; margin: 2px 0; }
  .tp-fee    { font-size: 0.78rem; color: #fbbf24; }
  .tp-reason { font-size: 0.8rem; color: #64748b; margin-top: 4px; }

  /* Status pill */
  .status-pill {
    display: inline-block;
    font-family: 'Oswald', sans-serif;
    font-size: 0.68rem;
    letter-spacing: 0.07em;
    padding: 1px 8px;
    border-radius: 10px;
    margin-left: 6px;
  }

  /* Key factor chips */
  .factor-chip {
    display: inline-block;
    background: #1e293b;
    border: 1px solid #334155;
    color: #94a3b8;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.78rem;
    margin: 3px 3px 3px 0;
  }

  /* Theme chip */
  .theme-chip {
    display: inline-block;
    background: #1a0a2e;
    border: 1px solid #4c1d95;
    color: #c4b5fd;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.78rem;
    margin: 3px 3px 3px 0;
  }

  .analysis-box {
    background: #111827;
    border-left: 3px solid #7c3aed;
    border-radius: 0 8px 8px 0;
    padding: 0.8rem 1rem;
    color: #94a3b8;
    font-size: 0.88rem;
    line-height: 1.6;
    margin: 0.8rem 0;
  }

  .storyline-item {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    padding: 0.5rem 0.8rem;
    margin: 0.3rem 0;
    font-size: 0.85rem;
    color: #cbd5e1;
  }

  section[data-testid="stSidebar"] { background: #0a0a0a; }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pred-header">
  <h1>🔮 FabrizioAI Prediction Engine</h1>
  <div class="sub">Gemini-powered · Grounded in live transfer news · 3 prediction modes</div>
</div>
""", unsafe_allow_html=True)

st.caption(
    "⚠️ Predictions are AI-generated for entertainment. "
    "They factor in scraped KB data — the more articles in your KB, the better the predictions."
)

# ── Tabs ──────────────────────────────────────────────────────────────────
tab_match, tab_league, tab_transfer = st.tabs([
    "⚽  Match Predictor",
    "🏆  League & Trophy Predictor",
    "🔄  Transfer Window Predictor",
])


# ════════════════════════════════════════════════════════════
# TAB 1 — MATCH PREDICTOR
# ════════════════════════════════════════════════════════════
with tab_match:
    st.markdown("### Pick your match")

    col_a, col_vs, col_b = st.columns([5, 1, 5])

    with col_a:
        team_a = st.selectbox(
            "Home Team", ALL_CLUBS, index=ALL_CLUBS.index("Arsenal"),
            key="match_team_a",
        )
    with col_vs:
        st.markdown(
            "<div style='text-align:center;margin-top:28px;'>"
            "<span class='vs-divider'>VS</span></div>",
            unsafe_allow_html=True,
        )
    with col_b:
        team_b = st.selectbox(
            "Away Team", ALL_CLUBS, index=ALL_CLUBS.index("Manchester City"),
            key="match_team_b",
        )

    competition_m = st.selectbox(
        "Competition", COMPETITIONS, key="match_comp",
    )

    col_btn, col_note = st.columns([2, 5])
    with col_btn:
        predict_match = st.button(
            "🔮 Predict Match", type="primary", use_container_width=True,
        )
    with col_note:
        st.caption("Uses your scraped KB + Gemini football knowledge to predict the result.")

    if predict_match:
        if team_a == team_b:
            st.error("Please choose two different teams!")
        else:
            with st.spinner(f"Analysing {team_a} vs {team_b}…"):
                try:
                    result = predictor.predict_match(team_a, team_b, competition_m)
                except Exception as e:
                    st.error(f"Prediction error: {e}")
                    st.stop()

            pred    = result.get("prediction", "DRAW")
            home_p  = result.get("home_win_pct", 33)
            draw_p  = result.get("draw_pct", 34)
            away_p  = result.get("away_win_pct", 33)
            score   = result.get("predicted_score", "? - ?")
            factors = result.get("key_factors", [])
            form_h  = result.get("form_home", "? ? ? ? ?")
            form_a  = result.get("form_away", "? ? ? ? ?")
            conf    = result.get("confidence", 3)
            analysis = result.get("analysis", "")

            # Winner banner
            if pred == "HOME_WIN":
                winner_label = f"🏆 {team_a} WIN"
                banner_color = "#14532d"
                border_color = "#22c55e"
            elif pred == "AWAY_WIN":
                winner_label = f"🏆 {team_b} WIN"
                banner_color = "#1e1b4b"
                border_color = "#818cf8"
            else:
                winner_label = "🤝 DRAW"
                banner_color = "#1c1400"
                border_color = "#fbbf24"

            st.markdown(
                f'<div class="result-banner" style="background:{banner_color};border:2px solid {border_color};">'
                f'  <div class="result-winner" style="color:{border_color};">{winner_label}</div>'
                f'  <div class="result-score">{team_a}  {score}  {team_b}</div>'
                f'  <div style="font-size:0.8rem;color:#64748b;margin-top:4px;">{competition_m}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Probability bars
            st.markdown("#### Outcome Probabilities")
            bars = [
                (team_a + " Win", home_p, "#22c55e"),
                ("Draw",          draw_p, "#f59e0b"),
                (team_b + " Win", away_p, "#818cf8"),
            ]
            for label, pct, color in bars:
                st.markdown(
                    f'<div class="prob-row">'
                    f'  <div class="prob-label">{label}</div>'
                    f'  <div class="prob-bar-bg">'
                    f'    <div class="prob-bar-fill" style="width:{pct}%;background:{color};"></div>'
                    f'  </div>'
                    f'  <div class="prob-pct">{pct}%</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Form + confidence
            col_f1, col_f2, col_cf = st.columns(3)
            with col_f1:
                st.metric(f"{team_a} Form (last 5)", form_h)
            with col_f2:
                st.metric(f"{team_b} Form (last 5)", form_a)
            with col_cf:
                st.metric("Prediction Confidence", f"{conf}/5 ⭐")

            # Key factors
            if factors:
                st.markdown("#### Key Factors")
                chips = "".join(
                    f'<span class="factor-chip">📌 {f}</span>' for f in factors
                )
                st.markdown(chips, unsafe_allow_html=True)

            # Analysis
            if analysis:
                st.markdown(
                    f'<div class="analysis-box">🧠 {analysis}</div>',
                    unsafe_allow_html=True,
                )

            # Confetti for a big match
            if conf >= 4:
                components.html("""
                <script>
                  var s=document.createElement('script');
                  s.src='https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.2/dist/confetti.browser.min.js';
                  s.onload=function(){confetti({particleCount:120,spread:70,origin:{y:0.6},colors:['#22c55e','#818cf8','#fbbf24']});};
                  document.head.appendChild(s);
                </script>
                """, height=0)


# ════════════════════════════════════════════════════════════
# TAB 2 — LEAGUE & TROPHY PREDICTOR
# ════════════════════════════════════════════════════════════
with tab_league:
    st.markdown("### Pick a competition")

    col_comp, col_season = st.columns([3, 2])
    with col_comp:
        competition_l = st.selectbox("Competition", COMPETITIONS, key="league_comp")
    with col_season:
        season = st.selectbox("Season", ["2025/26", "2024/25"], key="league_season")

    if st.button("🔮 Predict Champion", type="primary", use_container_width=False):
        with st.spinner(f"Crunching {competition_l} title race…"):
            try:
                result = predictor.predict_league(competition_l, season)
            except Exception as e:
                st.error(f"Prediction error: {e}")
                st.stop()

        preds      = result.get("predictions", [])
        storylines = result.get("key_storylines", [])
        dark_horse = result.get("dark_horse", "")
        analysis   = result.get("analysis", "")

        st.markdown(f"#### 🏆 {competition_l} {season} — Title Predictions")

        # Podium display
        rank_medals = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣"}
        rank_colors = {
            1: "#ca8a04", 2: "#94a3b8", 3: "#b45309", 4: "#374151", 5: "#374151",
        }

        for pred in preds:
            rank    = pred.get("rank", 0)
            team    = pred.get("team", "Unknown")
            prob    = pred.get("probability_pct", 0)
            reason  = pred.get("reasoning", "")
            medal   = rank_medals.get(rank, str(rank))
            r_color = rank_colors.get(rank, "#374151")
            bar_col = "#ca8a04" if rank == 1 else "#6b7280"

            st.markdown(
                f'<div class="podium-item" style="border-color:{r_color}33;">'
                f'  <div class="podium-rank" style="color:{r_color};">{medal}</div>'
                f'  <div style="flex:1;">'
                f'    <div class="podium-team">{team}'
                f'      <span style="color:#64748b;font-size:0.85rem;font-family:Inter,sans-serif;"> – {prob}%</span>'
                f'    </div>'
                f'    <div class="podium-reason">{reason}</div>'
                f'    <div style="background:#1e293b;border-radius:4px;height:5px;margin-top:6px;overflow:hidden;">'
                f'      <div style="width:{min(prob,100)}%;height:100%;background:{bar_col};border-radius:4px;"></div>'
                f'    </div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Dark horse
        if dark_horse:
            st.markdown(
                f'<div style="background:#1a0a2e;border:1px solid #4c1d95;border-radius:8px;'
                f'padding:0.7rem 1rem;margin:0.8rem 0;">'
                f'  🐴 <strong style="color:#c4b5fd;">Dark Horse:</strong> '
                f'  <span style="color:#e2e8f0;">{dark_horse}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Storylines
        if storylines:
            st.markdown("#### 📖 Key Storylines")
            for s in storylines:
                st.markdown(
                    f'<div class="storyline-item">📌 {s}</div>',
                    unsafe_allow_html=True,
                )

        # Analysis
        if analysis:
            st.markdown(
                f'<div class="analysis-box">🧠 {analysis}</div>',
                unsafe_allow_html=True,
            )


# ════════════════════════════════════════════════════════════
# TAB 3 — TRANSFER WINDOW PREDICTOR
# ════════════════════════════════════════════════════════════
with tab_transfer:
    st.markdown("### Configure the prediction")

    col_w, col_l, col_f = st.columns(3)
    with col_w:
        window = st.radio("Transfer Window", ["Summer", "Winter"], horizontal=True)
    with col_l:
        tw_leagues = st.multiselect(
            "Focus Leagues",
            ["All", "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"],
            default=["All"],
        )
    with col_f:
        focus = st.text_input(
            "Player / Club focus (optional)",
            placeholder="e.g. Mbappé, Arsenal striker",
        )

    col_b1, col_b2 = st.columns([2, 5])
    with col_b1:
        predict_transfers = st.button(
            "🔮 Predict Transfers", type="primary", use_container_width=True,
        )
    with col_b2:
        st.caption("Predicts the 8 most likely moves using current KB news + Gemini transfer knowledge.")

    if predict_transfers:
        leagues_str = ", ".join(tw_leagues) if tw_leagues else "All"
        with st.spinner(f"Predicting {window} window moves…"):
            try:
                result = predictor.predict_transfers(
                    window=window,
                    leagues=leagues_str,
                    focus=focus,
                )
            except Exception as e:
                st.error(f"Prediction error: {e}")
                st.stop()

        preds    = result.get("predictions", [])
        surprise = result.get("biggest_surprise", "")
        themes   = result.get("window_themes", [])
        analysis = result.get("analysis", "")

        st.markdown(f"#### 🔄 Predicted {window} Window Moves")

        STATUS_COLORS = {
            "Almost Certain": ("#14532d", "#22c55e"),
            "Likely":         ("#1e3a5f", "#3b82f6"),
            "Talks":          ("#422006", "#f59e0b"),
            "Rumour":         ("#1e1b4b", "#818cf8"),
        }

        for pred in preds:
            rank      = pred.get("rank", "?")
            player    = pred.get("player", "Unknown")
            from_club = pred.get("from_club", "?")
            to_club   = pred.get("to_club", "?")
            fee       = pred.get("fee_estimate", "TBD")
            pct       = pred.get("likelihood_pct", 50)
            reasoning = pred.get("reasoning", "")
            status    = pred.get("status", "Rumour")

            s_bg, s_txt = STATUS_COLORS.get(status, ("#1e1b4b", "#818cf8"))
            bar_col     = s_txt

            st.markdown(
                f'<div class="transfer-pred-card">'
                f'  <div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                f'    <div>'
                f'      <span style="color:#64748b;font-size:0.78rem;margin-right:6px;">#{rank}</span>'
                f'      <span class="tp-player">{player}</span>'
                f'      <span class="status-pill" style="background:{s_bg};color:{s_txt};border:1px solid {s_txt}44;">'
                f'        {status}'
                f'      </span>'
                f'    </div>'
                f'    <div style="font-family:Oswald,sans-serif;font-size:1.2rem;color:{bar_col};font-weight:700;">'
                f'      {pct}%'
                f'    </div>'
                f'  </div>'
                f'  <div class="tp-clubs">🏟️ {from_club}  →  ✈️ {to_club}</div>'
                f'  <div class="tp-fee">💶 {fee}</div>'
                f'  <div style="background:#0f172a;border-radius:4px;height:5px;margin:6px 0 4px;overflow:hidden;">'
                f'    <div style="width:{min(pct,100)}%;height:100%;background:{bar_col};border-radius:4px;"></div>'
                f'  </div>'
                f'  <div class="tp-reason">📌 {reasoning}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Biggest surprise
        if surprise:
            st.markdown(
                f'<div style="background:#1a0a2e;border:1px solid #4c1d95;border-radius:8px;'
                f'padding:0.8rem 1rem;margin:0.8rem 0;">'
                f'  💥 <strong style="color:#c4b5fd;">Biggest Surprise Pick:</strong><br>'
                f'  <span style="color:#e2e8f0;font-size:0.9rem;">{surprise}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Window themes
        if themes:
            st.markdown("#### 📊 Window Themes")
            chips = "".join(
                f'<span class="theme-chip">🔥 {t}</span>' for t in themes
            )
            st.markdown(chips, unsafe_allow_html=True)

        # Analysis
        if analysis:
            st.markdown(
                f'<div class="analysis-box">🧠 {analysis}</div>',
                unsafe_allow_html=True,
            )

        # Confetti for Here We Go vibes
        components.html("""
        <script>
          var s=document.createElement('script');
          s.src='https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.2/dist/confetti.browser.min.js';
          s.onload=function(){
            confetti({particleCount:80,spread:60,origin:{y:0.5},colors:['#7c3aed','#e94560','#fbbf24']});
          };
          document.head.appendChild(s);
        </script>
        """, height=0)
