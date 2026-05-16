import pytest

from agent.documents import build_document_chunks, chunk_text, decode_document


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
    assert chunks[0].metadata["filename"] == "expense-policy.md"
    assert chunks[0].metadata["chunk_index"] == 1
    assert chunks[0].metadata["tags"] == ["policy", "finance"]
    assert chunks[0].metadata["uploaded_at"]


def test_decode_document_rejects_unsupported_file_type():
    with pytest.raises(ValueError, match="Unsupported file type"):
        decode_document("policy.pdf", b"not supported yet")
