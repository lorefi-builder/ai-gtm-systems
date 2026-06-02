"""Central configuration for the Project Assessment Agent (Block 2: the AI core).

Single source of truth for the model name, temperatures, thresholds, and the
fixed enums. Change the model in ONE place (`CLAUDE_MODEL`) to swap it everywhere.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

# --- model + sampling --------------------------------------------------------
# One-line swap point for the whole pipeline.
CLAUDE_MODEL = "claude-sonnet-4-6"

LOW_TEMP = 0.0      # deterministic work: extraction + classification
DRAFT_TEMP = 0.4    # spec drafting gets a little room to write prose

MAX_OUTPUT_TOKENS = 4096   # JSON responses (extract / classify)
DRAFT_MAX_TOKENS = 8192    # ~3-4 page markdown spec

# --- thresholds / k values ---------------------------------------------------
CONFIDENCE_THRESHOLD = 0.65   # below this -> needs_human_review
ANALOG_K = 5                  # historical fct_spec rows averaged for a baseline
RAG_K = 3                     # past spec_documents retrieved for drafting

DEDUP_SIMILARITY = 0.40       # scope-overlap above this -> possible duplicate
LARGE_SCOPE_THRESHOLD = 50_000  # sample volume that trips the "large scope" flag

# --- paths -------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
MATRIX_PATH = BACKEND_DIR / "matrix" / "capability_matrix.json"
PROMPTS_DIR = BACKEND_DIR / "prompts"


# --- fixed enums (MUST match schema.sql checks + capability_matrix.json) ------
class Domain(str, Enum):
    """The six industries Lorefi serves. Values match the schema/matrix exactly."""

    TECHNOLOGY = "Technology"
    FINANCIAL_SERVICES = "Financial Services"
    HEALTHCARE = "Healthcare"
    LEGAL = "Legal"
    RETAIL = "Retail"
    GOVERNMENT = "Government"


class TaskType(str, Enum):
    """The six task types in the capability matrix."""

    DATA_LABELING = "Data Labeling"
    MODEL_EVAL = "Model Eval"
    CONTENT_GEN = "Content Gen"
    CONVERSATIONAL_AI = "Conversational AI"
    DOC_PROCESS = "Doc Process"
    CODE_REVIEW = "Code Review"


# Convenience lists for prompts and validation messages.
DOMAINS = [d.value for d in Domain]
TASK_TYPES = [t.value for t in TaskType]
