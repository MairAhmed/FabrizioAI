# ⚽ FabrizioAI — Transfer Intelligence Agent

> An agentic AI chatbot that scrapes live football transfer news and delivers insights in the style of Fabrizio Romano, powered by Google Gemini and LangGraph.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red?style=flat-square&logo=streamlit)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2%2B-green?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?style=flat-square&logo=google)

---

## 🧠 What It Does

FabrizioAI is a fully agentic transfer news assistant. You ask it about any player, club, or transfer rumour — and it autonomously:

1. **Searches its in-memory knowledge base** for previously scraped articles
2. **Scrapes live data** from trusted football sources if needed
3. **Falls back to Gemini's own knowledge** if scraping finds nothing
4. **Reasons over all results** and responds in character as FabrizioAI
5. **Scores confidence** from 1 (rumour) to 5 (HERE WE GO ✅)

All of this happens in a LangGraph agent loop — Gemini decides what tools to call and when it has enough information to answer.

---

## 🏗️ Project Structure

```
FabrizioAI/
│
├── app/
│   ├── main.py          # Streamlit UI
│   ├── utils.py         # LangGraph agent + tool definitions
│   └── prompts.py       # Fabrizio Romano personality + agent instructions
│
├── scripts/
│   ├── scraper.py       # Concurrent web scraper
│   └── processor.py     # In-memory article store + keyword retrieval
│
├── .env.example         # API key template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 📡 Data Sources

| Source | League Focus |
|--------|-------------|
| BBC Sport Transfers | All |
| Goal.com Transfers | All |

> Scraping runs concurrently with a 15s timeout. If a source fails, the agent falls back to Gemini's own training knowledge automatically.

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

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 💬 Example Queries

- *"Any Premier League deadline day news?"*
- *"Latest confirmed transfers today"*
- *"Which clubs are most active this window?"*
- *"What's the latest on Rashford?"*
- *"Top Serie A signings this summer"*
- *"Any Bundesliga rumours this week?"*

---

## ⚙️ Sidebar Controls

| Setting | Description |
|---------|-------------|
| **Leagues to monitor** | Filter answers to specific leagues |
| **Min. confidence to show** | Only show transfers above a confidence threshold (1–5) |
| **Live web scrape** | Toggle real-time scraping on/off (off = faster, uses Gemini knowledge only) |

> 💡 Tip: Turn off **Live web scrape** to save API quota and get faster responses.

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
       │ tool_calls?              ┌────┴────┐
    ┌──▼──┐                       │ Results │
    │ Yes │──► Tool Execution ───►│         │
    └─────┘   (scrape / search)   └─────────┘
    │ No  │
    └──▼──┘
   Final Answer
   (or LLM fallback if no data found)
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

## ⚠️ Common Issues

**`429 RESOURCE_EXHAUSTED`**
Your free tier Gemini quota is used up. Options:
- Wait for midnight PT reset
- Create a new API key in a **new project** at [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- Enable billing on your Google Cloud project

> Free tier gives ~20 requests/day on Gemini 2.5 Flash. Each question uses ~2-3 requests due to the agent loop.

**`404 NOT_FOUND` (model error)**
The model name is outdated. The app uses `gemini-2.5-flash` which is the current stable model as of 2026.

**Scraper failures in terminal**
Normal — some sites block scrapers or change their URLs. The agent automatically falls back to Gemini's knowledge if scraping fails. These are warnings, not crashes.

**Slow responses**
Turn off **Live web scrape** in the sidebar for instant answers using Gemini's own knowledge.

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| [Streamlit](https://streamlit.io) | UI |
| [LangGraph](https://langchain-ai.github.io/langgraph/) | Agentic graph / tool-calling loop |
| [LangChain Google GenAI](https://python.langchain.com/docs/integrations/llms/google_ai) | Gemini LLM |
| [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) | Web scraping |
| In-memory keyword store | Fast article retrieval (no DB needed) |
| [Google Gemini 2.5 Flash](https://ai.google.dev) | LLM backbone |

---

## 📄 License

MIT License — do whatever you want with it.

---

*Built by [Mair Ahmed](https://github.com/MairAhmed)*
