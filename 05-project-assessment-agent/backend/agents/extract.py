"""Agent 1 — Extraction.

Reads a raw discovery transcript, asks Claude (prompts/extract.md) for a fixed
JSON shape, validates it into an ``Extraction``, and writes exactly one row to
``stg_transcript_extracts`` (the staging layer). Returns the validated object.
"""

from __future__ import annotations

import hashlib
import re

from config import DOMAINS, LOW_TEMP, TASK_TYPES
from db.client import insert

from agents.llm import complete_json, render_prompt
from agents.schemas import Extraction

_SYSTEM = (
    "You are Lorefi's discovery-call extraction agent. Lorefi is an AI "
    "data-development company (data labeling, model evaluation, content "
    "generation, etc.). Read a sales-discovery transcript and extract structured "
    "signals as STRICT JSON. Do not invent facts that are not in the transcript; "
    "use null/empty when something was not discussed."
)


def _slugify(text: str) -> str:
    """Lowercase kebab slug, trimmed — used to derive a transcript_id if absent."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40] or "transcript"


def extract(transcript_text: str, raw_transcript_ref: str) -> Extraction:
    """Run Agent 1 and persist the staging row."""
    user = render_prompt(
        "extract.md",
        transcript=transcript_text,
        domains=", ".join(DOMAINS),
        task_types=", ".join(TASK_TYPES),
    )
    raw = complete_json(_SYSTEM, user, LOW_TEMP)
    extraction = Extraction(**raw)

    # Derive a stable transcript_id if the model couldn't find one in the text.
    if not extraction.transcript_id:
        digest = hashlib.sha1(transcript_text.encode("utf-8")).hexdigest()[:8]
        extraction.transcript_id = f"{_slugify(extraction.account_name)}-{digest}"

    _write_staging_row(extraction, raw_transcript_ref)
    return extraction


def _write_staging_row(extraction: Extraction, raw_transcript_ref: str) -> None:
    """Insert one row into stg_transcript_extracts.

    The table has fewer columns than the Extraction model, so the in-memory-only
    fields (language, multi_project, candidate_domain) are preserved inside the
    ``data_characteristics`` jsonb under underscored keys — lossless, no schema change.
    """
    data_characteristics = dict(extraction.data_characteristics)
    data_characteristics.update(
        {
            "_language": extraction.language,
            "_multi_project": extraction.multi_project,
            "_candidate_domain": extraction.candidate_domain,
        }
    )

    row = {
        "transcript_id": extraction.transcript_id,
        "account_name": extraction.account_name,
        "domain_signals": extraction.domain_signals,
        "candidate_task_type": extraction.candidate_task_type,
        "data_characteristics": data_characteristics,
        "scope": extraction.scope,
        "success_criteria": extraction.success_criteria,
        "special_flags": extraction.special_flags,
        "raw_transcript_ref": raw_transcript_ref,
    }
    insert("stg_transcript_extracts", row)
