"""Agent 2b — resource estimation (VERIFIED facts + analog baseline + rules).

Two clearly separated layers:

  VERIFIED (SQL)  -> account resolution + prior-spec history, read straight from
                     the DB. If the account is unknown we insert a net_new stub
                     so the fct_spec FK holds, and flag "net-new account".
  ESTIMATE (det.) -> average ec/tdm/dops/fde across retrieve_analogs(), then apply
                     transparent RESOURCE-ADJUSTMENT rules (each flag names the
                     role it bumps and by how much, for auditability).

No LLM in this module — estimates are reproducible and explainable.
"""

from __future__ import annotations

import json
import re
from statistics import mean
from typing import Any, Dict, Iterable, List
from uuid import uuid4

from config import LARGE_SCOPE_THRESHOLD
from db.client import insert, select

from agents.retrieval import retrieve_analogs
from agents.schemas import (
    Classification,
    Extraction,
    ResourceAdjustment,
    ResourceEstimate,
    VerifiedAccountFacts,
)

# Fallback baseline when no analogs exist yet (e.g. a brand-new task type).
_DEFAULT_BASELINE = {"ec": 6.0, "tdm": 1.0, "dops": 1.0, "fde": 1.0}

# Defaults for a net-new account stub (kept conservative + obviously generic).
_STUB_DEFAULTS = {
    "segment": "Mid-Market",
    "tier": "Standard",
    "region": "NA",
    "owner": "unassigned@lorefi.com",
}


# --- VERIFIED layer ----------------------------------------------------------
def gather_verified_facts(account_name: str, domain: str) -> VerifiedAccountFacts:
    """Resolve the account and its prior-spec history from the DB.

    Exact-match on account_name (PRODUCTION would fuzzy-match). If not found,
    insert a net_new dim_account stub so downstream FKs hold.
    """
    matches = select("dim_account", {"account_name": account_name}) if account_name else []

    if matches:
        account = matches[0]
        account_id = account["account_id"]
        net_new = False
        relationship = account["relationship_status"]
        segment, region = account["segment"], account["region"]
        owner, tier = account["owner"], account.get("tier")
    else:
        account_id = str(uuid4())
        insert(
            "dim_account",
            {
                "account_id": account_id,
                "account_name": account_name or "Unknown (net-new)",
                "domain": domain,
                "segment": _STUB_DEFAULTS["segment"],
                "tier": _STUB_DEFAULTS["tier"],
                "region": _STUB_DEFAULTS["region"],
                "owner": _STUB_DEFAULTS["owner"],
                "relationship_status": "net_new",
            },
        )
        net_new = True
        relationship = "net_new"
        segment, region = _STUB_DEFAULTS["segment"], _STUB_DEFAULTS["region"]
        owner, tier = _STUB_DEFAULTS["owner"], _STUB_DEFAULTS["tier"]

    prior = select(
        "fct_spec", {"account_id": account_id}, columns="spec_id,status,rejection_reason"
    )
    approved = sum(1 for r in prior if r.get("status") == "approved")
    rejections = [
        r["rejection_reason"]
        for r in prior
        if r.get("status") == "rejected" and r.get("rejection_reason")
    ]

    return VerifiedAccountFacts(
        account_id=account_id,
        account_name=account_name or "Unknown (net-new)",
        found=bool(matches),
        net_new=net_new,
        relationship_status=relationship,
        segment=segment,
        region=region,
        owner=owner,
        tier=tier,
        prior_spec_count=len(prior),
        prior_approved_count=approved,
        prior_rejection_reasons=rejections,
    )


# --- ESTIMATE layer ----------------------------------------------------------
def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return float(mean(values)) if values else 0.0


def _max_number(objs: List[Any]) -> int:
    """Largest integer-looking number across the given objects (for volume)."""
    text = json.dumps(objs)
    nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]{2,}", text)]
    return max(nums) if nums else 0


