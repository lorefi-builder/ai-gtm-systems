"""Pydantic models for every structured output in the pipeline.

Pydantic gives us validation at each hand-off: the LLM's JSON is parsed into a
typed object or it fails loudly (and the caller decides how to recover). Written
for Python 3.9 + pydantic v2 — note we use ``Optional[...]`` (not ``X | None``)
so the annotations evaluate on 3.9.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from config import Domain, TaskType


# --- Agent 1 : extraction ----------------------------------------------------
class Extraction(BaseModel):
    """Structured signals pulled from one discovery transcript by Agent 1.

    Richer than the ``stg_transcript_extracts`` table — the extra fields
    (candidate_domain, multi_project, language) travel in-memory through the
    pipeline and are persisted inside ``data_characteristics`` (see extract.py).
    """

    transcript_id: str = ""
    account_name: str = ""
    domain_signals: List[str] = Field(default_factory=list)
    candidate_domain: str = ""          # Agent 1's guess; classify.py canonicalizes
    candidate_task_type: str = ""       # Agent 1's guess; classify.py canonicalizes
    data_characteristics: Dict[str, Any] = Field(default_factory=dict)
    scope: Dict[str, Any] = Field(default_factory=dict)
    success_criteria: List[str] = Field(default_factory=list)
    special_flags: List[str] = Field(default_factory=list)
    multi_project: bool = False         # more than one distinct project discussed?
    language: str = "en"

    @field_validator(
        "domain_signals", "success_criteria", "special_flags", mode="before"
    )
    @classmethod
    def _none_to_list(cls, v: Any) -> Any:
        return v if v is not None else []

    @field_validator("data_characteristics", "scope", mode="before")
    @classmethod
    def _none_to_dict(cls, v: Any) -> Any:
        return v if v is not None else {}

    @field_validator(
        "transcript_id", "account_name", "candidate_domain", "candidate_task_type",
        mode="before",
    )
    @classmethod
    def _none_to_str(cls, v: Any) -> Any:
        return v if v is not None else ""

    @field_validator("language", mode="before")
    @classmethod
    def _none_to_en(cls, v: Any) -> Any:
        return v if v else "en"


# --- Agent 2a : classification ----------------------------------------------
class ClassificationLLM(BaseModel):
    """RAW output of the LLM classification step (the JUDGMENT layer).

    ``domain``/``task_type`` are constrained to the fixed enums — if the model
    returns anything off-enum this fails validation and classify.py falls back
    gracefully rather than crashing.
    """

    domain: Domain
    task_type: TaskType
    confidence: float
    reasoning: str = ""
    # LLM-judged escalation flags only (deterministic ones are added in code):
    escalation_flags: List[str] = Field(default_factory=list)

    @field_validator("escalation_flags", mode="before")
    @classmethod
    def _none_to_list(cls, v: Any) -> Any:
        return v if v is not None else []


class Classification(BaseModel):
    """FINAL classification combining all three layers.

    color comes from the deterministic matrix LOOKUP; escalation_flags merge the
    deterministic detectors with the LLM-judged ones; needs_human_review is the
    graceful confidence/escalation hook.
    """

    domain: Domain
    task_type: TaskType
    color: str                              # green | yellow | red (matrix lookup)
    confidence: float
    reasoning: str
    escalation_flags: List[str] = Field(default_factory=list)
    needs_human_review: bool = False
    review_reason: Optional[str] = None


# --- Agent 2b : verified facts + estimate -----------------------------------
class VerifiedAccountFacts(BaseModel):
    """VERIFIED layer: facts read straight from the DB, never from the LLM."""

    account_id: str
    account_name: str
    found: bool
    net_new: bool
    relationship_status: str
    segment: str
    region: str
    owner: str
    tier: Optional[str] = None
    prior_spec_count: int = 0
    prior_approved_count: int = 0
    prior_rejection_reasons: List[str] = Field(default_factory=list)


class ResourceAdjustment(BaseModel):
    """One transparent resourcing bump: which flag fired, which role, how much."""

    flag: str
    role: str           # ec | tdm | dops | fde
    delta: int
    why: str


class ResourceEstimate(BaseModel):
    """Analog-based resource estimate + the audit trail behind it.

    Verified facts are kept in their own field so the deterministic SQL truth is
    never blurred with the estimated headcount.
    """

    ec_count: int
    tdm_count: int
    dops_count: int
    fde_count: int
    adjustments: List[ResourceAdjustment] = Field(default_factory=list)
    resource_flags: Dict[str, bool] = Field(default_factory=dict)
    analogs_used: List[str] = Field(default_factory=list)     # fct_spec.spec_id values
    baseline: Dict[str, float] = Field(default_factory=dict)  # averaged analog counts
    verified: VerifiedAccountFacts


# --- dedup -------------------------------------------------------------------
class DedupResult(BaseModel):
    """Non-blocking duplicate check; surfaced in the summary for a human."""

    is_possible_duplicate: bool
    match_spec_id: Optional[str] = None
    reason: str
