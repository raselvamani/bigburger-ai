# BigBurger AI - Prototype

A working Python prototype of the **multi-tenant document intelligence platform** for managing contracts across 4 regional subsidiaries.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the prototype with 7 demo scenarios
python main.py

# Run validation tests (optional)
python test_synthetic_data.py
```

---

## 📊 High-Level Flow Diagram

The prototype demonstrates two main flows:

### 1. **Data Ingestion Pipeline** (Setup)
```
                          ┌─────────────────────────────────────┐
                          │   Raw Documents (JSON)              │
                          │   - 40 contracts across 4 regions    │
                          │   - Vendor contracts, leases, etc    │
                          └──────────────┬──────────────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────────┐
                          │   Document Chunker                  │
                          │   - Word-based sliding window       │
                          │   - 120 words/chunk, 20 word overlap│
                          │   - ~200+ total chunks              │
                          └──────────────┬──────────────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────────┐
                          │   Embed Chunks (MiniLM-L6-v2)      │
                          │   - ONNX embeddings (bundled)       │
                          │   - 384-dimensional vectors        │
                          └──────────────┬──────────────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────────┐
                          │   Multi-Tenant Vector Store         │
                          │   (ChromaDB in-memory)              │
                          │   - Per-region collections (NORTH,  │
                          │     SOUTH, EAST, WEST)              │
                          │   - Tenant isolation at storage     │
                          └─────────────────────────────────────┘
```

### 2. **Query Execution Pipeline** (Runtime)

```
                          ┌─────────────────────────────────────┐
                          │   User Query                        │
                          │   "Show me all beef contracts"      │
                          └──────────────┬──────────────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────────┐
                          │   Orchestrator Agent                │
                          │   Entry point for all queries       │
                          └──────────────┬──────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
        ┌──────────────────────┐┌──────────────────────┐┌──────────────────────┐
        │   1. Authenticate    ││   2. Classify Query  ││   3. Authorize Access │
        │   - Validate JWT     ││   - LOCAL vs CROSS-  ││   - Check RBAC       │
        │   - Extract user_id  ││     REGIONAL?        ││   - Allowed regions? │
        │   - Resolve role     ││   - Keyword patterns ││                       │
        └──────────────────────┘└──────────────────────┘└──────────────────────┘
                    │                    │                    │
                    └────────────────────┼────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 │                                               │
        ┌────────▼──────────────────┐              ┌────────────▼──────────────┐
        │  LOCAL QUERY             │              │  CROSS-REGIONAL QUERY    │
        │  (Single region)         │              │  (Multiple regions)      │
        │                          │              │                         │
        │  ① Delegate to           │              │  ① Fan-out to all       │
        │     RegionalAgent        │              │     authorized           │
        │  ② Search single region  │              │     RegionalAgents       │
        │  ③ Return results        │              │  ② Execute in parallel   │
        │                          │              │  ③ Collect all results   │
        └──────────┬───────────────┘              └────────────┬──────────────┘
                   │                                            │
                   └────────────────┬─────────────────────────┬─┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
        ┌──────────────────┐┌──────────────────┐┌──────────────────┐
        │  North Region    ││  South Region    ││  East Region     │
        │  ┌────────────┐  ││  ┌────────────┐  ││  ┌────────────┐  │
        │  │ Vector     │  ││  │ Vector     │  ││  │ Vector     │  │
        │  │ Search     │  ││  │ Search     │  ││  │ Search     │  │
        │  │ (RBAC)     │  ││  │ (RBAC)     │  ││  │ (RBAC)     │  │
        │  └────┬───────┘  ││  └────┬───────┘  ││  └────┬───────┘  │
        │       │          ││       │          ││       │          │
        │       ▼          ││       ▼          ││       ▼          │
        │  Top-K Chunks   ││  Top-K Chunks   ││  Top-K Chunks   │
        │  + Metadata     ││  + Metadata     ││  + Metadata     │
        │                 ││                 ││                 │
        │  ┌────────────┐  ││  ┌────────────┐  ││  ┌────────────┐  │
        │  │ Regional   │  ││  │ Regional   │  ││  │ Regional   │  │
        │  │ Agent      │  ││  │ Agent      │  ││  │ Agent      │  │
        │  │ Response   │  ││  │ Response   │  ││  │ Response   │  │
        │  └──────┬─────┘  ││  └──────┬─────┘  ││  └──────┬─────┘  │
        │         │        ││         │        ││         │        │
        └─────────┼────────┘└─────────┼────────┘└─────────┼────────┘
                  │                   │                   │
                  └───────────────────┼───────────────────┘
                                      │
                                      ▼
                      ┌────────────────────────────────────┐
                      │   Synthesis Agent                 │
                      │   - Aggregate results from all    │
                      │     regions (if cross-regional)  │
                      │   - Identify conflicts/patterns   │
                      │   - Mock LLM synthesis            │
                      └────────────────┬───────────────────┘
                                       │
                                       ▼
                      ┌────────────────────────────────────┐
                      │   Final Answer                     │
                      │   - Structured response            │
                      │   - Sources & metadata             │
                      │   - RBAC-enforced visibility       │
                      └────────────────────────────────────┘
