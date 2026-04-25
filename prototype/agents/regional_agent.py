"""
agents/regional_agent.py — Regional Scoped Agent

Handles queries scoped to a single region.  Each regional agent
is "tenant-aware" — it enforces RBAC before retrieval and always
annotates results with its region tag so the orchestrator can
correctly attribute findings during cross-regional synthesis.

Production equivalent on GCP:
  • Each regional agent would be a separate Cloud Run service
    (or a separate ADK Agent instance) with environment-scoped
    configuration pointing at its region's Vertex AI Vector Search index.
  • The orchestrator invokes regional agents via internal gRPC/HTTP
    calls, collecting responses in parallel (asyncio.gather).
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import UserToken, TOP_K_RESULTS
from agents.rbac import assert_region_access
from retrieval.retriever import MultiTenantRetriever


class RegionalAgent:
    """
    Handles retrieval for a single named region.

    Responsibilities:
      1. RBAC check — verify the calling user may access this region.
      2. Retrieve top-K semantically relevant chunks via the retriever.
      3. Return a structured result payload that the orchestrator can
         consume or present directly to the user.
    """

    def __init__(
        self,
        region: str,
        retriever: MultiTenantRetriever,
    ) -> None:
        self.region = region
        self._retriever = retriever

    def query(
        self,
        user: UserToken,
        query_text: str,
        n_results: int = TOP_K_RESULTS,
    ) -> dict[str, Any]:
        """
        Execute a regional search with RBAC enforcement.

        Returns:
            {
                "region":   str,
                "query":    str,
                "user_id":  str,
                "hits":     [ { text, distance, metadata }, … ],
                "error":    None | str   (set on permission error)
            }
        """
        # ── Access check ─────────────────────────────────────────
        try:
            assert_region_access(user, self.region)
        except PermissionError as exc:
            return {
                "region": self.region,
                "query": query_text,
                "user_id": user.user_id,
                "hits": [],
                "error": str(exc),
            }

        # ── Retrieval ────────────────────────────────────────────
        results_by_region = self._retriever.query(
            user=user,
            query_text=query_text,
            regions=[self.region],
            n_results=n_results,
        )

        hits = results_by_region.get(self.region, [])

        return {
            "region": self.region,
            "query": query_text,
            "user_id": user.user_id,
            "hits": hits,
            "error": None,
        }

    def format_hits_summary(self, hits: list[dict[str, Any]]) -> str:
        """
        Format retrieved hits into a readable text block.
        This is the "context" block handed to the LLM synthesiser.
        """
        if not hits:
            return f"[{self.region.upper()} REGION] No relevant documents found."

        lines = [f"[{self.region.upper()} REGION — {len(hits)} relevant chunk(s)]"]
        for i, hit in enumerate(hits, 1):
            meta = hit["metadata"]
            lines.append(
                f"\n  [{i}] {meta.get('title', 'Untitled')} "
                f"(doc_id: {meta.get('doc_id')}, "
                f"type: {meta.get('doc_type')}, "
                f"expiry: {meta.get('expiry_date', 'N/A')}, "
                f"liability: ${meta.get('liability_amount', 0):,.0f}, "
                f"similarity: {1 - hit['distance']:.2%})"
            )
            lines.append(f"     Excerpt: …{hit['text'][:220]}…")

        return "\n".join(lines)
