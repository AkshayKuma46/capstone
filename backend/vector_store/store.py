"""
store.py — Vector_Store (pure-Python fallback, no ChromaDB required)

Uses numpy cosine similarity instead of ChromaDB.
Works on any machine without a C/Rust compiler.
Embeddings are stored in memory + saved to JSON on disk.
"""

import json
import logging
import time
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    CHROMA_PERSIST_DIR,
    RAG_SIMILARITY_THRESHOLD, RAG_LOW_CONFIDENCE_MIN_RESULTS, RAG_DEFAULT_K
)

logger = logging.getLogger(__name__)

STORE_PATH = CHROMA_PERSIST_DIR / "vector_store.json"


# ── Data Classes ──────────────────────────────────────────────────────────────
@dataclass
class EmbeddingRecord:
    id: str
    type: str
    userId: Optional[str]
    corpusVersion: Optional[str]
    metadata: dict
    similarityScore: float = 0.0
    updatedAt: str = ""


@dataclass
class RetrievalResult:
    records: list
    lowConfidence: bool
    retrievedAt: str


# ── Simple TF-IDF style embedding (no ML model required) ──────────────────────
def _simple_embed(text: str, dim: int = 64) -> list:
    """
    Deterministic hash-based embedding.
    Good enough for keyword matching without any ML dependency.
    """
    import math
    text = text.lower().strip()
    words = text.split()
    vec = [0.0] * dim
    for i, word in enumerate(words):
        h = hash(word) % dim
        vec[h] += 1.0 / (i + 1)
    # Normalize
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _cosine_similarity(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return max(0.0, min(1.0, dot))


def embed_texts(texts: list) -> list:
    return [_simple_embed(t) for t in texts]


def embed_query(query: str) -> list:
    return _simple_embed(query)


# ── Garment text builder ──────────────────────────────────────────────────────
def _garment_to_text(g: dict) -> str:
    parts = [
        g.get("name", ""),
        g.get("category", ""),
        g.get("primaryColor", ""),
        g.get("fabricType", ""),
        g.get("fitType", "") or "",
        g.get("styleTag", "") or "",
        " ".join(g.get("occasionTags", [])),
    ]
    return " ".join(p for p in parts if p).strip()


def _rule_to_text(r: dict) -> str:
    return r.get("description", "") or r.get("ruleText", str(r))


# ── Vector Store ──────────────────────────────────────────────────────────────
class VectorStore:
    """Pure-Python in-memory vector store with JSON persistence."""

    def __init__(self):
        self._garments: dict = {}   # id → {vector, metadata, document}
        self._rules: dict = {}      # id → {vector, metadata, document}
        self._load()

    def _load(self):
        if STORE_PATH.exists():
            try:
                data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
                self._garments = data.get("garments", {})
                self._rules = data.get("rules", {})
                logger.info(f"[VectorStore] Loaded {len(self._garments)} garments, {len(self._rules)} rules")
            except Exception as e:
                logger.warning(f"[VectorStore] Could not load store: {e}")

    def _save(self):
        try:
            CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
            STORE_PATH.write_text(
                json.dumps({"garments": self._garments, "rules": self._rules}),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"[VectorStore] Save failed: {e}")

    # ── Garment CRUD ──────────────────────────────────────────────────────────
    def add_garment(self, garment: dict, user_id: str) -> str:
        start = time.time()
        gid = garment["garmentId"]
        text = _garment_to_text(garment)
        self._garments[gid] = {
            "vector": embed_query(text),
            "document": text,
            "metadata": {
                "type": "garment",
                "userId": user_id,
                "name": garment.get("name", ""),
                "category": garment.get("category", ""),
                "primaryColor": garment.get("primaryColor", ""),
                "fabricType": garment.get("fabricType", ""),
                "occasionTags": ",".join(garment.get("occasionTags", [])),
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            }
        }
        self._save()
        logger.info(f"[VectorStore] Garment {gid} added in {time.time()-start:.2f}s")
        return gid

    def update_garment(self, garment: dict, user_id: str) -> str:
        return self.add_garment(garment, user_id)

    def delete_garment(self, garment_id: str):
        self._garments.pop(garment_id, None)
        self._save()
        logger.info(f"[VectorStore] Garment {garment_id} deleted")

    # ── Rule Embeddings ───────────────────────────────────────────────────────
    def add_rules(self, rules: list, corpus_version: str) -> dict:
        start = time.time()
        success = 0
        failed = 0
        texts = [_rule_to_text(r) for r in rules]
        vectors = embed_texts(texts)
        for rule, text, vector in zip(rules, texts, vectors):
            rid = rule.get("ruleId") or rule.get("id", "unknown")
            key = f"{corpus_version}::{rid}"
            try:
                self._rules[key] = {
                    "vector": vector,
                    "document": text,
                    "metadata": {
                        "type": "rule",
                        "corpusVersion": corpus_version,
                        "ruleType": rule.get("ruleType", ""),
                        "description": text,
                        "updatedAt": datetime.now(timezone.utc).isoformat(),
                    }
                }
                success += 1
            except Exception as e:
                logger.error(f"[VectorStore] Rule {rid} failed: {e}")
                failed += 1
        self._save()
        elapsed = time.time() - start
        logger.info(f"[VectorStore] Embedded {success}/{len(rules)} rules in {elapsed:.1f}s")
        return {"success": success, "failed": failed, "total": len(rules)}

    # ── Retrieval ─────────────────────────────────────────────────────────────
    def retrieve(
        self,
        query: str,
        user_id: str,
        k: int = RAG_DEFAULT_K,
        filter_type: Optional[str] = None,
        occasion_tags: Optional[list] = None,
    ) -> RetrievalResult:
        qvec = embed_query(query)
        records = []
        retrieved_at = datetime.now(timezone.utc).isoformat()

        # Garments
        if filter_type in (None, "garment", "both"):
            for gid, entry in self._garments.items():
                if entry["metadata"].get("userId") != user_id:
                    continue
                sim = _cosine_similarity(qvec, entry["vector"])
                records.append(EmbeddingRecord(
                    id=gid, type="garment", userId=user_id,
                    corpusVersion=None, metadata=entry["metadata"],
                    similarityScore=round(sim, 4),
                    updatedAt=entry["metadata"].get("updatedAt", ""),
                ))

        # Rules
        if filter_type in (None, "rule", "both"):
            for rid, entry in self._rules.items():
                sim = _cosine_similarity(qvec, entry["vector"])
                meta = entry["metadata"].copy()
                meta["document"] = entry.get("document", "")
                meta["description"] = entry.get("document", "")
                records.append(EmbeddingRecord(
                    id=rid, type="rule", userId=None,
                    corpusVersion=meta.get("corpusVersion"),
                    metadata=meta,
                    similarityScore=round(sim, 4),
                    updatedAt=meta.get("updatedAt", ""),
                ))

        records.sort(key=lambda r: r.similarityScore, reverse=True)
        top_records = records[:k]
        above = sum(1 for r in top_records if r.similarityScore >= RAG_SIMILARITY_THRESHOLD)
        low_confidence = above < RAG_LOW_CONFIDENCE_MIN_RESULTS

        return RetrievalResult(
            records=top_records,
            lowConfidence=low_confidence,
            retrievedAt=retrieved_at,
        )

    def garment_count(self, user_id: str) -> int:
        return sum(1 for e in self._garments.values() if e["metadata"].get("userId") == user_id)


# ── Singleton ──────────────────────────────────────────────────────────────────
_vector_store: Optional[VectorStore] = None

def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
