"""Slack-style summary formatter.

Builds the structured summary the case study's "post a Slack summary" step asks
for, as a plain string. Block 3 will actually post it; here we just return text.
"""

from __future__ import annotations

from typing import Any, Dict

from agents.schemas import Classification, DedupResult, Extraction, ResourceEstimate

_COLOR_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}


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
    if risks:
        lines.append("• *Risks / review:*")
        lines.extend(f"    {r}" for r in risks)
    else:
        lines.append("• *Risks / review:* none flagged")

    # • Links
    lines.append(f"• *Links:* spec_id `{spec_id}` (live links added in Block 3)")

    return "\n".join(lines)
