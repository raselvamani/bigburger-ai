# BigBurger AI — Enterprise Multi-Tenant Document Intelligence

A GCP-native system design and working Python prototype for BigBurger's
cross-regional AI document retrieval platform.

---
## Presentation Deck

Presentation deck is provided in the **architecture/BigBurger_AI_Architecture.md** file


## Repository Layout

```
bigburger-ai/
├── README.md
├── architecture/
│   └── BigBurger_AI_Architecture.md   ← 12-slide architecture deck (Marp markdown)
└── prototype/
    ├── requirements.txt
    ├── config.py                       ← Regions, roles, mock user tokens (JWT simulation)
    ├── mock_data/
    │   └── contracts.json              ← 16 realistic contracts across 4 regions
    ├── ingestion/
    │   ├── chunker.py                  ← Word-overlap document chunker
    │   └── pipeline.py                 ← Full ingestion orchestration
    ├── retrieval/
    │   ├── vector_store.py             ← ChromaDB multi-tenant store (per-region collections)
    │   └── retriever.py                ← RBAC-enforced retriever
    ├── agents/
    │   ├── rbac.py                     ← authenticate() / authorize_region_access()
    │   ├── regional_agent.py           ← Single-region scoped retrieval agent
    │   └── orchestrator_agent.py       ← Query classifier + cross-regional fan-out + synthesis
    └── main.py                         ← 7 live demo scenarios
```

---

## How to Read the Architecture Deck

Open `architecture/BigBurger_AI_Architecture.md`.

