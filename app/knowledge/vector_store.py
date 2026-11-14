"""ChromaDB vector store over the policy documents.

RAG in three steps:
  1. Split each document into chunks (one chunk per '## ' section).
  2. Embed each chunk and store it in ChromaDB.
  3. At question time, embed the question and return the closest chunks.

The index is saved to disk (settings.chroma_dir), so documents are embedded
once. A hash of the documents is stored with the index; if you edit
documents.py the index is rebuilt automatically on the next search.
"""

import hashlib
import logging
import threading
from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.knowledge.documents import KNOWLEDGE_BASE
from app.llm import get_embeddings

log = logging.getLogger(__name__)

COLLECTION_NAME = "insurance_kb"
MIN_CHUNK_CHARS = 50  # Skip header-only fragments


def chunk_documents(documents: dict[str, str] = KNOWLEDGE_BASE) -> list[dict]:
    """Split documents on '## ' headings → [{"id", "text", "source"}, ...]."""
    chunks = []
    for source, text in documents.items():
        for section in text.split("\n## "):
            section = section.strip()
            if len(section) >= MIN_CHUNK_CHARS:
                chunks.append({"id": f"chunk_{len(chunks)}", "text": section, "source": source})
    return chunks


class PolicyVectorStore:
    """Lazily builds (or reuses) the Chroma collection on first search."""

    def __init__(self, persist_dir, embedding_model_name: str):
        self._persist_dir = persist_dir
        self._embedding_model_name = embedding_model_name
        self._collection = None
        self._lock = threading.Lock()  # FastAPI may call us from several threads

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        collection = self._get_collection()
        query_vector = get_embeddings().embed_query(query)
        results = collection.query(query_embeddings=[query_vector], n_results=max(1, min(top_k, 8)))
        return [
            {"content": doc, "source": (meta or {}).get("source", "unknown")}
            for doc, meta in zip(results["documents"][0], results["metadatas"][0])
        ]

    def warm_up(self) -> None:
        """Build/load the index ahead of the first question."""
        self._get_collection()

    # ─── internals ────────────────────────────────────────────────────
    def _documents_hash(self) -> str:
        h = hashlib.sha256(self._embedding_model_name.encode())
        for name in sorted(KNOWLEDGE_BASE):
            h.update(name.encode() + KNOWLEDGE_BASE[name].encode())
        return h.hexdigest()[:16]

    def _get_collection(self):
        with self._lock:
            if self._collection is None:
                self._collection = self._load_or_build()
            return self._collection

    def _load_or_build(self):
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(
            path=str(self._persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        docs_hash = self._documents_hash()

        existing = next((c for c in client.list_collections() if c.name == COLLECTION_NAME), None)
        if existing is not None:
            collection = client.get_collection(COLLECTION_NAME, embedding_function=None)
            if (collection.metadata or {}).get("docs_hash") == docs_hash and collection.count() > 0:
                log.info("Using existing knowledge base index (%d chunks)", collection.count())
                return collection
            log.info("Knowledge base changed — rebuilding index")
            client.delete_collection(COLLECTION_NAME)

        collection = client.create_collection(
            COLLECTION_NAME, embedding_function=None, metadata={"docs_hash": docs_hash}
        )
        chunks = chunk_documents()
        vectors = get_embeddings().embed_documents([c["text"] for c in chunks])  # one batched call
        collection.add(
            ids=[c["id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[{"source": c["source"]} for c in chunks],
            embeddings=vectors,
        )
        log.info("Indexed %d chunks into ChromaDB", collection.count())
        return collection


@lru_cache
def get_vector_store() -> PolicyVectorStore:
    settings = get_settings()
    return PolicyVectorStore(settings.chroma_dir, settings.embedding_model)
