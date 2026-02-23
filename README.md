# ⚽ FabrizioAI — Transfer Intelligence Agent

> *"Here We Go!"* — An agentic AI chatbot that scrapes live football transfer news and delivers insights in the style of Fabrizio Romano, powered by Google Gemini and LangGraph.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red?style=flat-square&logo=streamlit)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2%2B-green?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-2.0_Flash_Lite-orange?style=flat-square&logo=google)

---

## 🧠 What It Does

FabrizioAI is a fully agentic transfer news assistant. You ask it about any player, club, or transfer rumour — and it autonomously:

1. **Searches its local knowledge base** (ChromaDB vector store) for cached articles
2. **Scrapes live data** from 8 trusted football sources if needed
3. **Reasons over the results** using Gemini and responds in character as FabrizioAI
4. **Scores confidence** from 1 (rumour) to 5 (HERE WE GO ✅)

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
│   ├── scraper.py       # Concurrent web scraper (8 sources)
│   └── processor.py     # ChromaDB vector store (embed + retrieve)
│
├── .env.example         # API key template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 📡 Data Sources

The scraper pulls from:

| Source | League Focus |
|--------|-------------|
| Fabrizio Romano (via Nitter) | All |
| BBC Sport Transfers | Premier League |
| Sky Sports Transfer News | Premier League |
| Transfermarkt | All |
| Marca | La Liga |
| Calciomercato | Serie A |
| Kicker | Bundesliga |
| L'Equipe | Ligue 1 |

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
- *"What's the latest on Mbappé?"*
- *"Top Serie A signings this summer"*
- *"Any Bundesliga rumours this week?"*

---

## ⚙️ Sidebar Controls

| Setting | Description |
|---------|-------------|
| **Leagues to monitor** | Filter scraping and answers to specific leagues |
| **Min. confidence to show** | Only show transfers above a confidence threshold (1–5) |
| **Live web scrape** | Toggle real-time scraping on/off (off = knowledge base only, faster) |

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
    │ No  │    / assess)
    └──▼──┘
   Final Answer
```

The agent runs a maximum of 2 tool calls per query to keep responses fast.

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
- Create a new API key at [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- Enable billing on your Google Cloud project (very cheap)

**`Model not found (404)`**
The model name is outdated. The app uses `gemini-2.0-flash-lite` by default which is current as of 2026.

**Slow responses**
Turn off **Live web scrape** in the sidebar for faster answers using the cached knowledge base only.

---

## 🛠️ Tech Stack

- **[Streamlit](https://streamlit.io)** — UI
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** — Agentic graph / tool-calling loop
- **[LangChain Google GenAI](https://python.langchain.com/docs/integrations/llms/google_ai)** — Gemini LLM + embeddings
- **[ChromaDB](https://www.trychroma.com)** — Local vector database
- **[BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)** — Web scraping
- **[Google Gemini 2.0 Flash Lite](https://ai.google.dev)** — LLM

---

## 📄 License

MIT License — do whatever you want with it.

---

*Built by [Mair Ahmed](https://github.com/MairAhmed)*
