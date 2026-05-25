import sys
from types import SimpleNamespace

import pytest

from agent.documents import DocumentPage, build_document_chunks, chunk_text, decode_document, decode_document_pages


def test_chunk_text_returns_single_short_chunk():
    chunks = chunk_text("Expense claims require approval.", chunk_size=100, overlap=10)

    assert chunks == ["Expense claims require approval."]


def test_chunk_text_splits_with_overlap():
    text = "A" * 80 + " " + "B" * 80 + " " + "C" * 80

    chunks = chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) == 3
    assert chunks[0].endswith("B" * 19)
    assert chunks[1].startswith("B" * 20)


def test_chunk_text_empty_input_returns_no_chunks():
    assert chunk_text(" \n\n ") == []


def test_build_document_chunks_adds_enterprise_metadata():
    chunks = build_document_chunks(
        "expense-policy.md",
        "Expense claims over EUR 1,000 require finance review.",
        ["policy", "finance"],
    )

    assert len(chunks) == 1
    assert chunks[0].metadata["source"] == "document_upload"
    assert chunks[0].metadata["document_id"]
    assert chunks[0].metadata["filename"] == "expense-policy.md"
    assert chunks[0].metadata["chunk_index"] == 1
    assert chunks[0].metadata["page"] is None
    assert chunks[0].metadata["tags"] == ["policy", "finance"]
    assert chunks[0].metadata["uploaded_at"]


def test_build_document_chunks_preserves_pdf_page_numbers():
    chunks = build_document_chunks(
        "handbook.pdf",
        [DocumentPage("Page one policy.", page=1), DocumentPage("Page two policy.", page=2)],
        ["policy"],
        document_id="doc-123",
    )

    assert [chunk.metadata["page"] for chunk in chunks] == [1, 2]
    assert {chunk.metadata["document_id"] for chunk in chunks} == {"doc-123"}


def test_decode_pdf_document_extracts_text_pages(monkeypatch):
    class FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class FakePdfReader:
        def __init__(self, _stream):
            self.pages = [FakePage("Policy page 1"), FakePage("   "), FakePage("Policy page 3")]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakePdfReader))

    pages = decode_document_pages("policy.pdf", b"%PDF-1.4")

    assert [page.text for page in pages] == ["Policy page 1", "Policy page 3"]
    assert [page.page for page in pages] == [1, 3]
    assert decode_document("policy.pdf", b"%PDF-1.4") == "Policy page 1\n\nPolicy page 3"


def test_decode_pdf_document_rejects_empty_text(monkeypatch):
    class FakePage:
        def extract_text(self):
            return ""

    class FakePdfReader:
        def __init__(self, _stream):
            self.pages = [FakePage()]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakePdfReader))

    with pytest.raises(ValueError, match="no extractable text"):
        decode_document_pages("policy.pdf", b"%PDF-1.4")


def test_decode_document_rejects_unsupported_file_type():
    with pytest.raises(ValueError, match="Unsupported file type"):
        decode_document("policy.docx", b"not supported yet")
