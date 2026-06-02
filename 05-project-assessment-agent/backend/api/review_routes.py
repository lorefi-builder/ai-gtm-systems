"""Review lifecycle routes: send-to-review, approve, reject.

All three are guarded warehouse mutations routed through ops/lifecycle.py, which
enforces the legal from-state and writes the spec_status_history audit row.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from api import to_error_response
from ops import slack_messages
from ops.lifecycle import create_opportunity_from_spec, transition

router = APIRouter(tags=["review"])


class ReviewRequest(BaseModel):
    spec_id: str
    requested_by: str


class ApproveRequest(BaseModel):
    spec_id: str
    actor: str


class RejectRequest(BaseModel):
    spec_id: str
    actor: str
    reason: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/review")
def send_to_review(body: ReviewRequest):
    """draft -> in_review.

    PRODUCTION: a Slack-internal routing action that records the transition to
    the warehouse (the warehouse, not Slack, is the source of truth).
    """
    try:
        transition(
            body.spec_id,
            "in_review",
            actor=body.requested_by,
            require_from="draft",
            reason="sent to review",
        )
        return {
            "status": "in_review",
            "spec_id": body.spec_id,
            "slack_message": slack_messages.review_routed_message(
                body.spec_id, body.requested_by
            ),
        }
    except Exception as exc:
        return to_error_response(exc)


@router.post("/approve")
def approve(body: ApproveRequest):
    """in_review -> approved, then create opportunity + spine.

    PRODUCTION: approval fires HIGHTOUCH reverse ETL (near-real-time) creating a
    Salesforce Spec object + Opportunity object. Here FastAPI writes the
    warehouse rows those objects mirror.
    ASSUMPTION: the opportunity is created ON APPROVAL (not at discovery). If
    opps are created at disco, this becomes link-and-advance, not create.
    """
    try:
        spec = transition(
            body.spec_id,
            "approved",
            actor=body.actor,
            require_from="in_review",
            reason="approved",
            extra_changes={"approved_at": _now_iso()},
        )
        # Fan-out: stands in for the warehouse -> Salesforce reverse-ETL sync.
        opportunity_id, opportunity = create_opportunity_from_spec(spec, body.actor)
        return {
            "status": "approved",
            "spec_id": body.spec_id,
            "opportunity_id": opportunity_id,
            "slack_message": slack_messages.approved_opp_message(
                body.spec_id, opportunity_id, body.actor, opportunity
            ),
        }
    except Exception as exc:
        return to_error_response(exc)


@router.post("/reject")
def reject(body: RejectRequest):
    """in_review -> rejected (reason required). No opportunity is created.

    PRODUCTION: a Slack reject action recorded to the warehouse; no reverse-ETL
    push happens because nothing was approved.
    """
    try:
        if not body.reason or not body.reason.strip():
            raise ValueError("a non-empty reason is required to reject a spec")
        transition(
            body.spec_id,
            "rejected",
            actor=body.actor,
            require_from="in_review",
            reason=body.reason,
            extra_changes={"rejection_reason": body.reason},
        )
        return {
            "status": "rejected",
            "spec_id": body.spec_id,
            "slack_message": slack_messages.rejected_message(
                body.spec_id, body.actor, body.reason
            ),
        }
    except Exception as exc:
        return to_error_response(exc)
