# ⚽ FabrizioAI — Transfer Intelligence Agent

> *"Here We Go!"* — A fully agentic football transfer intelligence app powered by Google Gemini and LangGraph. Chat with it, browse live news, run AI-powered predictions, and track player movements on a live timeline — all in the style of Fabrizio Romano.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red?style=flat-square&logo=streamlit)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2%2B-green?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?style=flat-square&logo=google)
![SQLite](https://img.shields.io/badge/SQLite-Persistent_KB-lightblue?style=flat-square&logo=sqlite)

---

## 🧠 What It Does

FabrizioAI is a multi-page transfer intelligence platform. It scrapes 13 live football sources, stores articles in a persistent SQLite knowledge base, and lets you interact with that data in four ways:

| Page | What it does |
|------|-------------|
| **💬 Chat** | Ask anything about transfers, players, or clubs — the agent scrapes live sources and reasons with Gemini |
| **📰 News Feed** | Browse all scraped articles in a card grid, filterable by league and confidence |
| **🔮 Predictor** | AI-powered mini-game: predict match results, league champions, and transfer window moves |
| **⏱️ Timeline** | Gemini-extracted player movement tracker — joining & leaving, grouped by date |

---

## 🏗️ Project Structure

```
FabrizioAI/
│
├── app/
│   ├── main.py                  # Chat UI (main page)
│   ├── utils.py                 # LangGraph agent + FabrizioPredictor
│   ├── prompts.py               # Fabrizio Romano personality prompt
│   └── pages/
│       ├── 1_📰_News_Feed.py    # Live article feed page
│       ├── 2_🔮_Predictor.py   # Match / league / transfer predictor
│       └── 3_⏱️_Timeline.py    # AI-powered player movement timeline
│
├── scripts/
│   ├── scraper.py               # Concurrent scraper — 13 sources, multi-URL fallback
│   └── processor.py             # SQLite-backed article store + watchlist
│
├── .chroma_db/
│   └── articles.db              # Persistent SQLite knowledge base (auto-created)
│
├── .env                         # Your API key (never commit this)
├── .env.example                 # API key template
├── requirements.txt
└── README.md
```

---

## 📡 Data Sources

The scraper pulls from 13 trusted football sources concurrently. Each source has multiple fallback URLs so a site restructure never breaks the pipeline.

| Source | League Focus |
|--------|-------------|
| **Fabrizio Romano (Twitter/X)** | All — primary source ⭐ |
| **Fabrizio Romano (Caught Offside)** | All — primary source ⭐ |
| ESPN Soccer | All |
| BBC Sport Transfers | All |
| Goal.com Transfers | All |
| Sky Sports Transfers | Premier League |
| Transfermarkt | All |
| Calciomercato | Serie A |
| Marca | La Liga |
| L'Equipe | Ligue 1 |
| Kicker | Bundesliga |
| MLS Soccer | MLS |
| Saudi Pro League News | Saudi Pro League |

All articles are filtered for English language and football content before being stored — no other sports, no French/Spanish/German/Italian articles slipping through.

---

## ✨ Feature Overview

### 💬 Chat Page
- **`st.chat_message` bubbles** with timestamps on every message
- **Live `st.status` loading panel** showing each step: KB check → scraping → Gemini reasoning
- **Structured transfer cards** — agent responses parsed into styled per-transfer panels
- **Confidence progress bar** on every response (red → amber → blue → green)
- **League-coloured source chips** — Premier League purple, La Liga red, Serie A blue, etc.
- **"Here We Go!" confetti** burst (via canvas-confetti) when confidence hits 5
- **Watchlist** — pin players or clubs; stored in SQLite, persists between sessions
- **Session stats panel** — articles in KB, queries asked, last scrape time
- **Auto-refresh** — configurable timer (2/5/10/15/30 min) that silently re-scrapes in the background
- **Export chat** — download the full conversation as a `.txt` file
- **Welcome screen** — suggestion grid shown when chat is empty

### 📰 News Feed Page
- Card-based grid of all scraped articles (1/2/3 column layout)
- Filter by league, minimum confidence, and sort order
- Confidence bar and league tag on every card
- "Scrape Now" button hits all 13 sources directly from the feed
- English-only and football-only display filters applied on top of the KB
- Knowledge base stats (total articles, sources scraped)

### 🔮 Predictor Page
Three prediction modes, all powered by Gemini grounded in your scraped KB:

**⚽ Match Predictor**
- Pick any two clubs from all major leagues (Premier League, La Liga, Serie A, Bundesliga, Ligue 1, MLS, Saudi Pro League + European clubs)
- Returns: win/draw/loss probabilities, predicted scoreline, last-5 form, key factors, expert analysis

**🏆 League & Trophy Predictor**
- Covers all major competitions including Champions League, Europa League, Conference League, Club World Cup, Leagues Cup, and all domestic cups
- Returns: medal podium for top 5 contenders with probability bars, dark horse pick, key storylines
- Grounded strictly in KB articles — won't repeat stale training data (e.g. won't show knocked-out teams as favourites)

