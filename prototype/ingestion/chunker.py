"""
ingestion/chunker.py — Document Chunking

Splits raw contract documents into overlapping word-based chunks,
preserving key metadata on every chunk so vector search results
are always traceable back to their source document and region.

Production equivalent on GCP:
  • This logic would run inside a Cloud Run Job triggered by
    a Pub/Sub notification when a new file lands in Cloud Storage
    (after being fetched from Google Drive and OCR'd by Document AI).
"""

from typing import Any
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS


def chunk_document(
    doc: dict[str, Any],
    chunk_size: int = CHUNK_SIZE_WORDS,
    overlap: int = CHUNK_OVERLAP_WORDS,
) -> list[dict[str, Any]]:
    """
    Split a document dict into overlapping word-based chunks.

    Args:
        doc:        A single document dict loaded from contracts.json.
        chunk_size: Max words per chunk.
        overlap:    Words shared between adjacent chunks (sliding window).

    Returns:
        List of chunk dicts, each carrying the original document metadata
        plus a unique chunk_id and the chunk text itself.

    Chunking Strategy Notes:
        • Word-based sliding window keeps implementation simple and
          dependency-free for this prototype.
        • In production we use semantic chunking (split at sentence /
          paragraph boundaries) with spaCy or LangChain's
          RecursiveCharacterTextSplitter so clause boundaries are not cut.
        • Overlap ensures important clauses that straddle a boundary are
          captured in at least one chunk.
    """
    content: str = doc.get("content", "")
    words = content.split()
    chunks: list[dict[str, Any]] = []

    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_text = " ".join(words[start:end])

        # Build a flat metadata dict — ChromaDB requires all values to be
        # str, int, float, or bool (no lists or nested dicts).
        chunk: dict[str, Any] = {
            # Identity
            "chunk_id": f"{doc['doc_id']}_chunk_{len(chunks)}",
            "doc_id": doc["doc_id"],
            "chunk_index": len(chunks),
            # Tenancy & routing
            "region": doc["region"],
            "subsidiary": doc["subsidiary"],
            # Document metadata
            "doc_type": doc["doc_type"],
            "title": doc["title"],
            "supplier": doc.get("supplier", doc.get("landlord", doc.get("issuer", ""))),
            "expiry_date": doc.get("expiry_date", ""),
            "effective_date": doc.get("effective_date", ""),
            "liability_amount": doc.get("liability_amount", 0),
            "tags": ", ".join(doc.get("tags", [])),   # serialised for ChromaDB
            "version": doc.get("version", 1),
            "last_modified": doc.get("last_modified", ""),
            # Chunk content
            "text": chunk_text,
        }
        chunks.append(chunk)

        if end == len(words):
            break
        start = end - overlap  # slide back by overlap for next chunk

    return chunks


def chunk_all_documents(
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Chunk an entire list of documents.

    Returns a flat list of all chunks across all documents.
    """
    all_chunks: list[dict[str, Any]] = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc))
    return all_chunks
