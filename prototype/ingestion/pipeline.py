"""
ingestion/pipeline.py — Ingestion Orchestration

Loads raw documents from mock_data/contracts.json, chunks them,
and loads them into the multi-tenant vector store.

Production equivalent on GCP:
  ┌──────────────────────────────────────────────────────────────┐
  │  Google Drive (per-region)                                    │
  │    ↓  Drive API webhook → Pub/Sub topic                       │
  │  Cloud Storage (staging bucket, per-region prefix)            │
  │    ↓  Cloud Run Job triggered by Pub/Sub                      │
  │  Document AI (OCR for scanned PDFs)                           │
  │    ↓                                                          │
  │  Chunker + Embedder (this module, running in Cloud Run)       │
  │    ↓                                                          │
  │  Vertex AI Vector Search (per-region index)                   │
  │  Firestore (document registry for versioning / soft-delete)   │
  └──────────────────────────────────────────────────────────────┘

Versioning & Sync Strategy:
  • Every document ingested is stamped with a (doc_id, version) pair
    stored in Firestore (document registry).
  • When a Drive file changes, the pipeline fetches the new version,
    re-chunks it, upserts new chunks by chunk_id, and soft-deletes
    orphaned chunks from the previous version using a tombstone flag.
  • Deletions from Drive are detected via the Drive API's `changes.list`
    endpoint, which sets a tombstone in Firestore and removes chunks
    from the vector store.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.chunker import chunk_all_documents
from retrieval.vector_store import MultiTenantVectorStore


CONTRACTS_PATH = Path(__file__).parent.parent / "mock_data" / "contracts.json"


def load_documents(path: Path = CONTRACTS_PATH) -> list[dict]:
    """Load all mock contract documents from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_ingestion_pipeline(store: MultiTenantVectorStore, verbose: bool = True) -> int:
    """
    Full ingestion pipeline:
      1. Load raw documents
      2. Chunk each document
      3. Upsert chunks into the multi-tenant vector store

    Returns the total number of chunks ingested.
    """
    if verbose:
        print("── Ingestion Pipeline ──────────────────────────────────")

    # Step 1: Load
    documents = load_documents()
    if verbose:
        print(f"  [1/3] Loaded {len(documents)} documents from mock_data/contracts.json")

    # Step 2: Chunk
    all_chunks = chunk_all_documents(documents)
    if verbose:
        print(f"  [2/3] Chunked into {len(all_chunks)} chunks "
              f"(chunk_size={120} words, overlap={20} words)")

    # Step 3: Ingest into vector store (per-region collections)
    store.upsert_chunks(all_chunks)
    if verbose:
        region_counts: dict[str, int] = {}
        for chunk in all_chunks:
            region_counts[chunk["region"]] = region_counts.get(chunk["region"], 0) + 1
        for region, count in sorted(region_counts.items()):
            print(f"         → {region:6s}: {count} chunks")
        print(f"  [3/3] All chunks indexed in ChromaDB (in-memory)\n")

    return len(all_chunks)
