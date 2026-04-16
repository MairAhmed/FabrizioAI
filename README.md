# ⚽ FabrizioAI — Transfer Intelligence Agent

> *"Here We Go!"* — A fully agentic football transfer intelligence app powered by Google Gemini and LangGraph. Chat with it, browse live news, and run AI-powered predictions — all in the style of Fabrizio Romano.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red?style=flat-square&logo=streamlit)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2%2B-green?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?style=flat-square&logo=google)
![SQLite](https://img.shields.io/badge/SQLite-Persistent_KB-lightblue?style=flat-square&logo=sqlite)

---

## 🧠 What It Does

FabrizioAI is a multi-page transfer intelligence platform. It scrapes 8 live football sources, stores articles in a persistent SQLite knowledge base, and lets you interact with that data in three ways:

| Page | What it does |
|------|-------------|
| **💬 Chat** | Ask anything about transfers, players, or clubs — the agent scrapes live sources and reasons with Gemini |
| **📰 News Feed** | Browse all scraped articles in a card grid, filterable by league and confidence |
| **🔮 Predictor** | AI-powered mini-game: predict match results, league champions, and transfer window moves |

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
│       └── 2_🔮_Predictor.py   # Match / league / transfer predictor
│
├── scripts/
│   ├── scraper.py               # Concurrent scraper — 8 sources, multi-URL fallback
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

The scraper pulls from 8 trusted football sources concurrently. Each source has multiple fallback URLs so a site restructure never breaks the pipeline.

| Source | League Focus |
|--------|-------------|
| BBC Sport Transfers | All |
| Goal.com Transfers | All |
| Sky Sports Transfers | Premier League |
| Transfermarkt | All |
| Calciomercato | Serie A |
| Marca | La Liga |
| L'Equipe | Ligue 1 |
| Kicker | Bundesliga |

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
- "Scrape Now" button hits all 8 sources directly from the feed
- Knowledge base stats (total articles, sources scraped)

### 🔮 Predictor Page
Three prediction modes, all powered by Gemini grounded in your scraped KB:

**⚽ Match Predictor**
- Pick any two clubs from all five major leagues
- Returns: win/draw/loss probabilities, predicted scoreline, last-5 form, key factors, expert analysis
- Confetti on high-confidence predictions

**🏆 League & Trophy Predictor**
- Covers all major competitions including Champions League, Europa League, and Club World Cup
- Returns: medal podium for top 5 contenders with probability bars, dark horse pick, key storylines

**🔄 Transfer Window Predictor**
- Summer or Winter window, filterable by league and player/club focus
- Returns: 8 ranked transfer predictions each with player, clubs, fee estimate, likelihood %, status pill (Rumour → Almost Certain), and reasoning
- Highlights the "biggest surprise" move nobody is talking about yet

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
streamlit run app/main.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser. The News Feed and Predictor pages appear automatically in the Streamlit sidebar.

---

## 💬 Example Chat Queries

- *"Any Premier League deadline day news?"*
- *"Latest confirmed transfers today"*
- *"Which clubs are most active this window?"*
- *"What's the latest on Mbappé?"*
- *"Top Serie A signings this summer"*
- *"Any Bundesliga rumours this week?"*

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

---

## ⚠️ Common Issues

**`Agent error: futures unfinished`**
A slow scraping source timed out. This is now handled gracefully — the app collects results from whichever sources finished and discards the rest. You'll still get an answer from the KB or the fast sources.

**`429 RESOURCE_EXHAUSTED`**
Your free-tier Gemini quota is used up. Options:
- Wait for midnight PT reset
- Create a new API key at [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- Enable billing on your Google Cloud project (very cheap, ~$0.01 per query)

**`Model not found (404)`**
The model name is outdated. The app uses `gemini-2.5-flash` by default — update `utils.py` if needed.

**Slow responses**
Turn off **Live web scrape** in the sidebar for faster answers using the cached knowledge base only.

**Scrapers returning no results**
Some sites block automated requests. The scraper tries multiple fallback URLs per source and fails silently — other sources continue normally. You can see which sources are active in the **Session Stats** panel.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | [Streamlit](https://streamlit.io) (multipage) |
| Agent framework | [LangGraph](https://langchain-ai.github.io/langgraph/) |
| LLM | [Google Gemini 2.5 Flash](https://ai.google.dev) via LangChain |
| Scraping | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) + `requests` (concurrent) |
| Knowledge base | SQLite (built-in, no external DB needed) |
| Confetti | [canvas-confetti](https://github.com/catdad/canvas-confetti) |

---

## 📄 License

MIT License — do whatever you want with it.

---

*Built by [Mair Ahmed](https://github.com/MairAhmed)*
