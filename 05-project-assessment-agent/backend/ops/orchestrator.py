"""Pipeline orchestration — stands in for warehouse-triggered jobs.

Runs the Block 2 agents in sequence. In PRODUCTION these steps are NOT a single
synchronous call: the `/spec` Slack slash command inserts a staging row, and a
Postgres LISTEN/NOTIFY trigger (or Supabase Edge Function / queue) fires dedup +
Agent 2 off the warehouse. Here FastAPI calls them inline; the warehouse writes
are identical either way.

CRITICAL: dedup runs REAL-TIME against the warehouse's own spec history and has
NO dependency on any Salesforce sync.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from uuid import uuid4

from config import DRAFT_MAX_TOKENS, DRAFT_TEMP
from db.client import insert, select

from agents.classify import classify
from agents.dedup import check_duplicate
from agents.edge_cases import detect_edge_cases
from agents.draft import _SYSTEM as _DRAFT_SYSTEM
from agents.draft import _format_examples, draft_spec
from agents.estimate import run_estimate
from agents.extract import extract
from agents.format_slack import format_summary
from agents.llm import complete_text, render_prompt
from agents.retrieval import retrieve_spec_examples
from agents.schemas import DedupResult, Extraction

from ops import slack_messages
from ops.lifecycle import LifecycleError, log_status, transition

# Dedup resume choices (echoed back from the Slack buttons).
CHOICE_PROCEED = "proceed"
CHOICE_LINK = "link"
CHOICE_ESCALATE = "escalate"


# --- POST /spec --------------------------------------------------------------
def run_spec(
    transcript_text: str, requested_by: str, transcript_id: Optional[str] = None
) -> Dict[str, Any]:
    """Extract -> real-time dedup -> (pause | assess+write). Returns a result dict.

    PRODUCTION: /spec is a Slack slash command; the stg insert triggers dedup +
    Agent 2 via LISTEN/NOTIFY. Dedup is real-time off the warehouse.
    """
    # Honor a caller-supplied transcript_id by surfacing it to the extractor the
    # same way the file format does (a "Transcript id:" line it already reads).
    text = transcript_text
    if transcript_id and "transcript id:" not in text.lower():
        text = f"Transcript id: {transcript_id}\n\n{text}"

    # Agent 1 writes stg_transcript_extracts. DEMO: we stash the raw transcript as
    # the raw_transcript_ref so /spec/resume can reload it from the warehouse;
    # PRODUCTION the raw transcript lives in object storage and this is a pointer.
    extraction = extract(text, raw_transcript_ref=text)

    # Real-time dedup against warehouse spec history (no sync dependency).
    dedup = check_duplicate(extraction)
    if dedup.is_possible_duplicate:
        # Pre-spec audit event (spec_id is null — no fct_spec exists yet).
        log_status(
            None,
            None,
            "dedup_paused",
            requested_by,
            f"possible duplicate of {dedup.match_spec_id} for transcript "
            f"{extraction.transcript_id}: {dedup.reason}",
        )
        return {
            "status": "paused_duplicate",
            "ref": extraction.transcript_id,
            "transcript_id": extraction.transcript_id,
            "dedup": dedup.model_dump(mode="json"),
            "slack_message": slack_messages.dedup_paused_message(
                requested_by, extraction.transcript_id, dedup
            ),
        }

    # Clean path: full assessment + write.
    return _assess_and_write(extraction, text, requested_by, dedup)


# --- POST /spec/resume -------------------------------------------------------
def resume_spec(ref: str, choice: str) -> Dict[str, Any]:
    """Implement the three dedup choices. ``ref`` is the transcript_id."""
    extraction = _load_extraction(ref)
    text = _load_raw_text(ref)
    requested_by = _lookup_requester(ref)

    if choice == CHOICE_PROCEED:
        # The human confirmed it's not a duplicate; assess as if clean.
        dedup = DedupResult(
            is_possible_duplicate=False,
            match_spec_id=None,
            reason="creator confirmed this is not a duplicate",
        )
        log_status(None, None, "dedup_proceed", requested_by, f"proceeded for transcript {ref}")
        return _assess_and_write(extraction, text, requested_by, dedup)

    if choice == CHOICE_LINK:
        # Associate with the existing spec and close; no new spec is created.
        dedup = check_duplicate(extraction)  # re-derive the match, real-time
        match_id = dedup.match_spec_id
        if match_id:
            match_rows = select("fct_spec", {"spec_id": match_id}, columns="status")
            from_status = match_rows[0].get("status") if match_rows else None
            log_status(
                match_id,
                from_status,
                "duplicate_linked",
                requested_by,
                f"transcript {ref} linked to existing spec {match_id}",
            )
        return {
            "status": "linked_duplicate",
            "ref": ref,
            "match_spec_id": match_id,
            "slack_message": slack_messages.link_confirm_message(ref, match_id),
        }

    if choice == CHOICE_ESCALATE:
        # Route to a human owner; pre-spec audit event.
        log_status(None, None, "escalated_to_tdm", requested_by, f"transcript {ref} escalated to TDM")
        return {
            "status": "escalated",
            "ref": ref,
            "slack_message": slack_messages.escalate_message(ref),
        }

    raise ValueError(f"unknown dedup choice '{choice}' (expected proceed|link|escalate)")


# --- shared assessment + write ----------------------------------------------
def _assess_and_write(
    extraction: Extraction, transcript_text: str, requested_by: str, dedup: DedupResult
) -> Dict[str, Any]:
    """classify -> estimate -> draft -> write fct_spec(draft). Returns result dict."""
    classification = classify(extraction, transcript_text)
    edge_cases = detect_edge_cases(extraction, classification)  # advisory only
    estimate = run_estimate(classification, extraction)
    draft = draft_spec(extraction, classification, estimate)

    spec_id = str(uuid4())  # client-side so we can reference it in the summary
    fct_spec_row = {
        "spec_id": spec_id,
        "transcript_id": extraction.transcript_id,
        "account_id": estimate.verified.account_id,        # VERIFIED (SQL)
        "domain": classification.domain.value,             # JUDGMENT (LLM, canonical)
        "task_type": classification.task_type.value,       # JUDGMENT (LLM, canonical)
        "matrix_color": classification.color,              # LOOKUP (matrix)
        "escalation_flags": classification.escalation_flags,
        "confidence": round(classification.confidence, 3),
        "ec_count": estimate.ec_count,
        "tdm_count": estimate.tdm_count,
        "dops_count": estimate.dops_count,
        "fde_count": estimate.fde_count,
        "resource_flags": estimate.resource_flags,
        "status": "draft",
        "needs_human_review": classification.needs_human_review,
        "review_reason": classification.review_reason,
        "requested_by": requested_by,
    }
    insert("fct_spec", fct_spec_row)

    summary_text = format_summary(
        extraction, classification, estimate, dedup, spec_id, edge_cases
    )
    return {
        "status": "draft_created",
        "spec_id": spec_id,
        "needs_human_review": classification.needs_human_review,
        "review_reason": classification.review_reason,
        "classification": classification.model_dump(mode="json"),
        "summary": summary_text,
        "draft_spec": draft,
        "slack_message": slack_messages.spec_summary_message(
            requested_by, summary_text, spec_id, classification
        ),
    }


# --- resume helpers (reload state from the warehouse) -----------------------
def _latest_stg(ref: str) -> Dict[str, Any]:
    rows = select(
        "stg_transcript_extracts", {"transcript_id": ref}, order="created_at.desc"
    )
    if not rows:
        raise ValueError(f"no staging extract found for ref '{ref}'")
    return rows[0]


def _load_extraction(ref: str) -> Extraction:
    """Rebuild the Extraction object from its staging row (incl. stashed fields)."""
    stg = _latest_stg(ref)
    dc = stg.get("data_characteristics") or {}
    clean_dc = {k: v for k, v in dc.items() if not k.startswith("_")}
    return Extraction(
        transcript_id=stg.get("transcript_id", ""),
        account_name=stg.get("account_name", ""),
        domain_signals=stg.get("domain_signals") or [],
        candidate_domain=dc.get("_candidate_domain", ""),
        candidate_task_type=stg.get("candidate_task_type", ""),
        data_characteristics=clean_dc,
        scope=stg.get("scope") or {},
        success_criteria=stg.get("success_criteria") or [],
        special_flags=stg.get("special_flags") or [],
        multi_project=bool(dc.get("_multi_project", False)),
        language=dc.get("_language", "en"),
    )


def _load_raw_text(ref: str) -> str:
    """Reload the raw transcript text the warehouse stashed at /spec time."""
    return _latest_stg(ref).get("raw_transcript_ref") or ""


def _lookup_requester(ref: str) -> str:
    """Recover the original requester from the dedup_paused audit row."""
    history = select(
        "spec_status_history", {"to_status": "dedup_paused"}, order="created_at.desc"
    )
    for row in history:
        if ref in (row.get("reason") or ""):
            return row.get("actor") or "(resume)"
    return "(resume)"


# --- POST /regenerate --------------------------------------------------------
def regenerate_spec(
    spec_id: str, requested_by: str, correction_context: Optional[str] = None
) -> Dict[str, Any]:
    """Regenerate a NEW draft from a REJECTED spec. Returns the /spec result shape.

    The old rejected spec is left untouched (preserves audit + lineage + the
    learning signal); a brand-new draft row is created with regenerated_from set.
    """
    # Validate the optional correction context server-side (<=500 chars).
    if correction_context is not None:
        correction_context = correction_context.strip()
        if len(correction_context) > 500:
            raise ValueError("correction_context must be 500 characters or fewer")
        correction_context = correction_context or None

    rows = select("fct_spec", {"spec_id": spec_id})
    if not rows:
        raise LifecycleError(f"spec {spec_id} not found")
    old = rows[0]
    if old.get("status") != "rejected":
        # Only rejected specs can be regenerated (guard -> clean 409).
        raise LifecycleError(
            f"spec {spec_id} is '{old.get('status')}'; only rejected specs can be regenerated"
        )

    rejection_reason = old.get("rejection_reason")          # VERIFIED (structured signal)
    transcript_id = old.get("transcript_id")
    transcript_text = _load_raw_text(transcript_id)         # same demo-shortcut as resume
    if not transcript_text:
        raise ValueError(
            f"no stored transcript text for '{transcript_id}'; cannot regenerate"
        )

    # Re-run the pipeline EXCEPT dedup. Dedup is intentionally skipped: a rejected
    # spec never became an approved/historical record, so there is nothing to
    # dedup against; regeneration is an explicit human-initiated retry.
    extraction = extract(transcript_text, raw_transcript_ref=transcript_text)
    classification = classify(extraction, transcript_text)
    edge_cases = detect_edge_cases(extraction, classification)  # advisory only
    estimate = run_estimate(classification, extraction)
    draft = _draft_with_correction(
        extraction, classification, estimate, rejection_reason, correction_context
    )

    new_spec_id = str(uuid4())
    insert(
        "fct_spec",
        {
            "spec_id": new_spec_id,
            "transcript_id": extraction.transcript_id,
            "account_id": estimate.verified.account_id,
            "domain": classification.domain.value,
            "task_type": classification.task_type.value,
            "matrix_color": classification.color,
            "escalation_flags": classification.escalation_flags,
            "confidence": round(classification.confidence, 3),
            "ec_count": estimate.ec_count,
            "tdm_count": estimate.tdm_count,
            "dops_count": estimate.dops_count,
            "fde_count": estimate.fde_count,
            "resource_flags": estimate.resource_flags,
            "status": "draft",
            "needs_human_review": classification.needs_human_review,
            "review_reason": classification.review_reason,
            "requested_by": requested_by,
            "regenerated_from": spec_id,                # lineage to the rejected original
            "correction_context": correction_context,
        },
    )

    # Audit the new draft's creation; the old spec stays 'rejected', untouched.
    log_status(
        new_spec_id,
        None,
        "draft",
        requested_by,
        f"regenerated from {spec_id} (rejection: {rejection_reason or 'n/a'})"
        + (f"; correction: {correction_context}" if correction_context else ""),
    )

    # No dedup ran, so the summary carries an explicit not-a-duplicate marker.
    dedup = DedupResult(
        is_possible_duplicate=False,
        match_spec_id=None,
        reason="regeneration — dedup intentionally skipped",
    )
    summary_text = format_summary(
        extraction, classification, estimate, dedup, new_spec_id, edge_cases
    )
    return {
        "status": "draft_created",
        "spec_id": new_spec_id,
        "regenerated_from": spec_id,
        "needs_human_review": classification.needs_human_review,
        "review_reason": classification.review_reason,
        "classification": classification.model_dump(mode="json"),
        "summary": summary_text,
        "draft_spec": draft,
        "slack_message": slack_messages.spec_summary_message(
            requested_by, summary_text, new_spec_id, classification
        ),
    }


def _draft_with_correction(
    extraction: Extraction,
    classification,
    estimate,
    rejection_reason: Optional[str],
    correction_context: Optional[str],
) -> str:
    """draft_spec, but with the rejection_reason + correction_context injected.

    Both are injected into the SAME prompt slot the RAG examples use, so the
    drafter treats them as additional contributor-style guidance. This mirrors
    the VERIFIED-vs-JUDGMENT split: rejection_reason is the structured signal,
    correction_context is the fuzzy/semantic guidance. (Reuses agents/draft.py
    pieces without modifying it.)
    """
    examples = retrieve_spec_examples(
        classification.domain.value, classification.task_type.value, extraction.scope
    )
    examples_block = _format_examples(examples)

    guidance_parts = []
    if rejection_reason:
        guidance_parts.append(
            "### Why the previous draft was rejected (structured signal)\n"
            f"The prior spec was rejected for: **{rejection_reason}**. "
            "Explicitly address and fix this in the new draft."
        )
    if correction_context:
        guidance_parts.append(
            "### Reviewer correction guidance (treat like contributor guidance)\n"
            f"{correction_context}"
        )
    # Put the correction guidance AHEAD of the retrieved examples so the drafter
    # sees the rejection_reason + correction_context first, then the RAG examples.
    guidance_block = "\n\n".join(guidance_parts)
    rag_blob = (guidance_block + "\n\n" + examples_block).strip() if guidance_parts else examples_block

    user = render_prompt(
        "draft.md",
        account=extraction.account_name or "the customer",
        domain=classification.domain.value,
        task_type=classification.task_type.value,
        color=classification.color,
        scope=json.dumps(extraction.scope, indent=2),
        requirements=json.dumps(extraction.data_characteristics, indent=2),
        success_criteria="\n".join(f"- {c}" for c in extraction.success_criteria)
        or "- (not specified)",
        resourcing=(
            f"EC {estimate.ec_count} · TDM {estimate.tdm_count} · "
            f"DOps {estimate.dops_count} · FDE {estimate.fde_count}"
        ),
        rag_examples=rag_blob,
    )
    return complete_text(_DRAFT_SYSTEM, user, DRAFT_TEMP, max_tokens=DRAFT_MAX_TOKENS)


# --- POST /spec/delete (soft delete) ----------------------------------------
def soft_delete_spec(spec_id: str, actor: str) -> Dict[str, Any]:
    """Soft-delete a draft or rejected spec. Never an approved one.

    The row and its spec_status_history stay; we only mark status='deleted'.
    spec_status_history IS our state-over-time record (every transition carries a
    timestamp + actor), so no separate SCD2 table is needed.
    """
    rows = select("fct_spec", {"spec_id": spec_id})
    if not rows:
        raise LifecycleError(f"spec {spec_id} not found")
    status = rows[0].get("status")
    if status == "approved":
        raise LifecycleError(
            f"spec {spec_id} is approved and has spawned an opportunity; deleting it "
            "would orphan the spec_lifecycle spine. Approved specs cannot be deleted."
        )
    if status == "deleted":
        raise LifecycleError(f"spec {spec_id} is already deleted")

    # Guarded transition (draft|rejected -> deleted) + audit row.
    transition(
        spec_id, "deleted", actor=actor, require_from=("draft", "rejected"), reason="soft delete"
    )
    return {"status": "deleted", "spec_id": spec_id}
