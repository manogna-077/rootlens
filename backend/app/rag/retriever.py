import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.rag.knowledge_base import KnowledgeChunk, KnowledgeBase


class RetrievalResult(BaseModel):
    document_id: str
    chunk_id: str
    title: str
    service: str
    source_type: str
    source_path: str
    score: float
    snippet: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_provenance(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_path": self.source_path,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "title": self.title,
            "service": self.service,
            "score": round(self.score, 4),
            "snippet": self.snippet,
        }


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercased alphanumeric terms."""
    return re.findall(r"\b\w+\b", text.lower())


class LexicalRetriever:
    """
    Deterministic Lexical (BM25/TF-IDF) Retriever.
    Indexes KnowledgeChunk objects and ranks them against text queries.
    """

    def __init__(self, knowledge_base: KnowledgeBase, k1: float = 1.5, b: float = 0.75):
        self.kb = knowledge_base
        self.k1 = k1
        self.b = b
        self.chunk_tokens: List[List[str]] = []
        self.doc_freqs: Dict[str, int] = Counter()
        self.avg_dl: float = 0.0
        self._index()

    def _index(self):
        self.chunk_tokens = []
        self.doc_freqs = Counter()
        total_tokens = 0

        for chunk in self.kb.chunks:
            tokens = tokenize(chunk.text + " " + chunk.title + " " + chunk.service)
            self.chunk_tokens.append(tokens)
            total_tokens += len(tokens)
            unique_terms = set(tokens)
            for term in unique_terms:
                self.doc_freqs[term] += 1

        N = len(self.kb.chunks)
        self.avg_dl = (total_tokens / N) if N > 0 else 1.0

    def retrieve(
        self,
        query: str,
        source_type: Optional[str] = None,
        service: Optional[str] = None,
        top_k: int = 3,
        min_score: float = 0.05,
    ) -> List[RetrievalResult]:
        query_tokens = tokenize(query)
        if not query_tokens or not self.kb.chunks:
            return []

        N = len(self.kb.chunks)
        scored_results: List[RetrievalResult] = []

        for idx, chunk in enumerate(self.kb.chunks):
            # Optional source_type filter
            if source_type and chunk.source_type != source_type:
                continue

            # Optional service filter (flexible match: if specified, matches service or empty)
            if service and chunk.service and service.lower() not in chunk.service.lower() and chunk.service.lower() not in service.lower():
                continue

            tokens = self.chunk_tokens[idx]
            doc_len = len(tokens)
            if doc_len == 0:
                continue

            tf_counter = Counter(tokens)
            bm25_score = 0.0

            for term in query_tokens:
                if term not in tf_counter:
                    continue

                tf = tf_counter[term]
                df = self.doc_freqs.get(term, 0)
                # IDF calculation with smoothing
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
                
                num = tf * (self.k1 + 1.0)
                den = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_dl))
                bm25_score += idf * (num / den)

            # Bonus for service or title keyword match
            if service and service.lower() in chunk.service.lower():
                bm25_score += 0.5

            if bm25_score >= min_score:
                res = RetrievalResult(
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    title=chunk.title,
                    service=chunk.service,
                    source_type=chunk.source_type,
                    source_path=chunk.source_path,
                    score=bm25_score,
                    snippet=chunk.text,
                    metadata=chunk.metadata,
                )
                scored_results.append(res)

        # Deterministic tie-breaking by score descending, then chunk_id ascending
        scored_results.sort(key=lambda x: (-x.score, x.chunk_id))

        return scored_results[:top_k]
