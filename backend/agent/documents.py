from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4


SUPPORTED_DOCUMENT_EXTENSIONS = {".txt", ".md", ".pdf"}
DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 150


@dataclass(frozen=True)
class DocumentChunk:
    content: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DocumentPage:
    text: str
    page: int | None = None


def decode_document(filename: str, data: bytes) -> str:
    pages = decode_document_pages(filename, data)
    return "\n\n".join(page.text for page in pages)


def decode_document_pages(filename: str, data: bytes) -> list[DocumentPage]:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{extension}'. Supported types: {supported}")

    if extension == ".pdf":
        return _decode_pdf_pages(data)

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Document must be UTF-8 encoded text.") from exc

    if not text.strip():
        raise ValueError("Uploaded document contains no text.")
    return [DocumentPage(text=text, page=None)]


def _decode_pdf_pages(data: bytes) -> list[DocumentPage]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
    except Exception as exc:
        raise ValueError("PDF could not be parsed.") from exc

    pages: list[DocumentPage] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(DocumentPage(text=text, page=index))

    if not pages:
        raise ValueError("PDF contains no extractable text.")
    return pages


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
    text: str | list[DocumentPage],
    tags: list[str] | None = None,
    document_id: str | None = None,
    source: str = "document_upload",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    uploaded_at = datetime.utcnow().isoformat()
    pages = text if isinstance(text, list) else [DocumentPage(text=text, page=None)]
    resolved_document_id = document_id or str(uuid4())
    chunks: list[DocumentChunk] = []

    for page in pages:
        for content in chunk_text(page.text, chunk_size=chunk_size, overlap=overlap):
            chunks.append(
                DocumentChunk(
                    content=content,
                    metadata={
                        "source": source,
                        "document_id": resolved_document_id,
                        "filename": filename,
                        "chunk_index": len(chunks) + 1,
                        "page": page.page,
                        "uploaded_at": uploaded_at,
                        "tags": tags or [],
                    },
                )
            )

    return chunks
