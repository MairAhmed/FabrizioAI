"""
processor.py – Vector database builder and retriever for transfer articles
Uses ChromaDB (local, persistent) + Gemini embeddings for semantic search.
"""
import os
import hashlib
import json
from pathlib import Path

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

CHROMA_PERSIST_DIR = str(Path(__file__).resolve().parents[1] / ".chroma_db")
COLLECTION_NAME = "transfer_articles"
EMBEDDING_MODEL = "models/text-embedding-004"


class LangChainEmbeddingFunction(EmbeddingFunction):
    """
    Wraps LangChain's GoogleGenerativeAIEmbeddings so ChromaDB can use it.
    This avoids needing the legacy google-generativeai package directly.
    """
    def __init__(self, api_key: str):
        self._embedder = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=api_key,
        )

    def __call__(self, input: Documents) -> Embeddings:
        return self._embedder.embed_documents(list(input))


class TransferProcessor:
    """
    Wraps ChromaDB to provide:
      - add_articles(): embed + store new articles
      - retrieve(): semantic search over stored articles
      - clear(): wipe the collection
    """

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY", "")

        self._embedding_fn = LangChainEmbeddingFunction(api_key=api_key)

        self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    # ── Public methods ─────────────────────────────────────────────────────
    def add_articles(self, articles: list[dict]) -> int:
        """
        Embeds and stores articles. Deduplicates by content hash.

        Returns:
            Number of newly added articles.
        """
        new_count = 0
        for article in articles:
            doc_text = self._build_document_text(article)
            doc_id = self._hash_id(article.get("url", "") + article.get("title", ""))

            # Skip if already stored
            existing = self._collection.get(ids=[doc_id])
            if existing["ids"]:
                continue

            metadata = {
                "title": article.get("title", "")[:256],  # Chroma metadata cap
                "source": article.get("source", "Unknown"),
                "url": article.get("url", ""),
                "date": article.get("date", ""),
                "confidence": int(article.get("confidence", 1)),
                "league_tags": json.dumps(article.get("league_tags", ["All"])),
            }

            self._collection.add(
                documents=[doc_text],
                metadatas=[metadata],
                ids=[doc_id],
            )
            new_count += 1

        return new_count

    def retrieve(self, query: str, top_k: int = 6) -> list[dict]:
        """
        Semantic search over stored articles.

        Returns:
            List of chunk dicts with title, text, source, url, date, confidence
        """
        count = self._collection.count()
        if count == 0:
            return []

        actual_k = min(top_k, count)
        results = self._collection.query(
            query_texts=[query],
            n_results=actual_k,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "text": doc,
                "title": meta.get("title", ""),
                "source": meta.get("source", ""),
                "url": meta.get("url", ""),
                "date": meta.get("date", ""),
                "confidence": meta.get("confidence", 1),
                "relevance_score": round(1 - dist, 3),  # cosine similarity
            })

        # Sort by relevance descending
        chunks.sort(key=lambda x: x["relevance_score"], reverse=True)
        return chunks

    def clear(self) -> None:
        """Wipe all stored articles (useful for testing)."""
        self._client.delete_collection(COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def stats(self) -> dict:
        """Return basic stats about the collection."""
        return {
            "total_articles": self._collection.count(),
            "persist_dir": CHROMA_PERSIST_DIR,
        }

    # ── Helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def _build_document_text(article: dict) -> str:
        """Combine title + text into a single string for embedding."""
        title = article.get("title", "")
        text = article.get("text", "")
        source = article.get("source", "")
        date = article.get("date", "")
        return f"[{source} | {date}]\n{title}\n{text}".strip()

    @staticmethod
    def _hash_id(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()[:32]