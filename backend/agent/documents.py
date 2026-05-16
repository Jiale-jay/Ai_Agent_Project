from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


SUPPORTED_DOCUMENT_EXTENSIONS = {".txt", ".md"}
DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 150


@dataclass(frozen=True)
class DocumentChunk:
    content: str
    metadata: dict[str, Any]


def decode_document(filename: str, data: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{extension}'. Supported types: {supported}")

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Document must be UTF-8 encoded text.") from exc


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    clean = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not clean:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be greater than or equal to 0 and smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + chunk_size, len(clean))
        candidate = clean[start:end]

        if end < len(clean):
            split_at = max(candidate.rfind("\n\n"), candidate.rfind("\n"), candidate.rfind(". "))
            if split_at >= chunk_size * 0.45:
                end = start + split_at + (2 if candidate[split_at:split_at + 2] == ". " else 0)
                candidate = clean[start:end]

        chunk = candidate.strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(clean):
            break
        start = max(0, end - overlap)

    return chunks


def build_document_chunks(
    filename: str,
    text: str,
    tags: list[str] | None = None,
    source: str = "document_upload",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    uploaded_at = datetime.utcnow().isoformat()
    raw_chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    return [
        DocumentChunk(
            content=content,
            metadata={
                "source": source,
                "filename": filename,
                "chunk_index": index,
                "page": None,
                "uploaded_at": uploaded_at,
                "tags": tags or [],
            },
        )
        for index, content in enumerate(raw_chunks, start=1)
    ]
