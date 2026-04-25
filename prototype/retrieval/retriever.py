"""
retrieval/retriever.py — RBAC-Enforced Multi-Tenant Retriever

Sits between the agents and the raw vector store.
Every query call must supply a validated UserToken; the retriever
enforces the user's region entitlements *before* any vector search
is executed — unauthorized regions are silently skipped.

Security design note:
  RBAC is enforced at *two* layers:
    1. This retriever (query-time policy enforcement)
    2. The vector store collection boundaries (storage-layer isolation)
  Even if a bug in layer-1 passes a forbidden region, layer-2
  ensures no data leaks across tenant boundaries.
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import UserToken, TOP_K_RESULTS
from retrieval.vector_store import MultiTenantVectorStore


class MultiTenantRetriever:
    """
    RBAC-enforced retriever.

    Usage:
        retriever = MultiTenantRetriever(store)

        # Single-region query (regional manager)
        results = retriever.query(
            user=alice_token,
            query="When does our beef contract expire?",
            regions=["north"],
        )

        # Cross-regional query (global auditor)
        results = retriever.query(
            user=eve_token,
            query="Which regions have FizzCo exclusivity clauses?",
            regions=["north", "south", "east", "west"],
        )
    """

    def __init__(self, store: MultiTenantVectorStore) -> None:
        self._store = store

    def query(
        self,
        user: UserToken,
        query_text: str,
        regions: list[str] | None = None,
        n_results: int = TOP_K_RESULTS,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Execute a semantic search across one or more regions,
        enforcing the user's access entitlements.

        Args:
            user:       Validated UserToken (from RBAC authenticate()).
            query_text: Natural-language query string.
            regions:    Regions to search. Defaults to all regions
                        the user is authorised for. Requesting a region
                        the user cannot access raises PermissionError.
            n_results:  Top-K results per region.

        Returns:
            Dict keyed by region name → list of result dicts.
            Only authorized, non-empty regions are included.

        Raises:
            PermissionError: if regions contains a region the user
                             is not authorised for.
        """
        # Default: search all regions the user is allowed to access
        target_regions = regions if regions is not None else user.regions

        # ── RBAC enforcement ──────────────────────────────────────
        unauthorized = [r for r in target_regions if not user.can_access_region(r)]
        if unauthorized:
            raise PermissionError(
                f"User '{user.user_id}' (role: {user.role}) is not authorised "
                f"to access region(s): {unauthorized}. "
                f"Authorised regions: {user.regions}"
            )

        # ── Query each authorised region ──────────────────────────
        results_by_region: dict[str, list[dict[str, Any]]] = {}

        for region in target_regions:
            region_results = self._store.query_region(
                region=region,
                query_text=query_text,
                n_results=n_results,
            )
            if region_results:
                results_by_region[region] = region_results

        return results_by_region

    def flat_results(
        self,
        results_by_region: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """
        Flatten region-keyed results into a single sorted list.
        Useful when the orchestrator wants to pass a unified context
        window to the LLM synthesiser.
        """
        flat: list[dict[str, Any]] = []
        for _region, hits in results_by_region.items():
            flat.extend(hits)
        # Sort globally by similarity distance
        flat.sort(key=lambda r: r["distance"])
        return flat
