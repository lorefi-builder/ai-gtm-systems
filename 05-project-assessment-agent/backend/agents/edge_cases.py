"""Advisory edge-case rubric (ADVISORY ONLY).

``detect_edge_cases`` runs deterministic, side-effect-free detectors over the
extraction + classification and returns a list of :class:`EdgeCaseFlag` hints for
the Slack summary. It NEVER sets ``needs_human_review`` and NEVER changes the
verdict — the matrix color, escalation flags, and the review hook are all decided
in ``classify.py``. These are reviewer nudges, ordered by tier (1 = most
structural, 3 = least), and the summary renders them in that order.
"""

from __future__ import annotations

from typing import List

from config import CONFIDENCE_THRESHOLD

from agents.schemas import Classification, EdgeCaseFlag, Extraction

# Scope keys that, by name alone, indicate a volume figure is present.
_VOLUME_KEYS = ("volume", "sample", "count")


def _has_numeric_volume(scope: dict) -> bool:
    """True if scope carries a volume signal: a volume-ish key OR any digit in a value."""
    for key, value in (scope or {}).items():
        if any(token in str(key).lower() for token in _VOLUME_KEYS):
            return True
        if any(ch.isdigit() for ch in str(value)):
            return True
    return False


def detect_edge_cases(
    extraction: Extraction, classification: Classification
) -> List[EdgeCaseFlag]:
    """Deterministic, advisory edge-case detectors. Returns hints ordered by tier."""
    flags: List[EdgeCaseFlag] = []

    # Tier 1 — more than one distinct project discussed in one call.
    if extraction.multi_project:
        flags.append(
            EdgeCaseFlag(
                code="multi_project",
                tier=1,
                label="Multi-project",
                suggestion=(
                    "More than one distinct project in this call. Review whether to "
                    "split into separate specs or consolidate. Primary drafted; "
                    "secondary noted."
                ),
            )
        )

    # Tier 2 — domain/task-type is uncertain; the matrix verdict rides on it.
    if classification.confidence < CONFIDENCE_THRESHOLD:
        flags.append(
            EdgeCaseFlag(
                code="ambiguous_domain",
                tier=2,
                label="Ambiguous domain/task-type",
                suggestion=(
                    f"Domain/task-type uncertain (confidence "
                    f"{classification.confidence:.2f}). The matrix verdict depends on "
                    f"this — confirm the classification before proceeding."
                ),
            )
        )

    # Tier 3 — discovery is incomplete; name exactly which signal is missing.
    missing: List[str] = []
    if not _has_numeric_volume(extraction.scope):
        missing.append("volume")
    if not extraction.success_criteria:
        missing.append("acceptance criteria")
    if not extraction.candidate_task_type:
        missing.append("deliverable")
    if missing:
        flags.append(
            EdgeCaseFlag(
                code="incomplete_info",
                tier=3,
                label="Incomplete discovery",
                suggestion=(
                    f"Missing {', '.join(missing)}. Follow up with the customer "
                    f"before committing; estimate uses conservative defaults."
                ),
            )
        )

    return flags
