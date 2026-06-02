"""Draft-spec generation — RAG-grounded.

Retrieves RAG_K past spec_documents, then asks Claude (prompts/draft.md) to write
a draft spec in markdown following the case study's six sections exactly:

  1. Overview & Context
  2. Requirements (sample- and dataset-level)
  3. Contributor Guidelines
  4. Acceptance Criteria
  5. Deliverables & Format
  6. Timeline & Milestones (Pilot -> Production)

Grounded in the retrieved examples + extracted requirements + the assessment.
Returns markdown text (no DB writes here).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from config import DRAFT_MAX_TOKENS, DRAFT_TEMP

from agents.llm import complete_text, render_prompt
from agents.retrieval import retrieve_spec_examples
from agents.schemas import Classification, Extraction, ResourceEstimate

_SYSTEM = (
    "You are a Lorefi solutions architect drafting a project specification for an "
    "AI data-development engagement. Write a focused, customer-facing spec in "
    "markdown. Follow the six required sections exactly and in order. Ground every "
    "claim in the provided requirements and example specs; do not invent scope the "
    "customer did not ask for. Aim for roughly 3-4 pages."
)


def draft_spec(
    extraction: Extraction, classification: Classification, estimate: ResourceEstimate
) -> str:
    """Generate the RAG-grounded draft spec as markdown."""
    examples = retrieve_spec_examples(
        classification.domain.value, classification.task_type.value, extraction.scope
    )
    user = render_prompt(
        "draft.md",
        account=extraction.account_name or "the customer",
        domain=classification.domain.value,
        task_type=classification.task_type.value,
        color=classification.color,
        scope=json.dumps(extraction.scope, indent=2),
        requirements=json.dumps(extraction.data_characteristics, indent=2),
        success_criteria="\n".join(f"- {c}" for c in extraction.success_criteria) or "- (not specified)",
        resourcing=(
            f"EC {estimate.ec_count} · TDM {estimate.tdm_count} · "
            f"DOps {estimate.dops_count} · FDE {estimate.fde_count}"
        ),
        rag_examples=_format_examples(examples),
    )
    return complete_text(_SYSTEM, user, DRAFT_TEMP, max_tokens=DRAFT_MAX_TOKENS)


def _format_examples(examples: List[Dict[str, Any]]) -> str:
    """Render retrieved spec_documents as labelled context blocks."""
    if not examples:
        return "(no close historical examples found)"
    blocks = []
    for i, doc in enumerate(examples, start=1):
        blocks.append(
            f"### Example {i}: {doc.get('title', 'untitled')}\n{doc.get('body', '')}"
        )
    return "\n\n---\n\n".join(blocks)
