"""
config.py — BigBurger AI Prototype Configuration

Defines regions, roles, and mock user tokens that simulate
what would normally be JWT claims from Identity Platform (GCP).
"""

from dataclasses import dataclass, field
from typing import List

# ──────────────────────────────────────────────
# Regions
# ──────────────────────────────────────────────
REGIONS: List[str] = ["north", "south", "east", "west"]

# ──────────────────────────────────────────────
# Role definitions
# ──────────────────────────────────────────────
# In production: roles are stored as custom claims in Firebase Auth / Identity Platform JWTs.
# regional_manager  → read-only access to a single assigned region
# global_auditor    → read-only access to ALL regions (cross-regional queries allowed)
# hq_executive      → same access as global_auditor + aggregation queries
ROLE_PERMISSIONS = {
    "regional_manager": {
        "can_query_cross_region": False,
        "can_aggregate": False,
        "description": "Read-only access to their assigned region only.",
    },
    "global_auditor": {
        "can_query_cross_region": True,
        "can_aggregate": True,
        "description": "Read-only access to all regions; can run cross-regional queries.",
    },
    "hq_executive": {
        "can_query_cross_region": True,
        "can_aggregate": True,
        "description": "Full read access across all regions; can view aggregated liability.",
    },
}


# ──────────────────────────────────────────────
# Mock User Token
# ──────────────────────────────────────────────
@dataclass
class UserToken:
    """
    Simulates a decoded JWT issued by GCP Identity Platform.
    In production this would be verified server-side before any query is processed.
    """
    user_id: str
    name: str
    role: str               # must be a key in ROLE_PERMISSIONS
    regions: List[str]      # list of region(s) this user is authorized to access

    def can_access_region(self, region: str) -> bool:
        return region in self.regions

    def can_query_cross_region(self) -> bool:
        return ROLE_PERMISSIONS.get(self.role, {}).get("can_query_cross_region", False)

    def can_aggregate(self) -> bool:
        return ROLE_PERMISSIONS.get(self.role, {}).get("can_aggregate", False)

    def __repr__(self) -> str:
        return (
            f"UserToken(user_id={self.user_id!r}, role={self.role!r}, "
            f"regions={self.regions})"
        )


# ──────────────────────────────────────────────
# Mock User Store  (replaces a real Identity Provider / user DB)
# ──────────────────────────────────────────────
MOCK_USERS: dict[str, UserToken] = {
    # Regional managers — single-region access
    "alice_north": UserToken(
        user_id="alice_north",
        name="Alice Johnson",
        role="regional_manager",
        regions=["north"],
    ),
    "bob_south": UserToken(
        user_id="bob_south",
        name="Bob Smith",
        role="regional_manager",
        regions=["south"],
    ),
    "carol_east": UserToken(
        user_id="carol_east",
        name="Carol Martinez",
        role="regional_manager",
        regions=["east"],
    ),
    "dave_west": UserToken(
        user_id="dave_west",
        name="Dave Kim",
        role="regional_manager",
        regions=["west"],
    ),
    # Global auditor — all-region access
    "eve_auditor": UserToken(
        user_id="eve_auditor",
        name="Eve Williams",
        role="global_auditor",
        regions=["north", "south", "east", "west"],
    ),
    # HQ executive — all-region access
    "frank_hq": UserToken(
        user_id="frank_hq",
        name="Frank Chen",
        role="hq_executive",
        regions=["north", "south", "east", "west"],
    ),
}


# ──────────────────────────────────────────────
# Chunking parameters
# ──────────────────────────────────────────────
CHUNK_SIZE_WORDS = 120       # target words per chunk
CHUNK_OVERLAP_WORDS = 20     # overlap between consecutive chunks
TOP_K_RESULTS = 4            # documents retrieved per region per query


# ──────────────────────────────────────────────
# ChromaDB settings
# ──────────────────────────────────────────────
CHROMA_COLLECTION_PREFIX = "bigburger"   # collections are named bigburger_{region}
