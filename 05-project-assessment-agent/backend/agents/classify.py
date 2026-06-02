"""Agent 2a — the HYBRID classifier (the architecturally important component).

Three visibly separate layers:

  JUDGMENT (LLM)   -> canonical domain + task_type + confidence + reasoning,
                      chosen ONLY from the fixed enums.
  LOOKUP (det.)    -> capability_matrix.json gives (domain, task_type) -> color.
                      No LLM here, so the go/no-go call is auditable.
  DETECTORS        -> escalation flags that ALWAYS escalate regardless of color:
                        * deterministic: PII/regulated data, non-English
                        * LLM-judged: nonstandard platform, extreme complexity,
                          new audio/video modality

Plus a graceful confidence/escalation HOOK: low confidence, unresolved
domain/task_type, or a multi-project transcript sets needs_human_review with a
reason. It never crashes — it produces the rest of the assessment and surfaces
the flag (full edge-case handling is a later block).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import List, Optional, Set, Tuple

from pydantic import ValidationError

from config import (
    CONFIDENCE_THRESHOLD,
    DOMAINS,
    LOW_TEMP,
    MATRIX_PATH,
    TASK_TYPES,
    Domain,
    TaskType,
)

from agents.llm import complete_json, render_prompt
from agents.schemas import Classification, ClassificationLLM, Extraction

_SYSTEM = (
    "You are Lorefi's project classification assistant. Map a discovery call to "
    "exactly one canonical domain and one canonical task type from the provided "
    "lists. Return STRICT JSON only. Be honest about confidence."
)


# --- LOOKUP layer: deterministic matrix --------------------------------------
@lru_cache(maxsize=1)
def _load_matrix() -> Tuple[dict, Set[str]]:
    """Return ((domain, task_type) -> color) and the set of valid rule_ids."""
    data = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    order = data["task_type_order"]
    lookup = {}
    for domain, colors in data["matrix"].items():
        for task_type, color in zip(order, colors):
            lookup[(domain, task_type)] = color
    rule_ids = {rule["rule_id"] for rule in data["escalation_rules"]}
    return lookup, rule_ids


def matrix_color(domain: str, task_type: str) -> str:
    """Deterministic go/no-go color for a cell."""
    lookup, _ = _load_matrix()
    return lookup[(domain, task_type)]


# --- DETERMINISTIC escalation detectors --------------------------------------
# Heuristic PII/regulated-data scan. PRODUCTION would use a proper PII detector
# (e.g. Presidio); this keyword/regex pass is deliberately simple and auditable.
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD_RE = re.compile(r"\b(?:\d[ -]?){13,16}\b")
_PII_KEYWORDS = (
    "ssn", "social security", "phi", "hipaa", "medical record", "patient record",
    "protected health", "cardholder", "pci", "credit card", "passport number",
    "date of birth", "driver's license",
)


def detect_pii(transcript_text: str) -> bool:
    """True if the transcript shows PII/regulated-data signals."""
    if _SSN_RE.search(transcript_text) or _CARD_RE.search(transcript_text):
        return True
    low = transcript_text.lower()
    return any(keyword in low for keyword in _PII_KEYWORDS)


def detect_non_english(language: str) -> bool:
    """True if the data language is not English.

    Simple heuristic on Agent 1's ``language`` field. PRODUCTION would run a
    language-ID model (fastText / langid) over the actual data sample.
    """
    return not str(language or "en").strip().lower().startswith("en")


# --- helpers -----------------------------------------------------------------
def _resolve_enum(value: str, enum_cls) -> Optional[object]:
    """Best-effort map a free string onto a fixed enum member (exact, then loose)."""
    if not value:
        return None
    candidate = str(value).strip().lower()
    for member in enum_cls:
        if member.value.lower() == candidate:
            return member
    for member in enum_cls:  # loose containment, e.g. "labeling" -> "Data Labeling"
        if candidate in member.value.lower() or member.value.lower() in candidate:
            return member
    return None


# --- main entry point --------------------------------------------------------
def classify(extraction: Extraction, transcript_text: str) -> Classification:
    """Run the full hybrid and return a FINAL Classification."""
    _, valid_rule_ids = _load_matrix()

    # 1) JUDGMENT: LLM canonical classification. On parse/validation failure we
    #    fall back to Agent 1's candidates instead of crashing.
    llm: Optional[ClassificationLLM] = None
    try:
        raw = complete_json(_SYSTEM, _build_user_prompt(extraction, transcript_text), LOW_TEMP)
        llm = ClassificationLLM(**raw)
    except (RuntimeError, ValidationError):
        llm = None

    domain = (llm.domain if llm else None) or _resolve_enum(extraction.candidate_domain, Domain)
    task_type = (llm.task_type if llm else None) or _resolve_enum(
        extraction.candidate_task_type, TaskType
    )
    unresolved = domain is None or task_type is None

    # Flagged fallback (NOT a silent guess): default to the first enum so we can
    # still produce a valid, matrix-backed row, and raise needs_human_review below.
    if domain is None:
        domain = Domain(DOMAINS[0])
    if task_type is None:
        task_type = TaskType(TASK_TYPES[0])

    confidence = float(llm.confidence) if llm else 0.0
    reasoning = (
        llm.reasoning if llm and llm.reasoning
        else "LLM classification unavailable; used Agent 1 candidate domain/task_type."
    )

    # 2) LOOKUP: deterministic color.
    color = matrix_color(domain.value, task_type.value)

    # 3) DETECTORS: escalation flags (always escalate, independent of color).
    flags: List[str] = []
    if detect_pii(transcript_text):
        flags.append("pii_regulated")
    if detect_non_english(extraction.language):
        flags.append("non_english")
    if llm:
        for flag in llm.escalation_flags:
            if flag in valid_rule_ids and flag not in flags:
                flags.append(flag)

    # 4) HOOK: graceful confidence / escalation review trigger.
    reasons: List[str] = []
    if unresolved:
        reasons.append("could not confidently resolve domain/task_type")
    if confidence < CONFIDENCE_THRESHOLD:
        reasons.append(f"confidence {confidence:.2f} below threshold {CONFIDENCE_THRESHOLD}")
    if extraction.multi_project:
        reasons.append("multiple distinct projects discussed in one transcript")

    return Classification(
        domain=domain,
        task_type=task_type,
        color=color,
        confidence=confidence,
        reasoning=reasoning,
        escalation_flags=flags,
        needs_human_review=bool(reasons),
        review_reason="; ".join(reasons) if reasons else None,
    )


def _build_user_prompt(extraction: Extraction, transcript_text: str) -> str:
    return render_prompt(
        "classify.md",
        domains=", ".join(DOMAINS),
        task_types=", ".join(TASK_TYPES),
        signals=json.dumps(extraction.domain_signals),
        candidate_domain=extraction.candidate_domain or "(none)",
        candidate_task_type=extraction.candidate_task_type or "(none)",
        scope=json.dumps(extraction.scope),
        transcript=transcript_text,
    )
