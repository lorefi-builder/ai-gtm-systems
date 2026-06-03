"""CLI orchestrator — ties the whole pipeline together.

Usage:
    python -m agents.run <path-to-transcript.md>

Flow:
    read -> extract (Agent 1, writes stg) -> dedup -> classify (Agent 2a) ->
    estimate (Agent 2b) -> draft -> write fct_spec (status='draft') ->
    print Slack summary, then the draft spec.

It deliberately does NOT create opportunities — that's a later block. A single
bad transcript prints a clean error, not a stack trace.
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from db.client import insert

from agents.classify import classify
from agents.dedup import check_duplicate
from agents.draft import draft_spec
from agents.edge_cases import detect_edge_cases
from agents.estimate import run_estimate
from agents.extract import extract
from agents.format_slack import format_summary
from agents.schemas import Classification, ResourceEstimate


def run_pipeline(transcript_path: str) -> int:
    """Run the assessment pipeline for one transcript. Returns a process exit code."""
    path = Path(transcript_path)
    if not path.is_file():
        print(f"[error] transcript not found: {transcript_path}")
        return 1

    transcript_text = path.read_text(encoding="utf-8")
    raw_ref = str(path.resolve())

    try:
        print("[1/6] extracting signals (Agent 1)...")
        extraction = extract(transcript_text, raw_ref)

        print("[2/6] checking for duplicate specs...")
        dedup = check_duplicate(extraction)

        print("[3/6] classifying (hybrid: LLM + matrix + escalation)...")
        classification = classify(extraction, transcript_text)
        edge_cases = detect_edge_cases(extraction, classification)  # advisory only

        print("[4/6] estimating resources (verified facts + analogs)...")
        estimate = run_estimate(classification, extraction)

        print("[5/6] drafting spec (RAG-grounded)...")
        draft = draft_spec(extraction, classification, estimate)

        print("[6/6] writing fct_spec (status=draft)...")
        spec_id = _write_fct_spec(extraction, classification, estimate)

    except Exception as exc:  # one bad transcript -> clean message, no traceback dump
        print(f"\n[error] pipeline failed: {type(exc).__name__}: {exc}")
        return 1

    # --- output: Slack summary, then the draft spec --------------------------
    summary = format_summary(
        extraction, classification, estimate, dedup, spec_id, edge_cases
    )
    print("\n" + "=" * 72)
    print("SLACK SUMMARY")
    print("=" * 72)
    print(summary)

    print("\n" + "=" * 72)
    print("DRAFT SPEC")
    print("=" * 72)
    print(draft)
    return 0


def _write_fct_spec(
    extraction, classification: Classification, estimate: ResourceEstimate
) -> str:
    """Assemble and insert one draft fct_spec row; return its spec_id.

    spec_id is generated client-side so the Slack summary can reference it.
    """
    spec_id = str(uuid4())
    row = {
        "spec_id": spec_id,
        "transcript_id": extraction.transcript_id,
        "account_id": estimate.verified.account_id,          # VERIFIED
        "domain": classification.domain.value,               # JUDGMENT (canonical)
        "task_type": classification.task_type.value,         # JUDGMENT (canonical)
        "matrix_color": classification.color,                # LOOKUP
        "escalation_flags": classification.escalation_flags,
        "confidence": round(classification.confidence, 3),
        "ec_count": estimate.ec_count,
        "tdm_count": estimate.tdm_count,
        "dops_count": estimate.dops_count,
        "fde_count": estimate.fde_count,
        "resource_flags": estimate.resource_flags,
        "status": "draft",
    }
    insert("fct_spec", row)
    return spec_id


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m agents.run <path-to-transcript.md>")
        raise SystemExit(2)
    raise SystemExit(run_pipeline(sys.argv[1]))


if __name__ == "__main__":
    main()
