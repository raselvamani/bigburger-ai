"""
agents/rbac.py — Authentication & Authorization

Provides mock versions of what would be token validation and
role enforcement in a production GCP system.

Production equivalent:
  • AuthN: Firebase Auth / Identity Platform issues a signed JWT.
    The backend (Cloud Run) calls `firebase_admin.auth.verify_id_token()`
    to validate the token and extract claims.
  • AuthZ: Custom claims embedded in the JWT (e.g. `role`,
    `allowed_regions`) are used to gate every query.
  • All auth events are logged to Cloud Audit Logs for compliance.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MOCK_USERS, UserToken


# ──────────────────────────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────────────────────────

def authenticate(user_id: str) -> UserToken:
    """
    Simulate JWT verification.

    In production: accepts a raw JWT string, verifies signature
    with Identity Platform public keys, and returns the decoded claims
    as a UserToken.  Here we just do a dict lookup.

    Raises:
        PermissionError: if the user_id is not found (simulates an
                         invalid / expired token rejection).
    """
    token = MOCK_USERS.get(user_id)
    if token is None:
        raise PermissionError(
            f"Authentication failed: user '{user_id}' not found. "
            f"Valid user IDs: {list(MOCK_USERS.keys())}"
        )
    return token


# ──────────────────────────────────────────────────────────────────
# Authorization helpers
# ──────────────────────────────────────────────────────────────────

def assert_region_access(token: UserToken, region: str) -> None:
    """
    Raise PermissionError if the user cannot access the given region.
    Called by the regional agent before executing any retrieval.
    """
    if not token.can_access_region(region):
        raise PermissionError(
            f"User '{token.user_id}' (role: {token.role}) does not have "
            f"access to region '{region}'. "
            f"Authorised regions: {token.regions}"
        )


def assert_cross_region_access(token: UserToken) -> None:
    """
    Raise PermissionError if the user is not allowed to run
    cross-regional queries (e.g. a regional manager trying to
    ask a question spanning multiple regions).
    """
    if not token.can_query_cross_region():
        raise PermissionError(
            f"User '{token.user_id}' (role: {token.role}) is not "
            f"authorised to run cross-regional queries. "
            f"Required role: global_auditor or hq_executive."
        )


def filter_to_allowed_regions(
    token: UserToken,
    requested_regions: list[str],
) -> list[str]:
    """
    Return only the regions from requested_regions that the user
    is authorised for, silently dropping any forbidden ones.
    """
    return [r for r in requested_regions if token.can_access_region(r)]