**🔄 Transfer Window Predictor**
- Summer or Winter window, filterable by league and player/club focus
- Returns: ranked transfer predictions each with player, clubs, fee estimate, likelihood %, status pill (Rumour → Almost Certain), and reasoning
- Only predicts named, real players — never invents "Undisclosed Striker" or "Top European Club" placeholders
- Highlights the "biggest surprise" move nobody is talking about yet
- Shows a KB freshness warning if the knowledge base is empty or sparse

### ⏱️ Timeline Page
- **On-demand Gemini extraction** — click "Extract Transfers (AI)" to have Gemini read all KB articles and identify only actual player transfer moves (not injuries, suspensions, or match news)
- Player movement cards showing: player name, JOINING/LEAVING badge, from→to clubs, confidence bar, league tag, source link, and the original headline
- Filters: league, confidence, direction (all / joining / leaving), player/club search, date range
- Summary metrics: total moves, players tracked, joining count, leaving count
- **Quota-safe**: uses `gemini-1.5-flash` (1,500 free calls/day) with `gemini-2.0-flash` as fallback; gracefully degrades to regex extraction if quota is exhausted
- Results cached for 10 minutes to avoid redundant API calls

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- A Google Gemini API key — get one free at [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

---

### 1. Clone the repo

```bash
git clone https://github.com/MairAhmed/FabrizioAI.git
cd FabrizioAI
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your API key

```bash
cp .env.example .env
```

Open `.env` and paste your Gemini API key:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

> ⚠️ Never commit your `.env` file. It's already in `.gitignore`.

### 5. Run the app

```bash
python -m streamlit run app/main.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser. The News Feed, Predictor, and Timeline pages appear automatically in the Streamlit sidebar.

---

## 💬 Example Chat Queries

- *"Any Premier League deadline day news?"*
- *"Latest confirmed transfers today"*
- *"Which clubs are most active this window?"*
- *"What's the latest on Mbappé?"*
- *"Top Serie A signings this summer"*
- *"Any Bundesliga rumours this week?"*
- *"Latest MLS transfer news"*
- *"Who has Al-Hilal signed recently?"*

---

## ⚙️ Chat Sidebar Controls

| Setting | Description |
|---------|-------------|
| **Leagues to monitor** | Filter scraping and answers to specific leagues |
| **Min. confidence to show** | Only show transfers above a confidence threshold (1–5) |
| **Live web scrape** | Toggle real-time scraping on/off (off = KB only, faster) |
| **Auto-refresh** | Automatically re-scrape on a timer (2–30 min intervals) |
| **Watchlist** | Add players or clubs to track; pinned to SQLite across sessions |
| **Session Stats** | Live count of articles in KB, queries asked, last scrape time |
| **Export Chat** | Download the conversation as a `.txt` file |

> 💡 Tip: Turn off **Live web scrape** to save API quota and get faster responses when you already have articles in the KB.

---

## 🔁 How the Agent Works

```
User Query
    │
    ▼
┌─────────────┐
│    Agent    │ ◄─────────────────────┐
│  (Gemini)   │                       │
└──────┬──────┘                       │
       │ tool_calls?                  │
    ┌──▼──┐                      ┌────┴────┐
    │ Yes │──► Tool Execution ──►│ Results │
    └─────┘   (scrape / search   └─────────┘
    │ No  │    / assess_confidence)
    └──▼──┘
   Final Answer (JSON → parsed → rendered as cards)
```

The agent runs a **maximum of 2 tool calls** per query to keep responses fast.

---

## 🔑 Confidence Scale

| Score | Label | Meaning |
|-------|-------|---------|
| 1 | Rumour 🌫️ | Single unverified source |
| 2 | Interest Reported 👀 | Multiple sources reporting interest |
| 3 | Talks Ongoing 🗣️ | Negotiations confirmed |
| 4 | Deal Close 🤝 | Personal terms / fee agreed |
| 5 | HERE WE GO! 🎉 | Fully confirmed, medical/signing done |

---

## 🗄️ Knowledge Base

Articles are stored in a local SQLite database at `.chroma_db/articles.db`. It persists between sessions — the more you use the app, the richer the KB gets and the better the Predictor's grounding becomes. The KB loads the 500 most recent articles into memory on startup for fast keyword retrieval.

The Predictor strictly uses KB articles for current-season facts and will not rely on Gemini's potentially outdated training data. If the KB is empty or sparse, a freshness warning banner is shown before predicting.

---

## ⚠️ Common Issues

**`Agent error: futures unfinished`**
A slow scraping source timed out. This is handled gracefully — the app collects results from whichever sources finished and discards the rest. You'll still get an answer from the KB or the fast sources.

**`429 RESOURCE_EXHAUSTED` on Chat/Predictor**
Your free-tier `gemini-2.5-flash` quota is used up (20 RPD on the free tier). Options:
- Wait for midnight PT reset
- Create a new API key at [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- Enable billing on your Google Cloud project (~$0.01 per query)

**`429 RESOURCE_EXHAUSTED` on Timeline**
The Timeline uses `gemini-1.5-flash` (1,500 RPD free) with `gemini-2.0-flash` as fallback. If both are exhausted it automatically falls back to regex extraction. This is much harder to hit than the Chat quota.

**`Model not found (404)`**
The model name is outdated. The Chat and Predictor use `gemini-2.5-flash`; the Timeline uses `gemini-1.5-flash`. Update `utils.py` or the Timeline page if needed.

**Slow responses**
Turn off **Live web scrape** in the sidebar for faster answers using the cached knowledge base only.

**Scrapers returning no results**
Some sites block automated requests. The scraper tries multiple fallback URLs per source and fails silently — other sources continue normally. You can see which sources are active in the **Session Stats** panel.

**Predictor showing wrong/outdated transfers**
Scrape fresh data first via **📰 News Feed → Scrape Now**, then run the prediction. The Predictor only trusts KB articles for current-season facts — the more up-to-date your KB, the more accurate the predictions.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | [Streamlit](https://streamlit.io) (multipage) |
| Agent framework | [LangGraph](https://langchain-ai.github.io/langgraph/) |
| LLM (Chat + Predictor) | [Google Gemini 2.5 Flash](https://ai.google.dev) via LangChain |
| LLM (Timeline extraction) | [Google Gemini 1.5 Flash](https://ai.google.dev) via LangChain |
| Scraping | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) + `requests` (concurrent) |
| Knowledge base | SQLite (built-in, no external DB needed) |
| Confetti | [canvas-confetti](https://github.com/catdad/canvas-confetti) |

---

## 📄 License

MIT License — do whatever you want with it.

---

*Built by [Mair Ahmed](https://github.com/MairAhmed)*
