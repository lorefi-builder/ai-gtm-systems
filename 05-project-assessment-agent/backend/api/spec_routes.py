"""Spec creation + dedup resume routes.

POST /spec         create a draft spec from a transcript (or pause on duplicate)
POST /spec/resume  resolve a paused duplicate via one of three choices
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api import to_error_response
from ops.orchestrator import regenerate_spec, resume_spec, run_spec, soft_delete_spec

router = APIRouter(tags=["spec"])


class SpecRequest(BaseModel):
    transcript_text: str
    requested_by: str
    transcript_id: Optional[str] = None


class ResumeRequest(BaseModel):
    ref: str          # the transcript_id returned by a paused /spec response
    choice: str       # "proceed" | "link" | "escalate"


class RegenerateRequest(BaseModel):
    spec_id: str
    requested_by: str
    correction_context: Optional[str] = None   # optional <=500-char guidance


class DeleteRequest(BaseModel):
    spec_id: str
    actor: str


@router.post("/spec")
def create_spec(body: SpecRequest):
    """Agent 1 -> real-time dedup -> (pause | classify+estimate+draft+write).

    PRODUCTION: /spec is a Slack slash command; the stg_transcript_extracts
    insert fires dedup + Agent 2 via a Postgres LISTEN/NOTIFY trigger. Dedup
    reads warehouse spec history directly — no Salesforce-sync dependency.
    """
    try:
        return run_spec(body.transcript_text, body.requested_by, body.transcript_id)
    except Exception as exc:  # clean JSON error, never a stack trace
        return to_error_response(exc)


@router.post("/spec/resume")
def resume(body: ResumeRequest):
    """Resolve a paused possible-duplicate.

    PRODUCTION: a Slack button click hits the Slack app, which writes the
    warehouse; the same resume logic runs off that warehouse mutation.
    """
    try:
        return resume_spec(body.ref, body.choice)
    except Exception as exc:
        return to_error_response(exc)


@router.post("/regenerate")
def regenerate(body: RegenerateRequest):
    """Regenerate a NEW draft from a REJECTED spec (dedup is skipped).

    Feeds the deterministic rejection_reason (structured) + optional
    correction_context (semantic guidance) into the draft step. The old rejected
    spec is preserved for lineage + audit; the new draft returns in the SAME
    shape as /spec, so it flows back through /review -> /approve|/reject.
    Guard: only status='rejected' specs may be regenerated (else 409).
    correction_context > 500 chars -> clean 400.
    """
    try:
        return regenerate_spec(body.spec_id, body.requested_by, body.correction_context)
    except Exception as exc:
        return to_error_response(exc)


@router.post("/spec/delete")
def delete_spec(body: DeleteRequest):
    """Soft-delete a spec (status -> 'deleted'), guarded + audit-logged.

    Allowed only from 'draft' or 'rejected'. Approved specs cannot be deleted
    (they have spawned an opportunity; deletion would orphan the spine) -> 409.
    The row and its history remain; this only marks state.
    """
    try:
        return soft_delete_spec(body.spec_id, body.actor)
    except Exception as exc:
        return to_error_response(exc)
