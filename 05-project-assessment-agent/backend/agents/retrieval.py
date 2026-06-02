"""Retrieval helpers — RAG spec examples + historical analogs.

PRODUCTION: replace the lexical ranking below with pgvector + an embeddings
model (e.g. Voyage). The function INTERFACES stay identical — only the ranking
internals change — so swapping in vectors later is a drop-in.

Why lexical now: the corpus is tiny (~12 spec_documents, ~240 fct_spec). A
vector DB would be more moving parts than signal. Structured filtering on
(domain, task_type) does most of the work; lightweight token/flag overlap breaks
ties. Honest and good enough at this scale.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set

from config import ANALOG_K, RAG_K
from db.client import select


# --- lightweight lexical similarity ------------------------------------------
def tokenize(text: str) -> Set[str]:
    """Lowercase alphanumeric tokens as a set."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def scope_text(scope: Dict[str, Any]) -> str:
    """Flatten a scope/characteristics dict to a searchable blob."""
    return " ".join(str(v) for v in scope.values())


def jaccard(a: Set[str], b: Set[str]) -> float:
    """Jaccard overlap of two token sets (0..1)."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# --- RAG: past spec_documents for drafting -----------------------------------
def retrieve_spec_examples(
    domain: str, task_type: str, scope: Dict[str, Any], k: int = RAG_K
) -> List[Dict[str, Any]]:
    """Top-k past spec_documents to ground the draft.

    Filter by (domain, task_type); fall back to domain-only, then task_type-only,
    then the whole corpus. Rank survivors by token overlap with the scope.
    """
    docs = select("spec_documents", {"domain": domain, "task_type": task_type})
    if not docs:
        docs = select("spec_documents", {"domain": domain})
    if not docs:
        docs = select("spec_documents", {"task_type": task_type})
    if not docs:
        docs = select("spec_documents", {})

    query = tokenize(scope_text(scope))
    docs.sort(
        key=lambda d: jaccard(query, tokenize(f"{d.get('title', '')} {d.get('body', '')}")),
        reverse=True,
    )
    return docs[:k]


# --- analogs: historical fct_spec for resource baselines ---------------------
def retrieve_analogs(
    domain: str, task_type: str, scope: Dict[str, Any], k: int = ANALOG_K
) -> List[Dict[str, Any]]:
    """Top-k historical fct_spec rows used to average a resourcing baseline.

    fct_spec has no free-text scope, so we rank by escalation-flag overlap
    (passed in ``scope['escalation_flags']``) and fall back to confidence as a
    quality tie-breaker. Same filter cascade as the RAG retriever.
    """
    rows = select("fct_spec", {"domain": domain, "task_type": task_type})
    if not rows:
        rows = select("fct_spec", {"domain": domain})
    if not rows:
        rows = select("fct_spec", {"task_type": task_type})

    wanted_flags = set(scope.get("escalation_flags", []) or [])

    def score(row: Dict[str, Any]) -> tuple:
        row_flags = set(row.get("escalation_flags", []) or [])
        flag_overlap = len(wanted_flags & row_flags)
        return (flag_overlap, float(row.get("confidence") or 0.0))

    rows.sort(key=score, reverse=True)
    return rows[:k]