```

---

## 🏗️ Architecture Components

### **Core Modules**

| Module | Purpose | Key Classes |
|--------|---------|------------|
| **`ingestion/`** | Load & chunk documents | `chunk_document()`, `chunk_all_documents()` |
| **`retrieval/`** | Multi-tenant vector search | `MultiTenantVectorStore`, `MultiTenantRetriever` |
| **`agents/`** | Query orchestration & RBAC | `OrchestratorAgent`, `RegionalAgent` |
| **`config.py`** | Users, roles, regions, permissions | `UserToken`, `RBAC_MATRIX`, region definitions |

### **Data Flow**

1. **Ingestion**
   - Load mock contracts from `mock_data/contracts.json` (or `synthetic_contracts.json`)
   - Chunk each document using sliding-window algorithm
   - Embed chunks using ONNX MiniLM-L6-v2 (384-dim vectors)
   - Upsert into ChromaDB per-region collections

2. **Query Execution**
   - User submits query via `OrchestratorAgent.handle_query(user_id, query_text)`
   - Orchestrator authenticates user & classifies query (LOCAL vs CROSS-REGIONAL)
   - For LOCAL queries: invoke single `RegionalAgent`
   - For CROSS-REGIONAL queries: fan-out to all authorized `RegionalAgent`s (parallel)
   - Collect results from all regions & synthesize final answer
   - Return structured response with sources

3. **Security (RBAC)**
   - Every query enforced against `RBAC_MATRIX` in `config.py`
   - `authenticate()` validates JWT and returns `UserToken`
   - `authorize_region_access()` checks if user may query a region
   - Unauthorized regions are silently skipped (no error leak)

---

## 🎮 Demo Scenarios

Run `python main.py` to execute 7 live demo scenarios:

| Demo | User | Role | Query Type | Tests |
|------|------|------|-----------|-------|
| 1 | `alice_north` | Regional Manager (North) | LOCAL | Basic RBAC & local search |
| 2 | `eve_auditor` | Global Auditor | CROSS-REGIONAL | Cross-region synthesis, conflict detection |
| 3 | `bob_south` | Regional Manager (South) | Blocked | RBAC enforcement (forbidden cross-region) |
| 4 | `charlie_east` | Regional Manager (East) | Blocked | RBAC enforcement (access denied) |
| 5 | `frank_hq` | HQ Executive | CROSS-REGIONAL | Aggregated financial reporting |
| 6 | `frank_hq` | HQ Executive | CROSS-REGIONAL | Compliance deadline tracking |
| 7 | `frank_hq` | HQ Executive | CROSS-REGIONAL | National vs regional conflict detection |

---

## 🔐 RBAC Model

### Roles

| Role | Regions | Query Types | Use Case |
|------|---------|------------|----------|
| **Regional Manager** | Single region | LOCAL only | Day-to-day regional operations |
| **Global Auditor** | All regions | LOCAL + CROSS-REGIONAL | Enterprise-wide compliance & audits |
| **HQ Executive** | All regions | LOCAL + CROSS-REGIONAL | Strategic planning & reporting |

### Users (in `config.py`)

```python
MOCK_USERS = {
    "alice_north": {"role": "regional_manager", "region": "north"},
    "bob_south": {"role": "regional_manager", "region": "south"},
    "charlie_east": {"role": "regional_manager", "region": "east"},
    "dave_west": {"role": "regional_manager", "region": "west"},
    "eve_auditor": {"role": "global_auditor", "regions": ["north", "south", "east", "west"]},
    "frank_hq": {"role": "hq_executive", "regions": ["north", "south", "east", "west"]},
}
```

---

## 📁 Data Structure

### Mock Data Format

Each document in `mock_data/contracts.json`:

```json
{
  "doc_id": "contract_north_fizzcobev_001",
  "region": "north",
  "title": "FizzCo Beverages - Exclusive Supply Agreement",
  "document_type": "contract",
  "content": "This agreement establishes...",
  "metadata": {
    "expiry_date": "2027-06-30",
    "liability": "$750,000",
    "status": "active"
  }
}
```

### Chunked Format

Each chunk in the vector store:

```json
{
  "chunk_id": "contract_north_fizzcobev_001__chunk_0",
  "doc_id": "contract_north_fizzcobev_001",
  "region": "north",
  "text": "This agreement establishes an exclusive supply relationship...",
  "doc_title": "FizzCo Beverages - Exclusive Supply Agreement",
  "metadata_str": "{\"expiry_date\": \"2027-06-30\", ...}"
}
```

---

## 🛠️ Configuration

Edit `config.py` to customize:

- **Regions**: Add/remove regions
- **Users & Roles**: Define new users or role permissions
- **Chunking**: `CHUNK_SIZE_WORDS`, `CHUNK_OVERLAP_WORDS`
- **Retrieval**: `TOP_K_RESULTS` per region
- **RBAC Matrix**: Define which roles can access which regions

---

## 📊 Vector Store

The prototype uses **ChromaDB** with per-region collections:

```
ChromaDB (in-memory)
├── north          (e.g., 50 chunks)
├── south          (e.g., 45 chunks)
├── east           (e.g., 48 chunks)
├── west           (e.g., 52 chunks)
└── (Embeddings: ONNX MiniLM-L6-v2, 384-dim)
```

- No external API keys required
- Embeddings bundled with ChromaDB
- Semantic search via cosine similarity

---

## 🧪 Testing

### Run All Tests

```bash
python test_synthetic_data.py --mode all
```

### Test Modes

- `--mode validate` — Validate data structure only
- `--mode load` — Test vector store loading
- `--mode scenarios` — Run 6 automated scenarios
- `--mode all` — Full test suite

---

## 📚 Documentation

- **[SYNTHETIC_DATA_GUIDE.md](../SYNTHETIC_DATA_GUIDE.md)** — Complete data documentation (40 contracts, 8 test scenarios)
- **[QUICK_START.md](../QUICK_START.md)** — Quick reference guide
- **[DATA_ARCHITECTURE.md](../DATA_ARCHITECTURE.md)** — Technical architecture & relationships
- **[Architecture Slides](../architecture/BigBurger_AI_Architecture.md)** — 12-slide Marp deck

---

## 🚢 Production Equivalent (GCP)

This prototype demonstrates the core logic. In production on GCP:

### Ingestion
- **Google Drive API** → Fetch documents per region
- **Cloud Storage** → Staging bucket (per-region prefixes)
- **Document AI** → OCR for scanned PDFs
- **Cloud Run Job** → Triggered by Pub/Sub (document updates)
- **Vertex AI Vector Search** → Per-region indices
- **Firestore** → Document registry (versioning, soft-delete)

### Query Execution
- **Google ADK (Agent Development Kit)** → Supervisor pattern
- **Gemini 1.5 Pro/Flash** → Orchestration + synthesis
- **Cloud Run** → Regional agent services
- **Cloud Trace** → Observability & tracing
- **Vertex AI Rank API** → Cross-encoder re-ranking (if needed)

---

## 💡 Key Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Per-region collections** | Tenant isolation at storage layer | Extra overhead managing multiple collections |
| **Word-based chunking** | Simple, no dependencies | Semantic chunking would preserve clause boundaries better |
| **Mock LLM synthesis** | Fast iteration, no API keys | Mock LLM doesn't handle complex reasoning |
| **Keyword query classification** | Fast pattern matching | LLM classification more accurate but slower |
| **Synchronous retrieval** | Simple, testable | Parallel retrieval would be faster for cross-regional |

---

## 🤝 Next Steps

1. **Extend chunking** → Use semantic chunking (spaCy or LangChain)
2. **Add LLM integration** → Real Gemini API for synthesis
3. **Implement versioning** → Track document versions in Firestore
4. **Add observability** → Cloud Trace integration
5. **Scale to production** → Cloud Run, Vertex AI, Cloud Storage

---

## 📖 References

- **ChromaDB Documentation**: https://docs.trychroma.com
- **Google Generative AI**: https://ai.google.dev/
- **Agent Development Kit (ADK)**: https://ai.google.dev/agentic-ai
- **Vertex AI Vector Search**: https://cloud.google.com/vertex-ai/docs/vector-search

---

## 📄 License

Part of the BigBurger AI enterprise platform project.