It is written in [Marp](https://marp.app/) markdown (12 slides), meaning:

- **As plain text**: readable directly in any text editor or GitHub.
- **As rendered slides**: install the [Marp VS Code extension](https://marketplace.visualstudio.com/items?itemName=marp-team.marp-vscode)
  and open the file → click the Marp preview icon in the top-right.
- **As a PDF**: `npx @marp-team/marp-cli architecture/BigBurger_AI_Architecture.md --pdf`

### Slide Guide

| Slide | Content |
|-------|---------|
| 1 | Title |
| 2 | The Challenge — current state vs target state |
| 3 | High-Level Architecture Diagram (ASCII) — end-to-end data flow |
| 4 | Pillar 1: Data Ingestion Pipeline |
| 5 | Pillar 1 cont. — Sync, Versioning, Deletions |
| 6 | Pillar 2: AI & Agentic Architecture (two-tier ADK design) |
| 7 | Pillar 2 cont. — Token cost, rate limits, latency budget |
| 8 | Pillar 3: Security & Access Control (AuthN/AuthZ, RBAC) |
| 9 | Pillar 4: Observability & Evaluation (golden datasets, RAG metrics) |
| 10 | Pillar 4 cont. — Production monitoring & feedback loop |
| 11 | Design Trade-offs (DB choice, LLM, chunking, agent pattern) |
| 12 | Prototype overview & run instructions |

---

## Running the Prototype

### Prerequisites

- Python 3.10+
- pip

### Install & Run

```bash
# From the repo root
cd prototype
pip install -r requirements.txt
python main.py
```

That's it. The prototype uses:
- **ChromaDB** (in-memory) — no database setup required
- **ChromaDB default embeddings** (ONNX MiniLM-L6-v2 bundled) — no API key required
- A **mock LLM synthesiser** — no Gemini / OpenAI API key required

The entire pipeline runs locally, offline, in a single Python process.

---

## What the Prototype Demonstrates

The prototype focuses on the hardest part of the system: **Multi-Tenant Routing & Retrieval**.

### 7 Demo Scenarios (run automatically by `main.py`)

| Demo | User | Role | Query Type | What it shows |
|------|------|------|------------|---------------|
| 1 | `alice_north` | Regional Manager (North) | **LOCAL** | Beef contract expiry — North only |
| 2 | `eve_auditor` | Global Auditor | **CROSS-REGIONAL** | FizzCo exclusivity conflicts + $1.2M liability in East |
| 3 | `bob_south` | Regional Manager (South) | Scoped to South | RBAC enforcement — cross-regional keywords silently scoped |
| 4 | `hacker_anon` | Unknown | Blocked | Authentication rejection |
| 5 | `frank_hq` | HQ Executive | **CROSS-REGIONAL** | Upcoming health inspections across all regions |
| 6 | `carol_east` | Regional Manager (East) | **LOCAL** | NYC health certificate expiry + renewal deadline |
| 7 | `eve_auditor` | Global Auditor | **CROSS-REGIONAL** | Aggregated lease early-termination liability |

### RBAC Model

| User ID | Role | Accessible Regions |
|---------|------|--------------------|
| `alice_north` | `regional_manager` | north only |
| `bob_south` | `regional_manager` | south only |
| `carol_east` | `regional_manager` | east only |
| `dave_west` | `regional_manager` | west only |
| `eve_auditor` | `global_auditor` | all 4 regions |
| `frank_hq` | `hq_executive` | all 4 regions |

### Mock Data — What's in contracts.json

16 documents across 4 regions (4 per region):

| Region | Documents |
|--------|-----------|
| **North** | FizzCo exclusive beverage contract · PrimeBeef supply agreement · Seattle lease · King County health inspection |
| **South** | FizzCo exclusive beverage contract · SouthernMeat supply · Texas 12-location lease portfolio · Texas health compliance |
| **East** | **BubbleDrink Corp exclusive contract (explicitly prohibits FizzCo — the core conflict)** · Expired beef contract · NYC Grade A health certificate · Manhattan flagship lease |
| **West** | FizzCo **non-exclusive** beverage contract · Pacific Prime Ranches beef · CA/AZ 12-location lease portfolio · California health compliance |

**Key conflict scenario**: East region has an active exclusivity deal with BubbleDrink Corp that **explicitly prohibits FizzCo products**. If BigBurger signs a national FizzCo deal, the East contract triggers a **$1,200,000 early-termination penalty**. Demo 2 surfaces exactly this finding.

---

## Architecture Highlights

### Pillar 1 — Data Ingestion (GCP)
- **Google Drive API** webhooks → **Pub/Sub** → **Cloud Storage** (per-region prefix)
- **Document AI** for OCR on scanned PDFs
- Semantic chunking (400–600 tokens, 80-token overlap) preserving legal clause boundaries
- **Vertex AI `text-embedding-004`** → **Vertex AI Vector Search** (one index per region)
- **Firestore** document registry for versioning, soft-delete, and orphan chunk cleanup

### Pillar 2 — AI & Agentic Architecture (GCP)
- **Google ADK** multi-agent pattern: Orchestrator (Gemini 1.5 Pro) + 4 Regional Agents
- LLM-based query classifier (Gemini Flash, ~$0.0001/call) routes LOCAL vs CROSS-REGIONAL
- Cross-regional fan-out is **parallel** (`asyncio.gather`) → latency ≈ single-region latency
- Cross-encoder re-ranker trims context to top-16 chunks before LLM synthesis
- P95 latency target: **< 4 seconds** end-to-end

### Pillar 3 — Security & Access (GCP)
- **Identity Platform** JWTs with custom `role` + `allowed_regions` claims
- RBAC enforced at **two layers**: query-time (orchestrator) + storage-layer (separate vector indexes)
- **VPC Service Controls** data perimeter · **Cloud KMS** CMEK per region · **Cloud Audit Logs**

### Pillar 4 — Observability & Evaluation (GCP)
- Golden QA dataset (50–100 pairs/region) evaluated with **Vertex AI Evaluation** (Ragas metrics)
- Custom **Cloud Monitoring** metrics: latency, retrieval score, faithfulness, auth rejection rate
- **BigQuery** feedback table → weekly review cycle → prompt/chunking improvements
- CI/CD gate: deployment blocked if RAG metrics drop > 5% from baseline

---

## Key Design Trade-offs

| Decision | Rationale |
|----------|-----------|
| **One Vector Search index per region** (vs namespace filter) | Hard tenant isolation at storage; simpler RBAC; trade-off: slightly higher infra cost |
| **Gemini family** (vs GPT-4o/Claude) | GCP-native = no data egress; tighter IAM + audit integration |
| **Semantic chunking** (vs fixed-size) | Preserves legal clause boundaries — critical for accurate retrieval of specific contract terms |
| **Supervisor + Sub-Agent pattern** (vs single RAG chain) | Each regional agent is independently testable; scales to N regions; parallel fan-out |
| **Pub/Sub webhooks** (vs nightly batch) | Near-real-time sync (<1 min latency vs overnight staleness) |

---

## Dependencies

```
chromadb>=0.5.0    # In-memory vector store with default ONNX embeddings
```

No other runtime dependencies. No API keys needed.

---

## Time Spent

~2 hours, focused on:
1. Designing the multi-tenant RBAC + retrieval architecture (the hardest part)
2. Building the working prototype with 7 realistic demo scenarios
3. Writing the architecture deck covering all four pillars + trade-offs
