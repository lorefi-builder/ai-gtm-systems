"""Slack-faithful message builders.

Each function returns a structured dict shaped like a Slack Block Kit payload
(channel + fallback text + blocks with buttons). NOTHING is posted anywhere —
Block 4 renders these, and in PRODUCTION a Slack app posts them. Button
``value`` fields carry the JSON the UI echoes back to the resume/review/approve
endpoints, so every action round-trips through the warehouse.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from agents.schemas import Classification, DedupResult

# Channel placeholders (the demo doesn't post; these document intended routing).
_REVIEW_CHANNEL = "#spec-review"
_DEAL_CHANNEL = "#deal-tracking"


def _button(
    text: str, action_id: str, value: str, style: Optional[str] = None
) -> Dict[str, Any]:
    btn: Dict[str, Any] = {
        "type": "button",
        "text": {"type": "plain_text", "text": text},
        "action_id": action_id,
        "value": value,
    }
    if style:
        btn["style"] = style  # "primary" | "danger"
    return btn


def _section(markdown: str) -> Dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": markdown}}


# --- /spec : possible-duplicate pause ---------------------------------------
def dedup_paused_message(
    requested_by: str, transcript_id: str, dedup: DedupResult
) -> Dict[str, Any]:
    """Paused message with THREE actionable options the UI renders as buttons."""
    # Structured options (easy for the UI) + Slack action buttons (faithful).
    options: List[Dict[str, str]] = [
        {"label": "Not a duplicate — proceed anyway", "choice": "proceed", "style": "primary"},
        {"label": "Duplicate — link to existing spec", "choice": "link", "style": ""},
        {"label": "Unsure — escalate to a TDM", "choice": "escalate", "style": "danger"},
    ]
    buttons = [
        _button(
            o["label"],
            action_id=f"dedup_{o['choice']}",
            value=json.dumps({"ref": transcript_id, "choice": o["choice"]}),
            style=o["style"] or None,
        )
        for o in options
    ]
    return {
        "channel": f"@{requested_by}",
        "text": f":warning: Possible duplicate of spec `{dedup.match_spec_id}` — paused for your call.",
        "blocks": [
            _section(
                f":warning: *Possible duplicate detected.*\n{dedup.reason}\n\n"
                f"Matched spec: `{dedup.match_spec_id}`. How should we proceed?"
            ),
            {"type": "actions", "elements": buttons},
        ],
        "options": options,            # convenience for the UI
        "ref": transcript_id,
    }


# --- /spec : clean draft summary --------------------------------------------
def spec_summary_message(
    requested_by: str, summary_text: str, spec_id: str, classification: Classification
) -> Dict[str, Any]:
    """The assessment summary + a 'Send to review' action."""
    return {
        "channel": f"@{requested_by}",
        "text": summary_text,
        "blocks": [
            _section(summary_text),
            {
                "type": "actions",
                "elements": [
                    _button(
                        "Send to review",
                        action_id="send_to_review",
                        value=json.dumps({"spec_id": spec_id}),
                        style="primary",
                    )
                ],
            },
        ],
        "spec_id": spec_id,
        "needs_human_review": classification.needs_human_review,
    }


# --- /review : routed to reviewers ------------------------------------------
def review_routed_message(spec_id: str, requested_by: str) -> Dict[str, Any]:
    """Posted to the review channel, tagging approver placeholders."""
    return {
        "channel": _REVIEW_CHANNEL,
        "text": f"Spec `{spec_id}` is ready for review (from @{requested_by}).",
        "blocks": [
            _section(
                f"*Review requested* by @{requested_by}\n"
                f"Spec `{spec_id}` is now *in review*. Approvers: "
                f"@tdm-oncall · @solutions-lead"
            ),
            {
                "type": "actions",
                "elements": [
                    _button(
                        "Approve",
                        action_id="approve_spec",
                        value=json.dumps({"spec_id": spec_id}),
                        style="primary",
                    ),
                    _button(
                        "Reject",
                        action_id="reject_spec",
                        value=json.dumps({"spec_id": spec_id}),
                        style="danger",
                    ),
                ],
            },
        ],
        "spec_id": spec_id,
    }


# --- /approve : opportunity tracking ----------------------------------------
def approved_opp_message(
    spec_id: str, opportunity_id: str, actor: str, opportunity: Dict[str, Any]
) -> Dict[str, Any]:
    """Posted to the deal-tracking channel once an opportunity exists."""
    amount = opportunity.get("amount", 0)
    return {
        "channel": _DEAL_CHANNEL,
        "text": f":white_check_mark: Spec `{spec_id}` approved by @{actor} — opportunity created.",
        "blocks": [
            _section(
                f":white_check_mark: *Spec approved* by @{actor}\n"
                f"Opportunity `{opportunity_id}` created at *Discovery*.\n"
                f"*{opportunity.get('name', '')}* — "
                f"{opportunity.get('segment', '')} / {opportunity.get('region', '')} · "
                f"${amount:,.0f} · owner {opportunity.get('owner', '')}"
            )
        ],
        "spec_id": spec_id,
        "opportunity_id": opportunity_id,
    }


# --- /reject : back to the creator with next steps --------------------------
def rejected_message(spec_id: str, actor: str, reason: str) -> Dict[str, Any]:
    """Sent to the creator with the reason + suggested next steps."""
    next_steps = [
        "Regenerate with /regenerate — optionally add correction context to steer the redraft",
        "Split a multi-project transcript into separate specs",
        "Schedule a scoping call to tighten requirements",
    ]
    return {
        "channel": "@creator",
        "text": f":x: Spec `{spec_id}` was rejected by @{actor}.",
        "blocks": [
            _section(
                f":x: *Spec `{spec_id}` rejected* by @{actor}\n*Reason:* {reason}"
            ),
            _section("*Suggested next steps:*\n"
                     + "\n".join(f"• {s}" for s in next_steps)),
        ],
        "spec_id": spec_id,
        "reason": reason,
        "next_steps": next_steps,
    }


# --- /spec/resume : link + escalate confirmations ---------------------------
def link_confirm_message(ref: str, match_spec_id: Optional[str]) -> Dict[str, Any]:
    return {
        "channel": "@creator",
        "text": f"Linked transcript `{ref}` to existing spec `{match_spec_id}`. No new spec created.",
        "blocks": [
            _section(
                f":link: Transcript `{ref}` linked to existing spec "
                f"`{match_spec_id}`. No new spec was created."
            )
        ],
        "ref": ref,
        "match_spec_id": match_spec_id,
    }


def escalate_message(ref: str) -> Dict[str, Any]:
    return {
        "channel": _REVIEW_CHANNEL,
        "text": f"Transcript `{ref}` escalated to a TDM for a duplicate call.",
        "blocks": [
            _section(
                f":raised_hand: Transcript `{ref}` escalated to a TDM "
                f"(@tdm-oncall) to confirm whether it duplicates an existing spec."
            )
        ],
        "ref": ref,
    }