def _strict_quality(success_criteria: List[str]) -> bool:
    """True if acceptance criteria look strict (kappa / F1 / high-accuracy etc.)."""
    blob = " ".join(success_criteria).lower()
    return any(kw in blob for kw in ("kappa", "f1", "accuracy", "agreement", "gold", "strict"))


def estimate_resources(
    classification: Classification, extraction: Extraction, verified: VerifiedAccountFacts
) -> ResourceEstimate:
    """Average an analog baseline, then apply transparent adjustment rules."""
    domain = classification.domain.value
    task_type = classification.task_type.value
    flags = set(classification.escalation_flags)

    # Analog baseline (carry the escalation flags so retrieval can rank by overlap).
    scope = dict(extraction.scope)
    scope["escalation_flags"] = classification.escalation_flags
    analogs = retrieve_analogs(domain, task_type, scope)

    if analogs:
        baseline = {
            "ec": _mean(a.get("ec_count", 0) for a in analogs),
            "tdm": _mean(a.get("tdm_count", 0) for a in analogs),
            "dops": _mean(a.get("dops_count", 0) for a in analogs),
            "fde": _mean(a.get("fde_count", 0) for a in analogs),
        }
    else:
        baseline = dict(_DEFAULT_BASELINE)

    counts = {role: round(value) for role, value in baseline.items()}
    adjustments: List[ResourceAdjustment] = []
    resource_flags: Dict[str, bool] = {}

    def bump(flag: str, role: str, delta: int, why: str) -> None:
        counts[role] += delta
        resource_flags[flag] = True
        adjustments.append(ResourceAdjustment(flag=flag, role=role, delta=delta, why=why))

    # --- transparent RESOURCE-ADJUSTMENT rules -------------------------------
    if "pii_regulated" in flags:
        bump("data_sensitivity", "dops", 1, "secure/compliant data handling overhead")
        bump("data_sensitivity", "fde", 1, "secure pipeline + access controls")
    if "non_english" in flags:
        bump("multilingual", "ec", 2, "language-qualified contributors + QA")
    if domain in ("Legal", "Healthcare"):
        bump("scarce_expertise", "ec", 2, f"{domain} requires scarce SME contributors")
        bump("scarce_expertise", "fde", 1, "domain-expert QA / adjudication")
    if _max_number([extraction.scope, extraction.data_characteristics]) >= LARGE_SCOPE_THRESHOLD:
        bump("large_scope", "ec", 3, "high sample volume needs more throughput")
    if "new_modality_av" in flags:
        bump("novel_modality", "fde", 1, "audio/video tooling integration")
        bump("novel_modality", "dops", 1, "new pipeline stand-up")
    if _strict_quality(extraction.success_criteria):
        bump("strict_quality", "tdm", 1, "tighter QA cadence / measurement")
        bump("strict_quality", "ec", 1, "redundant labeling for agreement targets")
    if classification.needs_human_review or len(extraction.success_criteria) < 2:
        bump("ambiguous_requirements", "tdm", 1, "extra scoping + oversight")
    if "nonstandard_platform" in flags:
        bump("nonstandard_platform", "fde", 1, "custom delivery / platform integration")

    # Floor each role to a sane minimum.
    counts["ec"] = max(2, counts["ec"])
    counts["tdm"] = max(1, counts["tdm"])
    counts["dops"] = max(1, counts["dops"])
    counts["fde"] = max(0, counts["fde"])

    return ResourceEstimate(
        ec_count=counts["ec"],
        tdm_count=counts["tdm"],
        dops_count=counts["dops"],
        fde_count=counts["fde"],
        adjustments=adjustments,
        resource_flags=resource_flags,
        analogs_used=[a["spec_id"] for a in analogs],
        baseline={k: round(v, 2) for k, v in baseline.items()},
        verified=verified,
    )


def run_estimate(classification: Classification, extraction: Extraction) -> ResourceEstimate:
    """Convenience: gather verified facts, then estimate."""
    verified = gather_verified_facts(extraction.account_name, classification.domain.value)
    return estimate_resources(classification, extraction, verified)
