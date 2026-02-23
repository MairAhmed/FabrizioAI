"""
utils.py – FabrizioAI LangGraph Agent
A proper agentic graph where Gemini decides what tools to call,
can loop to gather more info, and reasons before responding.

Graph flow:
  START → agent (Gemini decides) → [tools | END]
  tools → agent (Gemini reasons over results) → [tools | END]
"""
import os
import sys
import json
import re
from pathlib import Path
from typing import Annotated, TypedDict, Literal

from dotenv import load_dotenv

# LangGraph + LangChain
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

# Local scripts
sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))
from scraper import TransferScraper
from processor import TransferProcessor
from prompts import ROMANO_SYSTEM_PROMPT

load_dotenv()

# ── Globals (shared across tool calls in a session) ────────────────────────
_scraper = TransferScraper()
_processor = TransferProcessor()

CONFIDENCE_LABELS = {
    1: "Rumour 🌫️",
    2: "Interest Reported 👀",
    3: "Talks Ongoing 🗣️",
    4: "Deal Close 🤝",
    5: "HERE WE GO! 🎉",
}


# ── Agent State ────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    sources_used: list[str]
    confidence: int


# ── Tools ──────────────────────────────────────────────────────────────────

@tool
def scrape_transfer_news(query: str, leagues: str = "All") -> str:
    """
    Scrape live transfer news from trusted football sources (BBC Sport, Sky Sports,
    Transfermarkt, Calciomercato, Marca, Kicker, L'Equipe, Fabrizio Romano).
    Use this when you need fresh, real-time information about a transfer or player.

    Args:
        query: The player name, club, or transfer topic to search for.
        leagues: Comma-separated league names to focus on, or 'All'.
                 Options: 'Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1', 'All'

    Returns:
        JSON string with scraped articles.
    """
    league_list = [l.strip() for l in leagues.split(",")] if leagues != "All" else ["All"]
    articles = _scraper.scrape(query=query, league_filter=league_list)

    if not articles:
        return json.dumps({"status": "no_results", "articles": []})

    # Store in vector DB for retrieval
    _processor.add_articles(articles)

    return json.dumps({
        "status": "success",
        "count": len(articles),
        "articles": [
            {
                "title": a["title"],
                "text": a["text"][:600],
                "source": a["source"],
                "url": a["url"],
                "date": a["date"],
                "confidence": a["confidence"],
            }
            for a in articles
        ],
    }, indent=2)


@tool
def search_knowledge_base(query: str, top_k: int = 6) -> str:
    """
    Search the local vector database of previously scraped transfer articles.
    Use this BEFORE scraping to check if you already have relevant information.
    Faster than live scraping.

    Args:
        query: The search query (player name, club, transfer topic).
        top_k: Number of results to return (default 6, max 10).

    Returns:
        JSON string with relevant article chunks ranked by relevance.
    """
    top_k = min(max(1, top_k), 10)
    chunks = _processor.retrieve(query=query, top_k=top_k)

    if not chunks:
        return json.dumps({
            "status": "empty",
            "message": "No articles in knowledge base yet. Use scrape_transfer_news first.",
            "chunks": [],
        })

    return json.dumps({
        "status": "success",
        "count": len(chunks),
        "chunks": [
            {
                "title": c["title"],
                "text": c["text"][:500],
                "source": c["source"],
                "url": c["url"],
                "date": c["date"],
                "confidence": c["confidence"],
                "relevance_score": c["relevance_score"],
            }
            for c in chunks
        ],
    }, indent=2)


@tool
def assess_transfer_confidence(text: str) -> str:
    """
    Analyse a piece of transfer news text and return a confidence score (1-5)
    based on the language used.

    Score guide:
      5 = HERE WE GO / medical / contract signed / confirmed
      4 = agreement reached / fee agreed / personal terms agreed
      3 = talks ongoing / in talks / bid submitted
      2 = interest / monitoring / scouted
      1 = unverified rumour

    Args:
        text: The transfer news text to analyse.

    Returns:
        JSON with confidence score and label.
    """
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["here we go", "medical", "contract signed", "official", "confirmed", "done deal"]):
        score = 5
    elif any(kw in text_lower for kw in ["agreement reached", "personal terms agreed", "fee agreed", "deal agreed"]):
        score = 4
    elif any(kw in text_lower for kw in ["negotiations", "talks ongoing", "in talks", "bid submitted", "offer made"]):
        score = 3
    elif any(kw in text_lower for kw in ["interest", "monitoring", "scouted", "considering", "target"]):
        score = 2
    else:
        score = 1

    return json.dumps({
        "confidence": score,
        "label": CONFIDENCE_LABELS[score],
    })


# ── Tool registry ──────────────────────────────────────────────────────────
TOOLS = [scrape_transfer_news, search_knowledge_base, assess_transfer_confidence]


