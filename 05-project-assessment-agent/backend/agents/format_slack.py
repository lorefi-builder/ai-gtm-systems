"""Slack-style summary formatter.

Builds the structured summary the case study's "post a Slack summary" step asks
for, as a plain string. Block 3 will actually post it; here we just return text.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.schemas import (
    Classification,
    DedupResult,
    EdgeCaseFlag,
    Extraction,
    ResourceEstimate,
)

_COLOR_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
# Per-tier emoji for the advisory edge-case block (1 most structural → 3 least).
_EDGE_EMOJI = {1: "📑", 2: "❓", 3: "📭"}


def _scope_oneliner(scope: Dict[str, Any]) -> str:
    """One short line summarizing scope (first couple of values)."""
    if not scope:
        return "scope not specified"
    parts = [f"{k}: {v}" for k, v in list(scope.items())[:3]]
    return "; ".join(parts)


def _first_sentence(text: str, limit: int = 160) -> str:
    text = (text or "").strip().replace("\n", " ")
    head = text.split(". ")[0]
    return (head[:limit] + "…") if len(head) > limit else head


def format_summary(
    extraction: Extraction,
    classification: Classification,
    estimate: ResourceEstimate,
    dedup: DedupResult,
    spec_id: str,
    edge_cases: Optional[List[EdgeCaseFlag]] = None,
) -> str:
    """Return the Slack-style assessment summary as a plain string."""
    color = classification.color
    emoji = _COLOR_EMOJI.get(color, "⚪")
    lines = ["*Project Assessment — Draft Spec Ready*", ""]

    # • Project summary
    lines.append(
        f"• *Project:* {extraction.account_name or 'Unknown account'} — "
        f"{classification.domain.value} × {classification.task_type.value}"
    )
    lines.append(f"    _{_scope_oneliner(extraction.scope)}_")

    # • Classification
    lines.append(
        f"• *Classification:* {emoji} {color.upper()} — "
        f"{_first_sentence(classification.reasoning)}"
    )
    if classification.escalation_flags:
        lines.append(f"    ⚠️ Escalation flags: {', '.join(classification.escalation_flags)}")

    # • Resource estimate
    lines.append(
        f"• *Resourcing:* EC {estimate.ec_count} · TDM {estimate.tdm_count} · "
        f"DOps {estimate.dops_count} · FDE {estimate.fde_count}"
    )
    if estimate.adjustments:
        bumps = ", ".join(
            f"{a.flag} (+{a.delta} {a.role})" for a in estimate.adjustments
        )
        lines.append(f"    Adjusted by: {bumps}")

    # • Risks / review
    risks = []
    if classification.needs_human_review:
        risks.append(f"🔎 Needs human review — {classification.review_reason}")
    if dedup.is_possible_duplicate:
        risks.append(f"♻️ Possible duplicate — {dedup.reason}")
    if estimate.verified.net_new:
        risks.append("🆕 Net-new account (stub created in dim_account)")
    else:
        # Returning account: surface the Salesforce/warehouse enrichment (prior
        # specs, approvals, and the most recent rejection reason if any).
        v = estimate.verified
        line = (
            f"🔁 Returning account — {v.prior_spec_count} prior specs "
            f"({v.prior_approved_count} approved)"
        )
        if v.prior_rejection_reasons:
            line += f", last rejected for: {v.prior_rejection_reasons[-1]}"
        risks.append(line)
    if risks:
        lines.append("• *Risks / review:*")
        lines.extend(f"    {r}" for r in risks)
    else:
        lines.append("• *Risks / review:* none flagged")

    # • Edge cases (advisory) — deliberately visually distinct from the policy
    # "Escalation flags" and "Needs human review" lines above. These never change
    # the verdict; they're reviewer nudges, rendered tier-ascending.
    if edge_cases:
        lines.append("📋 *Edge cases (advisory)*")
        for ec in sorted(edge_cases, key=lambda e: e.tier):
            emoji = _EDGE_EMOJI.get(ec.tier, "•")
            lines.append(f"    {emoji} Tier {ec.tier} · {ec.label} — {ec.suggestion}")

    # • Links
    lines.append(f"• *Links:* spec_id `{spec_id}` (live links added in Block 3)")

    return "\n".join(lines)
