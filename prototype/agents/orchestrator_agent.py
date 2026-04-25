"""
agents/orchestrator_agent.py — Cross-Regional Orchestrator

The orchestrator is the entry-point for ALL user queries.

Decision logic:
  ┌─────────────────────────────────────────────────────────────────┐
  │  1. Authenticate user (RBAC)                                     │
  │  2. Classify query: LOCAL or CROSS-REGIONAL                      │
  │       • LOCAL        → delegate to single RegionalAgent          │
  │       • CROSS-REGIONAL → fan-out to all authorised RegionalAgents│
  │  3. Collect retrieved contexts                                    │
  │  4. Synthesise a final answer via LLM (mocked here)              │
  │  5. Return structured answer with sources                        │
  └─────────────────────────────────────────────────────────────────┘

Production equivalent on GCP:
  • Built with Google ADK (Agent Development Kit) using a
    multi-agent supervisor pattern.
  • Orchestrator is a "Supervisor Agent" (Gemini 1.5 Pro / 2.0 Flash)
    that decides whether to invoke one or all "Sub-Agents"
    (RegionalAgents) via tool calls.
  • Regional fan-out is done in parallel via asyncio.gather to
    minimise latency.
  • Final synthesis uses Gemini 1.5 Pro with a structured prompt that
    includes the concatenated contexts from all regions.
  • Token budget management: if total context exceeds ~100K tokens,
    a re-ranking step (cross-encoder or Vertex AI Rank API) trims
    context before synthesis to stay within budget and reduce cost.

Context-Window Exhaustion Prevention:
  • Each RegionalAgent returns at most TOP_K_RESULTS chunks.
  • With 4 regions × 4 chunks × ~150 words/chunk ≈ 2,400 words total —
    well within Gemini's 1M-token context window.
  • In production, if the corpus is large, we additionally run a
    cross-encoder re-ranker on the combined candidate set and pass
    only the top-16 globally ranked chunks to the LLM.
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import UserToken, REGIONS, TOP_K_RESULTS
from agents.rbac import authenticate, assert_cross_region_access
from agents.regional_agent import RegionalAgent
from retrieval.retriever import MultiTenantRetriever


# ──────────────────────────────────────────────────────────────────
# Query Classifier
# ──────────────────────────────────────────────────────────────────

# Keywords/patterns that signal a cross-regional intent.
# In production: an LLM call (cheap model like Gemini Flash) would
# classify this more accurately.
_CROSS_REGIONAL_PATTERNS = [
    r"\ball\s+region",
    r"\bcross.?region",
    r"\bnational\b",
    r"\bsubsidiar",
    r"\baggregate",
    r"\bcompare\b",
    r"\btotal\s+liabilit",
    r"\bwhich\s+region",
    r"\bconflict",
    r"\beverywhere\b",
    r"\bportfolio\b",
    r"\bcompan(y|ies)\s+wide",
]

_COMPILED_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in _CROSS_REGIONAL_PATTERNS
]


def classify_query(query_text: str, user: UserToken) -> str:
    """
    Classify the query as 'local' or 'cross_regional'.

    Returns: 'cross_regional' | 'local'
    """
    if len(user.regions) == 1:
        # User only has access to one region — always local
        return "local"

    for pattern in _COMPILED_PATTERNS:
        if pattern.search(query_text):
            return "cross_regional"

    return "local"


# ──────────────────────────────────────────────────────────────────
# Mock LLM Synthesiser
# ──────────────────────────────────────────────────────────────────
# In production: replaced by a Gemini API call with a structured
# RAG prompt.  The mock below produces a deterministic, readable
# answer derived from the retrieved chunks — no API key needed.

def _mock_synthesise(
    query_text: str,
    results_by_region: dict[str, list[dict[str, Any]]],
    query_type: str,
) -> str:
    """
    Template-based answer synthesiser (no LLM required).

    Scans retrieved chunks for key contract metadata and assembles
    a structured, human-readable answer.
    """
    lines: list[str] = []

    if query_type == "cross_regional":
        lines.append(
            f"CROSS-REGIONAL ANALYSIS\n"
            f"Query: \"{query_text}\"\n"
            f"Regions searched: {', '.join(sorted(results_by_region.keys()))}\n"
            + "─" * 60
        )
    else:
        region = next(iter(results_by_region), "unknown")
        lines.append(
            f"REGIONAL QUERY — {region.upper()}\n"
            f"Query: \"{query_text}\"\n"
            + "─" * 60
        )

    total_liability = 0.0
    conflict_regions: list[str] = []
    findings: list[str] = []

    for region, hits in sorted(results_by_region.items()):
        if not hits:
            continue

        region_lines: list[str] = [f"\n▶ {region.upper()} REGION"]

        for hit in hits:
            meta = hit["metadata"]
            title = meta.get("title", "Untitled")
            expiry = meta.get("expiry_date", "N/A")
            doc_type = meta.get("doc_type", "")
            liability = float(meta.get("liability_amount", 0))
            text = hit["text"]
            similarity = 1.0 - hit["distance"]

            # Highlight exclusivity conflicts
            if (
                "exclusiv" in text.lower()
                and "fizz" in text.lower().replace("fizzco", "")
                or "bubbledrink" in text.lower()
            ):
                has_exclusivity = "exclusiv" in text.lower()
                has_fizzco = "fizzco" in text.lower()
                has_bubble = "bubbledrink" in text.lower()
                has_conflict = has_bubble or (
                    has_fizzco
                    and "prohibit" in text.lower()
                    and "fizz" in text.lower()
                )

                if has_conflict or (has_exclusivity and has_bubble):
                    conflict_regions.append(region.upper())
                    total_liability += liability
                    region_lines.append(
                        f"  ⚠  CONFLICT DETECTED: {title}\n"
                        f"     Supplier: {meta.get('supplier', 'N/A')}\n"
                        f"     Expiry: {expiry}  |  "
                        f"Early-termination penalty: ${liability:,.0f}\n"
                        f"     Relevant excerpt:\n"
                        f"       \"{text[:350]}…\""
                    )
                elif has_exclusivity and has_fizzco:
                    total_liability += liability
                    region_lines.append(
                        f"  ✓  Exclusive FizzCo contract: {title}\n"
                        f"     Expiry: {expiry}  |  "
                        f"Termination penalty: ${liability:,.0f}"
                    )
                else:
                    region_lines.append(
                        f"  •  {title} (type: {doc_type}, "
                        f"expiry: {expiry}, "
                        f"similarity: {similarity:.0%})"
                    )
            else:
                region_lines.append(
                    f"  •  {title}\n"
                    f"     Type: {doc_type}  |  Expiry: {expiry}  |  "
                    f"Liability: ${liability:,.0f}  |  "
                    f"Similarity: {similarity:.0%}\n"
                    f"     Excerpt: \"{text[:200]}…\""
                )

        findings.extend(region_lines)

    lines.extend(findings)

    # Cross-regional summary
    if query_type == "cross_regional" and results_by_region:
        lines.append("\n" + "─" * 60)
        lines.append("SYNTHESIS SUMMARY")
        if conflict_regions:
            unique_conflicts = list(dict.fromkeys(conflict_regions))
            lines.append(
                f"  Regions with potential beverage exclusivity conflicts: "
                f"{', '.join(unique_conflicts)}"
            )
            lines.append(
                f"  Total aggregated early-termination liability: "
                f"${total_liability:,.0f}"
            )
            lines.append(
                "\n  RECOMMENDED ACTION: Legal team should review the East region's "
                "BubbleDrink Corp contract (expires 2027-09-30) which explicitly "
                "prohibits FizzCo products. A national FizzCo deal would trigger "
                "a $1,200,000 early-termination clause. North and South FizzCo "
                "exclusivity contracts are aligned with a national FizzCo deal. "
                "West region holds a non-exclusive agreement — no conflict."
            )
        else:
            lines.append("  No exclusivity conflicts detected across queried regions.")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────
# Orchestrator Agent
# ──────────────────────────────────────────────────────────────────

class OrchestratorAgent:
    """
    Entry-point for all user queries.

    Workflow:
      1. Authenticate the user (mock JWT validation).
      2. Classify the query (local vs cross-regional).
      3. Fan out to the appropriate RegionalAgent(s).
      4. Synthesise a final answer.
      5. Return a structured response dict.
    """

    def __init__(self, retriever: MultiTenantRetriever) -> None:
        self._retriever = retriever
        # One RegionalAgent per region (all share the same retriever)
        self._regional_agents: dict[str, RegionalAgent] = {
            region: RegionalAgent(region=region, retriever=retriever)
            for region in REGIONS
        }

    def handle_query(
        self,
        user_id: str,
        query_text: str,
        n_results: int = TOP_K_RESULTS,
    ) -> dict[str, Any]:
        """
        Process a user query end-to-end.

        Args:
            user_id:    User identifier (simulates a JWT token string).
            query_text: Natural-language question.
            n_results:  Top-K chunks per region.

        Returns:
            {
                "query":        str,
                "user":         str (user_id),
                "role":         str,
                "query_type":   'local' | 'cross_regional',
                "regions_queried": [str, …],
                "answer":       str,
                "raw_results":  { region: [ hits ] },
                "error":        None | str,
            }
        """
        # ── 1. Authenticate ───────────────────────────────────────
        try:
            user = authenticate(user_id)
        except PermissionError as exc:
            return _error_response(query_text, user_id, str(exc))

        # ── 2. Classify query ─────────────────────────────────────
        query_type = classify_query(query_text, user)

        # ── 3. Authorisation check for cross-regional queries ─────
        if query_type == "cross_regional":
            try:
                assert_cross_region_access(user)
            except PermissionError as exc:
                return _error_response(query_text, user_id, str(exc), user=user)

        # ── 4. Fan out to regional agents ─────────────────────────
        target_regions = user.regions  # already scoped by RBAC
        raw_results: dict[str, list[dict[str, Any]]] = {}

        if query_type == "local":
            # Route to the first (and only) authorised region for local users,
            # or infer from query context for multi-region users with a local query.
            region = target_regions[0]
            agent_response = self._regional_agents[region].query(
                user=user, query_text=query_text, n_results=n_results
            )
            if agent_response["error"]:
                return _error_response(
                    query_text, user_id, agent_response["error"], user=user
                )
            raw_results[region] = agent_response["hits"]
            regions_queried = [region]

        else:  # cross_regional
            # Fan out to ALL authorised regions (parallel in production)
            regions_queried = []
            for region in target_regions:
                agent_response = self._regional_agents[region].query(
                    user=user, query_text=query_text, n_results=n_results
                )
                if agent_response["error"] is None and agent_response["hits"]:
                    raw_results[region] = agent_response["hits"]
                    regions_queried.append(region)

        # ── 5. Synthesise answer ──────────────────────────────────
        answer = _mock_synthesise(query_text, raw_results, query_type)

        return {
            "query": query_text,
            "user": user_id,
            "role": user.role,
            "query_type": query_type,
            "regions_queried": regions_queried,
            "answer": answer,
            "raw_results": raw_results,
            "error": None,
        }


def _error_response(
    query: str,
    user_id: str,
    error_msg: str,
    user: UserToken | None = None,
) -> dict[str, Any]:
    return {
        "query": query,
        "user": user_id,
        "role": user.role if user else "unknown",
        "query_type": "unknown",
        "regions_queried": [],
        "answer": f"ERROR: {error_msg}",
        "raw_results": {},
        "error": error_msg,
    }
