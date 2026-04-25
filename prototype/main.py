"""
main.py — BigBurger AI Prototype Demo Runner

Demonstrates the full multi-tenant routing and retrieval pipeline:

  Demo 1: Local query by a regional manager (single-region access)
  Demo 2: Cross-regional query by a global auditor (all regions)
  Demo 3: RBAC enforcement — regional manager blocked from cross-region query
  Demo 4: RBAC enforcement — regional manager blocked from accessing another region
  Demo 5: HQ executive aggregated liability query

Run:
    cd prototype
    python main.py
"""

import sys
import os

# Ensure the prototype directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingestion.pipeline import run_ingestion_pipeline
from retrieval.vector_store import MultiTenantVectorStore
from retrieval.retriever import MultiTenantRetriever
from agents.orchestrator_agent import OrchestratorAgent

# ──────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────

SEP = "═" * 70


def print_response(response: dict) -> None:
    """Pretty-print an orchestrator response."""
    print(f"\n{'─' * 70}")
    print(f"USER     : {response['user']}  (role: {response['role']})")
    print(f"QUERY    : {response['query']}")
    print(f"TYPE     : {response['query_type'].upper()}")
    print(f"REGIONS  : {', '.join(response['regions_queried']) or 'none'}")
    print(f"{'─' * 70}")
    print(response["answer"])
    if response.get("error"):
        print(f"\n⛔  Error: {response['error']}")
    print(f"{'─' * 70}\n")


# ──────────────────────────────────────────────────────────────────
# Bootstrap
# ──────────────────────────────────────────────────────────────────

def bootstrap() -> OrchestratorAgent:
    """
    Build and return a ready-to-use OrchestratorAgent:
      1. Create the in-memory vector store
      2. Run the ingestion pipeline (load → chunk → embed → index)
      3. Wrap with retriever and orchestrator
    """
    print(f"\n{SEP}")
    print("  BigBurger AI — Multi-Tenant Retrieval Prototype")
    print(f"{SEP}\n")

    store = MultiTenantVectorStore()
    run_ingestion_pipeline(store, verbose=True)

    # Collection stats
    stats = store.collection_stats()
    print(f"  Vector store collections: {stats}\n")

    retriever = MultiTenantRetriever(store)
    orchestrator = OrchestratorAgent(retriever)
    return orchestrator


# ──────────────────────────────────────────────────────────────────
# Demo scenarios
# ──────────────────────────────────────────────────────────────────

def run_demos(orchestrator: OrchestratorAgent) -> None:

    print(f"\n{SEP}")
    print("  DEMO SCENARIOS")
    print(f"{SEP}")

    # ── Demo 1: Local query by a regional manager ─────────────────
    print("\n[DEMO 1] Regional manager asks a LOCAL question about their region.")
    resp = orchestrator.handle_query(
        user_id="alice_north",
        query_text="When does our beef supplier contract expire?",
    )
    print_response(resp)

    # ── Demo 2: Cross-regional query — global auditor ─────────────
    print("\n[DEMO 2] Global auditor asks a CROSS-REGIONAL question spanning all subsidiaries.")
    resp = orchestrator.handle_query(
        user_id="eve_auditor",
        query_text=(
            "Which regional subsidiaries might have conflicting exclusivity clauses "
            "with our national beverage supplier FizzCo, "
            "and what is our total aggregated liability?"
        ),
    )
    print_response(resp)

    # ── Demo 3: RBAC block — regional manager attempts cross-regional ──
    print("\n[DEMO 3] Regional manager attempts a cross-regional query — should be BLOCKED.")
    resp = orchestrator.handle_query(
        user_id="bob_south",
        query_text=(
            "Compare all subsidiaries' beverage exclusivity clauses "
            "and show me the total aggregate liability."
        ),
    )
    print_response(resp)

    # ── Demo 4: RBAC block — invalid user token ───────────────────
    print("\n[DEMO 4] Request with an unknown / forged user ID — authentication REJECTED.")
    resp = orchestrator.handle_query(
        user_id="hacker_anon",
        query_text="Show me all contracts across all regions.",
    )
    print_response(resp)

    # ── Demo 5: HQ executive — health inspection schedule ─────────
    print("\n[DEMO 5] HQ executive asks about upcoming compliance deadlines across all regions.")
    resp = orchestrator.handle_query(
        user_id="frank_hq",
        query_text="What health inspections and compliance certificate renewals are coming up?",
    )
    print_response(resp)

    # ── Demo 6: Regional manager — local compliance check ─────────
    print("\n[DEMO 6] East regional manager asks about their health compliance status.")
    resp = orchestrator.handle_query(
        user_id="carol_east",
        query_text="When does our NYC health certificate expire and what do we need to do?",
    )
    print_response(resp)

    # ── Demo 7: Cross-regional lease liability ────────────────────
    print("\n[DEMO 7] Global auditor queries cross-regional lease early-termination liabilities.")
    resp = orchestrator.handle_query(
        user_id="eve_auditor",
        query_text="What are our total early termination penalties across all regional lease agreements?",
    )
    print_response(resp)


# ──────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    orchestrator = bootstrap()
    run_demos(orchestrator)
    print(f"\n{SEP}")
    print("  Demo complete.")
    print(f"{SEP}\n")