# ── LangGraph Agent ────────────────────────────────────────────────────────
class FabrizioAI:
    """
    LangGraph-powered agentic version of FabrizioAI.
    Gemini decides which tools to call, can loop for more info,
    and reasons over results before giving a final answer.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        api_key = os.environ["GEMINI_API_KEY"]

        # Bind tools to Gemini via LangChain
        self._llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.3,
            convert_system_message_to_human=True,  # Required for Gemini
        ).bind_tools(TOOLS)

        # Build and compile the LangGraph
        self._graph = self._build_graph()

    def get_transfer_insight(
        self,
        query: str,
        league_filter: list[str] | None = None,
        confidence_threshold: int = 1,
        use_live_scrape: bool = True,
    ) -> dict:
        """
        Run the agent graph on a user query.
        The agent will autonomously decide whether to search the KB first,
        scrape live data, assess confidence, and loop until satisfied.

        Returns:
            { answer, sources, confidence, confidence_label }
        """
        # Inject league/scrape context into the query
        context_note = ""
        if league_filter and "All" not in league_filter:
            context_note = f"\n[Focus on these leagues: {', '.join(league_filter)}]"
        if not use_live_scrape:
            context_note += "\n[Do NOT call scrape_transfer_news — use knowledge base only]"

        full_query = query + context_note

        initial_state: AgentState = {
            "messages": [
                SystemMessage(content=ROMANO_SYSTEM_PROMPT),
                HumanMessage(content=full_query),
            ],
            "sources_used": [],
            "confidence": 3,
        }

        try:
            final_state = self._graph.invoke(initial_state)
        except Exception as e:
            return {
                "answer": f"⚠️ Agent error: {e}",
                "sources": [],
                "confidence": 0,
                "confidence_label": "Error",
            }

        # Extract the final AI message — Gemini 2.5 may return content as a list
        ai_messages = [m for m in final_state["messages"] if isinstance(m, AIMessage)]
        if not ai_messages:
            return {"answer": "No response generated.", "sources": [], "confidence": 0, "confidence_label": "Error"}

        last_msg = ai_messages[-1]
        raw_answer = last_msg.content

        # Flatten list content to string
        if isinstance(raw_answer, list):
            raw_answer = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in raw_answer
            )

        # Pull sources from ToolMessages
        sources = self._extract_sources(final_state["messages"])

        return self._parse_response(raw_answer, sources)

    # ── Graph definition ───────────────────────────────────────────────────
    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        # Node 1: Gemini reasons + optionally calls tools
        graph.add_node("agent", self._agent_node)

        # Node 2: Executes whichever tool(s) Gemini requested
        graph.add_node("tools", ToolNode(TOOLS))

        graph.add_edge(START, "agent")

        # If Gemini called tools → run them → loop back to agent
        # If Gemini gave a final answer → end
        graph.add_conditional_edges(
            "agent",
            self._should_continue,
            {"continue": "tools", "end": END},
        )

        # After tools execute, always go back to agent to reason over results
        graph.add_edge("tools", "agent")

        return graph.compile()

    def _agent_node(self, state: AgentState) -> AgentState:
        """Invoke Gemini with fast retry on 429 quota errors."""
        import time
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = self._llm.invoke(state["messages"])
                return {"messages": [response]}
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt < max_retries - 1:
                        wait = 10  # short wait, don't block the UI for minutes
                        print(f"[FabrizioAI] Rate limited, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                        time.sleep(wait)
                    else:
                        raise RuntimeError(
                            "⚠️ Gemini quota exhausted. Your free tier daily limit is used up. "
                            "Wait for midnight PT reset, swap your API key, or enable billing at https://aistudio.google.com"
                        )
                else:
                    raise

    @staticmethod
    def _should_continue(state: AgentState) -> Literal["continue", "end"]:
        """Route: if Gemini made tool calls → continue, else → end."""
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "continue"
        return "end"

    # ── Helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def _extract_sources(messages: list) -> list[str]:
        sources = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                try:
                    data = json.loads(msg.content)
                    for key in ("articles", "chunks"):
                        for item in data.get(key, []):
                            src = item.get("source", "")
                            if src and src not in sources:
                                sources.append(src)
                except (json.JSONDecodeError, TypeError):
                    continue
        return sources

    @staticmethod
    def _parse_response(raw_text, fallback_sources: list[str]) -> dict:
        """Parse Gemini's response, handling both string and list content types."""
        # Gemini 2.5 returns content as a list of parts — flatten to string
        if isinstance(raw_text, list):
            raw_text = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in raw_text
            )
        elif not isinstance(raw_text, str):
            raw_text = str(raw_text)

        json_match = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                confidence = int(data.get("confidence", 3))
                return {
                    "answer": data.get("answer", raw_text),
                    "sources": data.get("sources", fallback_sources),
                    "confidence": confidence,
                    "confidence_label": CONFIDENCE_LABELS.get(confidence, "Unknown"),
                }
            except (json.JSONDecodeError, ValueError):
                pass

        return {
            "answer": raw_text,
            "sources": fallback_sources,
            "confidence": 3,
            "confidence_label": CONFIDENCE_LABELS[3],
        }