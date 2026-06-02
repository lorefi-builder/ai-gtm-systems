"""Duplicate-spec check (non-blocking).

Looks for a prior spec on the SAME account with the same domain+task_type and an
overlapping scope. fct_spec stores no scope text, so we recover each prior spec's
scope from its staging row (stg_transcript_extracts, joined by transcript_id) and
compare with lightweight token overlap.

The pipeline does NOT block on the result — it surfaces it in the Slack summary
for a human to confirm.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from config import DEDUP_SIMILARITY
from db.client import select

from agents.retrieval import jaccard, scope_text, tokenize
from agents.schemas import DedupResult, Extraction


def _loose_match(a: str, b: str) -> bool:
    """Case-insensitive containment match (candidates may be non-canonical)."""
    a, b = (a or "").strip().lower(), (b or "").strip().lower()
    if not a or not b:
        return False
    return a == b or a in b or b in a


def check_duplicate(extraction: Extraction) -> DedupResult:
    """Return a non-blocking duplicate assessment for this transcript.

    Runs BEFORE classification, so it uses Agent 1's candidate domain/task_type.
    """
    if not extraction.account_name:
        return DedupResult(
            is_possible_duplicate=False,
            match_spec_id=None,
            reason="no account name extracted; nothing to dedup against",
        )

    accounts = select("dim_account", {"account_name": extraction.account_name})
    if not accounts:
        return DedupResult(
            is_possible_duplicate=False,
            match_spec_id=None,
            reason="account is net-new; no prior specs to duplicate",
        )

    account_id = accounts[0]["account_id"]
    prior_specs = select(
        "fct_spec",
        {"account_id": account_id},
        columns="spec_id,transcript_id,domain,task_type",
    )

    query_tokens = tokenize(scope_text(extraction.scope))
    best_id: Optional[str] = None
    best_score = 0.0

    for spec in prior_specs:
        # Same kind of work? (loose, since candidates aren't canonicalized yet)
        if not _loose_match(spec.get("domain", ""), extraction.candidate_domain):
            continue
        if not _loose_match(spec.get("task_type", ""), extraction.candidate_task_type):
            continue

        prior_scope = _prior_scope(spec.get("transcript_id"))
        score = jaccard(query_tokens, tokenize(scope_text(prior_scope)))
        if score > best_score:
            best_score, best_id = score, spec["spec_id"]

    if best_id is not None and best_score >= DEDUP_SIMILARITY:
        return DedupResult(
            is_possible_duplicate=True,
            match_spec_id=best_id,
            reason=(
                f"prior spec {best_id} on this account has the same domain/task_type "
                f"and {best_score:.0%} scope overlap"
            ),
        )

    return DedupResult(
        is_possible_duplicate=False,
        match_spec_id=None,
        reason="no prior spec with same domain/task_type and overlapping scope",
    )


def _prior_scope(transcript_id: Optional[str]) -> Dict[str, Any]:
    """Recover a prior spec's scope from its staging row."""
    if not transcript_id:
        return {}
    rows = select(
        "stg_transcript_extracts", {"transcript_id": transcript_id}, columns="scope"
    )
    return rows[0].get("scope", {}) if rows else {}
