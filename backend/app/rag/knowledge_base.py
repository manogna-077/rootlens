import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

KNOWLEDGE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "knowledge"


class KnowledgeChunk(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    service: str
    source_type: str
    source_path: str
    text: str
    offset: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeDocument(BaseModel):
    document_id: str
    title: str
    service: str
    source_type: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


def chunk_text(text: str, chunk_size: int = 50, overlap: int = 10) -> List[tuple[str, int]]:
    """
    Chunks text by word count with specified window size and overlap.
    Returns list of (chunk_text, character_offset).
    """
    words = text.split()
    if not words:
        return []
    
    if len(words) <= chunk_size:
        return [(text, 0)]

    chunks = []
    step = chunk_size - overlap
    if step <= 0:
        step = chunk_size

    for i in range(0, len(words), step):
        chunk_words = words[i : i + chunk_size]
        chunk_str = " ".join(chunk_words)
        # Approximate offset
        offset = text.find(chunk_words[0]) if chunk_words else 0
        chunks.append((chunk_str, max(0, offset)))
        if i + chunk_size >= len(words):
            break

    return chunks


class KnowledgeBase:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or KNOWLEDGE_DIR
        self.documents: Dict[str, KnowledgeDocument] = {}
        self.chunks: List[KnowledgeChunk] = []

    def load_documents(self, filename: str, source_type: str) -> List[KnowledgeDocument]:
        file_path = self.data_dir / filename
        if not file_path.exists():
            return []

        loaded = []
        with open(file_path, "r", encoding="utf-8") as f:
            raw_items = json.load(f)

        for item in raw_items:
            doc_id = item.get("document_id", "")
            title = item.get("title", "")
            service = item.get("service", "")
            content = item.get("content", "")
            meta = {k: v for k, v in item.items() if k not in ("document_id", "title", "service", "content", "source_type")}

            doc = KnowledgeDocument(
                document_id=doc_id,
                title=title,
                service=service,
                source_type=source_type,
                content=content,
                metadata=meta,
            )
            self.documents[doc_id] = doc
            loaded.append(doc)

            # Generate chunks
            raw_chunks = chunk_text(content, chunk_size=50, overlap=10)
            for idx, (c_text, offset) in enumerate(raw_chunks):
                chunk_id = f"{doc_id}_chunk_{idx + 1}"
                chunk = KnowledgeChunk(
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    title=title,
                    service=service,
                    source_type=source_type,
                    source_path=str(file_path.relative_to(self.data_dir.parent.parent)),
                    text=c_text,
                    offset=offset,
                    metadata=meta,
                )
                self.chunks.append(chunk)

        return loaded

    def load_all(self):
        self.load_documents("historical_incidents.json", "historical_incident")
        self.load_documents("runbooks.json", "runbook")
