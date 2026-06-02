"""Guarded status transitions + audit log + the approval fan-out (spine writes).

EVERY status change in the system goes through here so that:
  * transitions are GUARDED (e.g. approve only from in_review), and
  * every transition writes a spec_status_history row (the warehouse audit log).

The warehouse is the single source of truth. There is no PATCH in the thin
client, so an "update" is: select the current row, merge changes, and upsert the
full row (on_conflict=spec_id). Re-sending all columns keeps NOT NULL columns
satisfied while ON CONFLICT updates the row in place.
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from db.client import insert, select, upsert


class LifecycleError(Exception):
    """Raised when a guarded transition is attempted from the wrong state."""


# Simple per-segment fallback if there are no analog opportunities to average.
_BASE_AMOUNT = {"Enterprise": 250_000.0, "Mid-Market": 110_000.0, "SMB": 45_000.0}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- low-level warehouse helpers --------------------------------------------
def _get_spec(spec_id: str) -> Dict[str, Any]:
    rows = select("fct_spec", {"spec_id": spec_id})
    if not rows:
        raise LifecycleError(f"spec {spec_id} not found")
    return rows[0]


def _persist_spec(merged_row: Dict[str, Any]) -> None:
    """Upsert a full fct_spec row (acts as an in-place update on spec_id)."""
    upsert("fct_spec", merged_row, on_conflict="spec_id")


def log_status(
    spec_id: Optional[str],
    from_status: Optional[str],
    to_status: str,
    actor: Optional[str],
    reason: Optional[str] = None,
) -> None:
    """Append one audit row. spec_id may be None for pre-spec events."""
    insert(
        "spec_status_history",
        {
            "spec_id": spec_id,
            "from_status": from_status,
            "to_status": to_status,
            "actor": actor,
            "reason": reason,
        },
    )


def update_spec(spec_id: str, changes: Dict[str, Any]) -> Dict[str, Any]:
    """Merge-and-persist arbitrary fct_spec fields (no status guard, no audit)."""
    merged = dict(_get_spec(spec_id))
    merged.update(changes)
    _persist_spec(merged)
    return merged


# --- the guarded transition --------------------------------------------------
def transition(
    spec_id: str,
    to_status: str,
    actor: str,
    *,
    require_from: Optional[Any] = None,
    reason: Optional[str] = None,
    extra_changes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Move a spec to ``to_status``, enforcing ``require_from`` and logging it.

    ``require_from`` may be a single status string or an iterable of allowed
    statuses (e.g. ("draft", "rejected") for soft delete).
    """
    current = _get_spec(spec_id)
    cur_status = current.get("status")
    if require_from is not None:
        allowed = (require_from,) if isinstance(require_from, str) else tuple(require_from)
        if cur_status not in allowed:
            raise LifecycleError(
                f"spec {spec_id} is '{cur_status}'; can only move to '{to_status}' "
                f"from {' or '.join(repr(s) for s in allowed)}"
            )

    merged = dict(current)
    merged["status"] = to_status
    if extra_changes:
        merged.update(extra_changes)
    _persist_spec(merged)

    log_status(spec_id, cur_status, to_status, actor, reason)
    return merged


# --- approval fan-out: create opportunity + spine ---------------------------
# PRODUCTION: this fan-out is performed by HIGHTOUCH reverse ETL (warehouse->SF),
# event-driven on approval — it creates a Salesforce Spec object + Opportunity
# object within minutes. Here FastAPI writes the warehouse rows those SF objects
# mirror, directly and synchronously.
def create_opportunity_from_spec(
    spec_row: Dict[str, Any], actor: str
) -> Tuple[str, Dict[str, Any]]:
    """Create the Discovery-stage opportunity + spec_lifecycle spine row.

    Returns (opportunity_id, opportunity_row) and sets fct_spec.opportunity_id.
    """
    account = _resolve_account(spec_row["account_id"])
    segment = account.get("segment", "Mid-Market")
    region = account.get("region", "NA")
    owner = account.get("owner", "unassigned@lorefi.com")
    account_name = account.get("account_name", "Unknown")

    opportunity_id = str(uuid4())
    opportunity_row = {
        "opportunity_id": opportunity_id,
        "spec_id": spec_row["spec_id"],
        "account_id": spec_row["account_id"],
        "name": f"{account_name} – {spec_row['task_type']} Program",
        "stage": "Discovery",                       # opps start at Discovery on approval
        "amount": _estimate_amount(segment),
        "segment": segment,                         # denormalized from dim_account
        "region": region,
        "owner": owner,
        "is_won": False,
    }
    insert("fct_opportunity", opportunity_row)

    # The spine: one row tying transcript <-> spec <-> opportunity <-> account.
    insert(
        "spec_lifecycle",
        {
            "lifecycle_id": str(uuid4()),
            "transcript_id": spec_row.get("transcript_id"),
            "spec_id": spec_row["spec_id"],
            "opportunity_id": opportunity_id,
            "account_id": spec_row["account_id"],
            "project_id": None,
        },
    )

    # Close the loop on the spec side.
    update_spec(spec_row["spec_id"], {"opportunity_id": opportunity_id})
    return opportunity_id, opportunity_row


def _resolve_account(account_id: str) -> Dict[str, Any]:
    rows = select("dim_account", {"account_id": account_id})
    return rows[0] if rows else {}


def _estimate_amount(segment: str) -> float:
    """Amount = average of existing opportunities in this segment (analog avg),
    falling back to a simple per-segment base rule when there are none yet."""
    opps = select("fct_opportunity", {"segment": segment}, columns="amount")
    amounts: List[float] = [
        float(o["amount"]) for o in opps if o.get("amount") is not None
    ]
    if amounts:
        return round(mean(amounts), 2)
    return _BASE_AMOUNT.get(segment, 100_000.0)
