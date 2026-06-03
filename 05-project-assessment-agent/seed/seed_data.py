"""Seed the Project Assessment Agent demo with fictional Lorefi data.

Generates a self-consistent dataset and INSERTS it into Supabase via the
PostgREST client in ``backend/db/client.py``. It does **not** run on import —
run it yourself once the schema is applied and ``.env`` is filled:

    python seed/seed_data.py

What it creates (all fictional — Lorefi + invented customers):
    * 59 customer accounts across 6 domains
    * the 36-cell capability matrix + 5 escalation rules (from the JSON)
    * 12 full ~1-page RAG spec documents
    * 500 fct_spec rows over the last 6 months: a deterministic Demand-Intelligence
      cohort of ~32 RED/escalated specs (guaranteed heatmap cells, emitted first)
      plus ~468 organic specs. Organic status mix is weighted
      ~56% approved / 20% in_review / 14% draft / 10% rejected; the cohort skews
      ~55% approved / 30% rejected / 10% in_review / 5% draft.
    * ~one fct_opportunity per approved spec (~55% close-gated funnel + varied win
      rates), with stage history for velocity
    * one spec_lifecycle spine row per spec (IDs consistent across tables)

The whole run is deterministic (fixed seed + a fixed "now"), so re-running
produces the same ids and the same numbers.
"""

from __future__ import annotations

import datetime as dt
import json
import random
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx

# --- make backend importable -------------------------------------------------
HERE = Path(__file__).resolve().parent          # .../05-project-assessment-agent/seed
ROOT = HERE.parent                              # .../05-project-assessment-agent
BACKEND = ROOT / "backend"
MATRIX_JSON = BACKEND / "matrix" / "capability_matrix.json"
sys.path.insert(0, str(BACKEND))

from db import client as dbclient  # noqa: E402  (reuse config/headers for clears)
from db.client import insert, upsert  # noqa: E402  (after sys.path tweak)

# --- determinism -------------------------------------------------------------
SEED = 4207
rng = random.Random(SEED)

# Fixed reference "now" so created_at spreads are reproducible. Matches the
# demo's notional current date.
NOW = dt.datetime(2026, 6, 1, 12, 0, tzinfo=dt.timezone.utc)
SIX_MONTHS_DAYS = 180

# --- domain / reference constants -------------------------------------------
DOMAINS = [
    "Technology",
    "Financial Services",
    "Healthcare",
    "Legal",
    "Retail",
    "Government",
]
SEGMENTS = ["Enterprise", "Mid-Market", "SMB"]
REGIONS = ["NA", "EMEA", "APAC", "LATAM"]
OWNERS = [
    "dana.okafor@lorefi.com",
    "sam.petrov@lorefi.com",
    "mara.lindqvist@lorefi.com",
    "theo.nguyen@lorefi.com",
    "priya.rao@lorefi.com",
    "jules.bernard@lorefi.com",
]

REJECTION_REASONS = [
    "missing_acceptance_criteria",
    "scope_too_broad",
    "wrong_task_type",
    "insufficient_contributor_guidelines",
    "data_sensitivity_unaddressed",
]

# Relative difficulty per domain — scales resourcing and dampens confidence.
DIFFICULTY: dict[str, float] = {
    "Technology": 1.00,
    "Retail": 1.05,
    "Financial Services": 1.30,
    "Legal": 1.50,
    "Healthcare": 1.60,
    "Government": 1.90,
}

# Fictional customer names per domain (no real companies). 10 per domain = 60
# accounts, so ~240 specs spread to ~4/account (no account carries an absurd load).
ACCOUNT_NAMES: dict[str, list[str]] = {
    "Technology": [
        "Meridian Synth", "Cobalt Stack", "Nimbus Forge", "Quanta Labs",
        "Vellum AI", "Driftwave Systems", "Pixelford", "Halcyon Compute",
        "Stratos Data", "Inkwell Compute",
    ],
    "Financial Services": [
        "Sterling Vale Capital", "Brightmark Financial", "Northcourt Bank",
        "Aurelia Payments", "Tideline Securities", "Cobblestone Mutual",
        "Veracity Lending", "Granite Trust", "Mercato Capital",
        "Beacon Hill Savings",
    ],
    # NOTE: "Cedarbrook Health" intentionally omitted — it is a live-demo hero
    # account and must have NO pre-seeded specs so the demo is a clean first run.
    "Healthcare": [
        "Vantage Medical", "Lumicare Diagnostics",
        "Northwind Bio", "Solace Health Systems", "Marrow Labs",
        "Evergreen Clinics", "Brightpath Care", "Helix Diagnostics",
        "Meadowlark Health",
    ],
    "Legal": [
        "Ashford & Lane", "Holloway Legal", "Pinnacle Counsel", "Brevia Law",
        "Castlewood Partners", "Meridian Counsel Group", "Wexford & Reed",
        "Stonegate Law", "Ardent Counsel", "Calderon Partners",
    ],
    "Retail": [
        "Foxglove Retail", "Harborline Goods", "Tumbleweed Outfitters",
        "Saffron Market", "Brightcart", "Wren & Co", "Lakeshore Supply",
        "Driftwood Goods", "Marigold Market", "Copperline Retail",
    ],
    "Government": [
        "Capitol Ridge Agency", "Civic Path Authority", "Statewide Records Office",
        "Harbor County Services", "Meridian Public Works", "National Civic Bureau",
        "Riverside Municipal Authority", "Cascade Public Records",
        "Granger County Services", "Federal Heritage Office",
    ],
}

# Win-rate model so the dashboard shows real segment x region differences.
WIN_BASE: dict[str, float] = {"Enterprise": 0.55, "Mid-Market": 0.45, "SMB": 0.35}
WIN_REGION_MOD: dict[str, float] = {"NA": 0.08, "EMEA": 0.00, "APAC": -0.05, "LATAM": -0.10}

# Indicative deal sizes (USD) by segment.
AMOUNT_RANGE: dict[str, tuple[int, int]] = {
    "Enterprise": (180_000, 620_000),
    "Mid-Market": (60_000, 210_000),
    "SMB": (15_000, 72_000),
}

# Annual contract value (revenue) ranges by segment — distinct from pipeline
# `amount`. ACV drives the Block 5C revenue charts.
ACV_RANGE: dict[str, tuple[int, int]] = {
    "Enterprise": (160_000, 520_000),
    "Mid-Market": (55_000, 190_000),
    "SMB": (14_000, 65_000),
}

# Estimated deal value at discovery — set on EVERY spec (all statuses), so
# declined/escalated demand carries a dollar figure (fct_opportunity.amount only
# exists for approved specs). Sized by the SAME segment ranges + fde bump as the
# opportunity amount (build_opportunities), so an approved spec's estimate is the
# same ballpark as the amount its opportunity eventually gets.
#
# It draws from a SEPARATE, independently-seeded RNG so adding it does NOT perturb
# the main `rng` stream: every protected count (500 specs / 274 opps / 74 won /
# the DI cohort / stage history) stays byte-identical to before this change.
_est_rng = random.Random(SEED + 100)


def estimate_value(segment: str, fde_count: int) -> float:
    """Plausible discovery-time deal value for a spec, by the account's segment.
    Mirrors build_opportunities' amount formula but on the independent _est_rng."""
    lo, hi = AMOUNT_RANGE[segment]
    return round(_est_rng.uniform(lo, hi) * (1 + 0.05 * fde_count), -3)

# Win-type mix on Closed Won opps. new_logo is the plurality everywhere; renewal
# is second (and Enterprise skews renewal-heavy); the other two are smaller.
WIN_TYPE_WEIGHTS: dict[str, dict[str, float]] = {
    "Enterprise": {"new_logo": 0.38, "renewal": 0.34, "prior_loss_now_won": 0.16, "reactivation": 0.12},
    "Mid-Market": {"new_logo": 0.46, "renewal": 0.26, "prior_loss_now_won": 0.16, "reactivation": 0.12},
    "SMB":        {"new_logo": 0.52, "renewal": 0.18, "prior_loss_now_won": 0.15, "reactivation": 0.15},
}

# ACV multiplier by win type so "revenue per win type" is a real story:
# new_logo deals largest on average, renewals smaller, reactivation smallest.
WIN_TYPE_ACV_MULT: dict[str, float] = {
    "new_logo": 1.25,
    "prior_loss_now_won": 1.05,
    "renewal": 0.85,
    "reactivation": 0.70,
}

# Opportunity stage path + stage velocity.
OPEN_STAGES = ["Discovery", "Proposal", "Negotiation"]
_SEGMENT_VELOCITY_FACTOR = {"Enterprise": 1.4, "Mid-Market": 1.0, "SMB": 0.8}

# Journey-variation probabilities for stage history (deterministic, seed=4207).
# Most deals keep the full linear path Discovery->Proposal->Negotiation->terminal;
# a minority vary. These gate ONLY the intermediate path — opp["stage"], is_won,
# win_type, amount and created_at are never touched, so all headline numbers
# (500 specs / 274 opps / 74 won / closed-won total / DI cohort) are preserved.
P_SKIP_PROPOSAL = 0.18      # Discovery->Negotiation, bypassing Proposal
P_LOST_AT_DISCOVERY = 0.12  # Closed Lost exits straight from Discovery
P_LOST_AT_PROPOSAL = 0.18   # Closed Lost exits from Proposal (no Negotiation)
P_WON_FROM_PROPOSAL = 0.20  # Closed Won closes from Proposal (no Negotiation)

# Day-gap bounds keyed by the ACTUAL (from -> to) transition. A Discovery->
# Negotiation skip spans roughly the two gaps it bypasses; early closes are
# moderate. Used by build_stage_history; falls back to (7, 21) if a pair is absent.
_STAGE_GAP_MAP: dict[tuple[str, str], tuple[int, int]] = {
    ("Discovery", "Proposal"): (5, 18),
    ("Proposal", "Negotiation"): (7, 21),
    ("Negotiation", "Closed Won"): (7, 30),
    ("Negotiation", "Closed Lost"): (7, 30),
    ("Discovery", "Negotiation"): (12, 39),   # Proposal skipped (~ sum of bypassed gaps)
    ("Discovery", "Closed Lost"): (5, 22),    # lost early, straight from Discovery
    ("Proposal", "Closed Lost"): (7, 28),     # lost from Proposal (no Negotiation)
    ("Proposal", "Closed Won"): (7, 28),      # won from Proposal (no Negotiation)
}

# Demand-Intelligence guaranteed-cohort floor. matrix_color and escalation_flags
# are otherwise pure byproducts of the random (domain x task_type) draws, so DI
# heatmap cells aren't guaranteed populated. This cohort is emitted BEFORE the
# random fill: each entry forces `count` specs into its domain's worst-available
# matrix cell (RED where the domain has one — derived from the matrix, never
# hardcoded — else its most severe color) with the named escalation flag on, and
# a status weighted toward approved/rejected so they carry opportunities+amounts
# (approved) or read as declined demand (rejected), not just drafts.
# (domain, segment, flag, count). Segment is read from the assigned ACCOUNT.
# All five entries land on a genuine RED matrix cell (matrix_color always agrees
# with capability_matrix.json) — new_modality_av is placed on Financial Services,
# whose RED cell is Conversational AI (voice/video assistant), a believable fit.
DI_COHORT: list[tuple[str, str, str, int]] = [
    ("Healthcare", "Enterprise", "pii_regulated", 13),                # dollar plurality (largest amounts via Enterprise)
    ("Government", "Enterprise", "nonstandard_platform", 5),          # 5 + 4 = ~9 nonstandard-platform
    ("Government", "Mid-Market", "nonstandard_platform", 4),
    ("Legal", "Enterprise", "pii_regulated", 6),
    ("Financial Services", "Enterprise", "new_modality_av", 4),       # RED cell (Conversational AI) + flag
]

# Status mix for cohort specs — skewed to approved/rejected (real won/declined
# demand) vs. the organic [approved, in_review, draft, rejected] weighting.
_DI_STATUS_WEIGHTS = [0.55, 0.30, 0.10, 0.05]  # approved, rejected, in_review, draft


# --- small helpers -----------------------------------------------------------
def new_uuid() -> str:
    """Deterministic UUIDv4 drawn from the seeded RNG (reproducible across runs)."""
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def iso(ts: dt.datetime) -> str:
    """ISO-8601 string Postgres/PostgREST accepts for a timestamptz."""
    return ts.isoformat()


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def weighted_choice(options: list[str], weights: list[float]) -> str:
    return rng.choices(options, weights=weights, k=1)[0]


def cap_now(ts: dt.datetime) -> dt.datetime:
    """Never let a generated timestamp drift into the future."""
    return min(ts, NOW)


# --- matrix / escalation (from the JSON) ------------------------------------
def load_matrix() -> tuple[dict[tuple[str, str], str], list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """Read capability_matrix.json into:

    * lookup:    (domain, task_type) -> color
    * rows:      36 dim_capability_matrix rows
    * rules:     5 escalation_rules rows
    * notes:     color -> note
    """
    data = json.loads(MATRIX_JSON.read_text())
    task_order: list[str] = data["task_type_order"]
    color_notes: dict[str, str] = data["color_notes"]

    lookup: dict[tuple[str, str], str] = {}
    rows: list[dict[str, Any]] = []
    for domain, colors in data["matrix"].items():
        for task_type, color in zip(task_order, colors):
            lookup[(domain, task_type)] = color
            rows.append(
                {
                    "domain": domain,
                    "task_type": task_type,
                    "color": color,
                    "note": color_notes[color],
                }
            )

    rules = [
        {
            "rule_id": r["rule_id"],
            "label": r["label"],
            "detection": r["detection"],
            "note": r["note"],
        }
        for r in data["escalation_rules"]
    ]
    return lookup, rows, rules, color_notes


# --- accounts ----------------------------------------------------------------
def build_accounts() -> list[dict[str, Any]]:
    """One row per fictional customer, spread across domains/segments/regions."""
    accounts: list[dict[str, Any]] = []
    for domain, names in ACCOUNT_NAMES.items():
        for name in names:
            # Enterprise 40% / Mid-Market 35% / SMB 25% so SMB carries enough
            # accounts to produce a real (non-starved) opportunity pipeline.
            segment = weighted_choice(SEGMENTS, [0.40, 0.35, 0.25])
            tier = {
                "Enterprise": "Strategic",
                "Mid-Market": "Growth",
                "SMB": "Standard",
            }[segment]
            relationship = weighted_choice(
                ["customer", "net_new", "reactivation"], [0.55, 0.35, 0.10]
            )
            # Accounts predate the 6-month spec window (existing book of business).
            created = cap_now(
                NOW - dt.timedelta(days=rng.randint(60, 540), hours=rng.randint(0, 23))
            )
            accounts.append(
                {
                    "account_id": new_uuid(),
                    "account_name": name,
                    "domain": domain,
                    "segment": segment,
                    "tier": tier,
                    "region": weighted_choice(REGIONS, [0.46, 0.30, 0.16, 0.08]),
                    "owner": rng.choice(OWNERS),
                    "relationship_status": relationship,
                    "created_at": iso(created),
                }
            )
    return accounts


# --- spec documents (RAG corpus) --------------------------------------------
SPEC_DOC_COMBOS: list[tuple[str, str]] = [
    ("Technology", "Data Labeling"),
    ("Technology", "Model Eval"),
    ("Technology", "Code Review"),
    ("Financial Services", "Data Labeling"),
    ("Financial Services", "Doc Process"),
    ("Healthcare", "Data Labeling"),
    ("Healthcare", "Doc Process"),
    ("Legal", "Doc Process"),
    ("Legal", "Content Gen"),
    ("Retail", "Content Gen"),
    ("Retail", "Conversational AI"),
    ("Financial Services", "Code Review"),
]


def spec_document_body(domain: str, task_type: str, account_name: str) -> str:
    """A realistic ~1-page markdown spec used as retrieval context."""
    diff = DIFFICULTY[domain]
    ec = round(rng.randint(5, 12) * diff)
    return f"""# Project Spec — {account_name} ({domain} · {task_type})

## Overview
{account_name} engaged Lorefi to deliver a {task_type.lower()} program. This spec
captures scope, acceptance criteria, and resourcing agreed during discovery and
ratified at the go/no-go review. It is the reference template for similar
{domain} engagements.

## Data
- Source: customer-provided export, delivered in batches via secure transfer.
- Language: English (in scope); other languages explicitly out of scope.
- Sensitivity: customer pre-processes to remove regulated fields before transfer.
- Volume: pilot batch followed by a steady weekly cadence on acceptance.

## Method & Taxonomy
- A flat, documented label/criteria set refined jointly during a calibration round.
- A held-out gold set with adjudication for measuring agreement and drift.
- Ambiguous items are flagged for review, never guessed.

## Acceptance Criteria
- Inter-annotator agreement at or above the agreed kappa threshold on the gold set.
- Per-class / per-criterion quality reported each delivery.
- Calibration round signed off before scaling to full volume.

## Resourcing
- Expert contributors: ~{ec}
- Technical delivery manager: 1–2
- Data ops: 1–2
- Forward-deployed engineer: as needed for ingest/export integration.

## Risks & Notes
- Scope creep beyond the documented taxonomy is the primary risk; changes go
  through a written change order.
- Timeline assumes prompt customer turnaround on calibration feedback.
"""


def build_spec_documents(accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for domain, task_type in SPEC_DOC_COMBOS:
        sample = rng.choice([a for a in accounts if a["domain"] == domain])
        created = cap_now(NOW - dt.timedelta(days=rng.randint(40, 360)))
        docs.append(
            {
                "doc_id": new_uuid(),
                "domain": domain,
                "task_type": task_type,
                "title": f"{domain} · {task_type} — reference spec",
                "body": spec_document_body(domain, task_type, sample["account_name"]),
                "created_at": iso(created),
            }
        )
    return docs


# --- escalation flag assignment ---------------------------------------------
def pick_escalation_flags(domain: str, region: str) -> list[str]:
    """0–2 plausible escalation rule_ids for a transcript."""
    flags: list[str] = []
    # PII / regulated: much likelier in regulated domains.
    pii_p = {
        "Healthcare": 0.45,
        "Financial Services": 0.35,
        "Government": 0.40,
        "Legal": 0.30,
    }.get(domain, 0.08)
    if rng.random() < pii_p:
        flags.append("pii_regulated")
    # Non-English: likelier outside NA.
    if region != "NA" and rng.random() < 0.18:
        flags.append("non_english")
    # The LLM-detected, rarer flags.
    if rng.random() < 0.07:
        flags.append("nonstandard_platform")
    if rng.random() < 0.06:
        flags.append("extreme_complexity")
    if rng.random() < 0.04:
        flags.append("new_modality_av")
    return flags


# --- resourcing --------------------------------------------------------------
def resource_counts(domain: str, color: str) -> dict[str, int]:
    """Headcount scaled by domain difficulty and matrix color."""
    diff = DIFFICULTY[domain]
    color_mult = {"green": 1.0, "yellow": 1.3, "red": 1.7}[color]
    ec = int(clamp(round(rng.randint(4, 11) * diff * color_mult), 2, 30))
    tdm = int(clamp(round(rng.randint(1, 2) * (1 + (diff - 1) * 0.6)), 1, 4))
    dops = int(clamp(round(rng.randint(1, 2) * color_mult), 1, 4))
    fde = int(clamp(round((0 if color == "green" else 1) + rng.randint(0, 1) * diff), 0, 3))
    return {"ec": ec, "tdm": tdm, "dops": dops, "fde": fde}


def resource_flags(domain: str, color: str, escalation_flags: list[str]) -> dict[str, bool]:
    return {
        "surge_capacity": color == "red" or DIFFICULTY[domain] >= 1.5,
        "sme_review": color in ("yellow", "red"),
        "language_qualified": "non_english" in escalation_flags,
        "dedicated_pod": DIFFICULTY[domain] >= 1.6 or color == "red",
    }


# --- created_at by status ----------------------------------------------------
def created_at_for_status(status: str) -> dt.datetime:
    """Spread over the last 6 months, skewed by lifecycle stage.

    Drafts/reviews cluster recently; approved/rejected reach further back. The
    triangular mode sits near 'recent' so volume grows toward the present.
    """
    if status == "draft":
        offset = rng.triangular(0, 45, 4)
    elif status == "in_review":
        offset = rng.triangular(2, 80, 18)
    elif status == "approved":
        offset = rng.triangular(18, SIX_MONTHS_DAYS, 65)
    else:  # rejected
        offset = rng.triangular(10, 170, 55)
    return cap_now(
        NOW - dt.timedelta(days=offset, hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
    )


# --- Demand-Intelligence guaranteed cohort -----------------------------------
def _reddest_task_type(domain: str, matrix: dict[tuple[str, str], str]) -> str:
    """Task_type whose matrix cell is the most severe color for this domain
    (red > yellow > green), derived from the matrix — never a hardcoded color.
    Returns a RED cell where the domain has one; otherwise its worst color."""
    severity = {"red": 3, "yellow": 2, "green": 1}
    return max(
        (tt for (d, tt) in matrix if d == domain),
        key=lambda tt: (severity[matrix[(domain, tt)]], tt),  # tie-break: task_type name
    )


def build_di_cohort(
    accounts: list[dict[str, Any]],
    matrix: dict[tuple[str, str], str],
) -> list[dict[str, Any]]:
    """Deterministic floor of RED/escalated specs for the DI heatmap (see
    DI_COHORT). Emitted before the random fill. Same row shape as organic specs.

    Heatmap segment is read from the ASSIGNED ACCOUNT (fct_spec has no segment;
    it lives on dim_account and is denormalized onto fct_opportunity), so we
    prefer an account matching (domain, segment); if none exists we fall back to
    any account in the domain (the cell's segment then follows that account)."""
    specs: list[dict[str, Any]] = []
    j = 0
    for domain, segment, flag, count in DI_COHORT:
        task_type = _reddest_task_type(domain, matrix)
        color = matrix[(domain, task_type)]
        matched = [a for a in accounts if a["domain"] == domain and a["segment"] == segment]
        pool = matched if matched else [a for a in accounts if a["domain"] == domain]
        for k in range(count):
            account = pool[k % len(pool)]  # cycle the matching accounts
            status = weighted_choice(
                ["approved", "rejected", "in_review", "draft"], _DI_STATUS_WEIGHTS
            )
            created = created_at_for_status(status)
            counts = resource_counts(domain, color)
            base_conf = {"green": 0.88, "yellow": 0.74, "red": 0.58}[color]
            confidence = round(
                clamp(base_conf + rng.uniform(-0.08, 0.08) - 0.06, 0.30, 0.98), 3
            )  # -0.06 == one forced escalation flag (mirrors the organic formula)
            approved_at = None
            if status == "approved":
                approved_at = iso(cap_now(created + dt.timedelta(days=rng.randint(3, 21))))
            specs.append(
                {
                    "spec_id": new_uuid(),
                    "transcript_id": f"txn_di_{j:04d}",
                    "account_id": account["account_id"],
                    "domain": domain,
                    "task_type": task_type,
                    "matrix_color": color,
                    "escalation_flags": [flag],          # the named flag, forced on
                    "confidence": confidence,
                    "ec_count": counts["ec"],
                    "tdm_count": counts["tdm"],
                    "dops_count": counts["dops"],
                    "fde_count": counts["fde"],
                    "resource_flags": resource_flags(domain, color, [flag]),
                    "status": status,
                    "rejection_reason": (
                        rng.choice(REJECTION_REASONS) if status == "rejected" else None
                    ),
                    "opportunity_id": None,
                    "estimated_value": estimate_value(account["segment"], counts["fde"]),
                    "created_at": iso(created),
                    "approved_at": approved_at,
                    "_account": account,
                }
            )
            j += 1
    return specs


# --- fct_spec ----------------------------------------------------------------
def build_specs(
    accounts: list[dict[str, Any]],
    matrix: dict[tuple[str, str], str],
    n: int = 500,
) -> list[dict[str, Any]]:
    """~500 assessed/draft specs. matrix_color always agrees with the matrix.

    A deterministic DI cohort (build_di_cohort) is emitted FIRST to guarantee the
    Demand-Intelligence heatmap cells are populated; the remaining n - cohort
    specs fill in organically exactly as before.
    """
    task_types = sorted({tt for (_d, tt) in matrix})
    # Enterprise still attracts the most discovery, but the skew is gentle
    # (1.6 / 1.3 / 1.0) so SMB keeps a real share of specs (~20%) rather than
    # being crowded out — that's what gives SMB an open pipeline after top-up.
    acct_weights = [
        {"Enterprise": 1.6, "Mid-Market": 1.3, "SMB": 1.0}[a["segment"]]
        for a in accounts
    ]

    # Deterministic DI cohort first, then organic fill for the remainder.
    specs: list[dict[str, Any]] = build_di_cohort(accounts, matrix)
    organic_n = max(0, n - len(specs))
    for i in range(organic_n):
        account = rng.choices(accounts, weights=acct_weights, k=1)[0]
        domain = account["domain"]
        task_type = rng.choice(task_types)
        color = matrix[(domain, task_type)]

        status = weighted_choice(
            ["approved", "in_review", "draft", "rejected"],
            [0.56, 0.20, 0.14, 0.10],
        )
        created = created_at_for_status(status)
        flags = pick_escalation_flags(domain, account["region"])

        base_conf = {"green": 0.88, "yellow": 0.74, "red": 0.58}[color]
        confidence = round(
            clamp(base_conf + rng.uniform(-0.08, 0.08) - 0.06 * len(flags), 0.30, 0.98),
            3,
        )

        counts = resource_counts(domain, color)
        approved_at = None
        if status == "approved":
            approved_at = iso(cap_now(created + dt.timedelta(days=rng.randint(3, 21))))

        specs.append(
            {
                "spec_id": new_uuid(),
                "transcript_id": f"txn_{i:05d}",
                "account_id": account["account_id"],
                "domain": domain,
                "task_type": task_type,
                "matrix_color": color,
                "escalation_flags": flags,
                "confidence": confidence,
                "ec_count": counts["ec"],
                "tdm_count": counts["tdm"],
                "dops_count": counts["dops"],
                "fde_count": counts["fde"],
                "resource_flags": resource_flags(domain, color, flags),
                "status": status,
                "rejection_reason": (
                    rng.choice(REJECTION_REASONS) if status == "rejected" else None
                ),
                "opportunity_id": None,  # back-filled for approved specs below
                "estimated_value": estimate_value(account["segment"], counts["fde"]),
                "created_at": iso(created),
                "approved_at": approved_at,
                # carried for downstream generation, dropped before insert:
                "_account": account,
            }
        )
    return specs


# --- fct_opportunity ---------------------------------------------------------
def win_rate(segment: str, region: str) -> float:
    return clamp(WIN_BASE[segment] + WIN_REGION_MOD[region], 0.10, 0.85)


def _close_opportunity(opp: dict[str, Any]) -> None:
    """Resolve an OPEN opportunity to Closed Won/Lost in place.

    Win/loss is drawn from ``win_rate(segment, region)`` so segment ordering
    (Enterprise > Mid-Market > SMB) and region variation are preserved no matter
    whether the close happened naturally or via the top-up pass below. closed_at
    is derived from the opp's own created_at, capped at NOW.
    """
    is_won = rng.random() < win_rate(opp["segment"], opp["region"])
    opp["is_won"] = is_won
    opp["stage"] = "Closed Won" if is_won else "Closed Lost"
    if is_won:
        weights = WIN_TYPE_WEIGHTS[opp["segment"]]
        opp["win_type"] = rng.choices(list(weights), weights=list(weights.values()), k=1)[0]
    # closed_at is aligned to the terminal stage-history entry in build_stage_history.


def build_opportunities(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One opportunity per approved spec; narrowing funnel + varied win rates.

    Mutates each approved spec's ``opportunity_id`` so fct_spec and
    fct_opportunity agree. ~55% of opportunities close naturally (resolved
    Won/Lost by win_rate). At ~500 specs the volume is enough that every segment
    carries both open and closed deals on its own — no flooring hack needed.
    """
    opportunities: list[dict[str, Any]] = []

    for spec in specs:
        if spec["status"] != "approved":
            continue
        account = spec["_account"]
        segment, region = account["segment"], account["region"]

        lo, hi = AMOUNT_RANGE[segment]
        amount = round(rng.uniform(lo, hi) * (1 + 0.05 * spec["fde_count"]), -3)

        approved_dt = dt.datetime.fromisoformat(spec["approved_at"])
        created = cap_now(approved_dt + dt.timedelta(days=rng.randint(1, 14)))

        opportunity_id = new_uuid()
        spec["opportunity_id"] = opportunity_id  # keep the spine consistent

        # Build the opp OPEN first (Discovery > Proposal > Negotiation funnel),
        # then maybe close it. ~55% close naturally.
        opp = {
            "opportunity_id": opportunity_id,
            "spec_id": spec["spec_id"],
            "account_id": account["account_id"],
            "name": f"{account['account_name']} – {spec['task_type']} Program",
            "stage": weighted_choice(
                ["Discovery", "Proposal", "Negotiation"], [0.50, 0.32, 0.18]
            ),
            "amount": amount,
            "segment": segment,
            "region": region,
            "owner": account["owner"],
            "created_at": iso(created),
            "closed_at": None,
            "is_won": False,
            "win_type": None,   # set only when Closed Won (see _close_opportunity)
            "acv": None,        # computed just below
        }

        if rng.random() < 0.55:
            _close_opportunity(opp)

        # ACV (revenue): base range by segment, scaled up for won deals by win type
        # so new_logo > prior_loss_now_won > renewal > reactivation on average.
        lo_acv, hi_acv = ACV_RANGE[segment]
        mult = WIN_TYPE_ACV_MULT.get(opp["win_type"], 1.0)
        opp["acv"] = round(rng.uniform(lo_acv, hi_acv) * mult, -3)

        opportunities.append(opp)

    return opportunities


# --- fct_opportunity_stage_history -------------------------------------------
def _journey_path(opp: dict[str, Any]) -> list[str]:
    """Ordered list of stages this opp passed through: always starts at Discovery,
    always ends at the opp's existing final stage (opp["stage"]). Introduces
    realistic variation off the seeded rng:
      * open-at-Negotiation deals may skip Proposal (Discovery->Negotiation);
      * Closed Lost deals may exit early (Discovery->Closed Lost, or
        Discovery->Proposal->Closed Lost) instead of reaching Negotiation;
      * Closed Won deals may close from Proposal (Discovery->Proposal->Closed Won);
      * otherwise the full linear path (still the dominant trunk).
    Reads opp["stage"] only — never mutates the opp.
    """
    final = opp["stage"]

    # Open deals: Discovery up to the current open stage; only an open-at-
    # Negotiation deal can have skipped Proposal on the way.
    if final in OPEN_STAGES:
        if final == "Discovery":
            return ["Discovery"]
        if final == "Proposal":
            return ["Discovery", "Proposal"]
        # final == "Negotiation"
        if rng.random() < P_SKIP_PROPOSAL:
            return ["Discovery", "Negotiation"]
        return ["Discovery", "Proposal", "Negotiation"]

    # Closed Lost: may exit early, else reach Negotiation (optionally skipping Proposal).
    if final == "Closed Lost":
        r = rng.random()
        if r < P_LOST_AT_DISCOVERY:
            return ["Discovery", "Closed Lost"]
        if r < P_LOST_AT_DISCOVERY + P_LOST_AT_PROPOSAL:
            return ["Discovery", "Proposal", "Closed Lost"]
        if rng.random() < P_SKIP_PROPOSAL:
            return ["Discovery", "Negotiation", "Closed Lost"]
        return ["Discovery", "Proposal", "Negotiation", "Closed Lost"]

    # Closed Won: may close from Proposal, else reach Negotiation (optionally skipping Proposal).
    if rng.random() < P_WON_FROM_PROPOSAL:
        return ["Discovery", "Proposal", "Closed Won"]
    if rng.random() < P_SKIP_PROPOSAL:
        return ["Discovery", "Negotiation", "Closed Won"]
    return ["Discovery", "Proposal", "Negotiation", "Closed Won"]


def build_stage_history(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per (opportunity, stage) — models Salesforce Opportunity History.

    Journey variation (deterministic, seed=4207): most deals walk the full linear
    path Discovery -> Proposal -> Negotiation -> (terminal), but a minority skip
    Proposal, exit Closed Lost early (from Discovery or Proposal), or close Won
    from Proposal — see _journey_path + the P_* probabilities. ONLY the
    intermediate path varies; opp["stage"], is_won, win_type, amount and
    created_at are never touched, so every headline count is preserved.

    The final stage's row has exited_at=null (current open stage OR terminal); for
    a closed opp we align opp.closed_at to that terminal entry. Per-transition gaps
    come from _STAGE_GAP_MAP (scaled by segment) and rows chain contiguously
    (exited_at[N] == entered_at[N+1]) so transition self-joins stay clean.
    """
    rows: list[dict[str, Any]] = []
    for opp in opportunities:
        factor = _SEGMENT_VELOCITY_FACTOR.get(opp["segment"], 1.0)
        path = _journey_path(opp)
        closed = path[-1] not in OPEN_STAGES

        cur = dt.datetime.fromisoformat(opp["created_at"])  # entered Discovery
        for i, st in enumerate(path):
            if i == len(path) - 1:
                # current open stage OR terminal closed stage: still here (exited=null)
                rows.append(_history_row(opp, st, cur, None))
                if closed:
                    opp["closed_at"] = iso(cur)  # align closed_at to the terminal entry
            else:
                lo, hi = _STAGE_GAP_MAP.get((st, path[i + 1]), (7, 21))
                gap = max(1, round(rng.randint(lo, hi) * factor))
                nxt = cap_now(cur + dt.timedelta(days=gap))
                # entered_at must be STRICTLY increasing within an opp: when a path
                # runs up against NOW, cap_now() can clamp consecutive entries to the
                # same instant, which would create same-timestamp rows and corrupt the
                # transition self-join (phantom self-loops / backward edges). If the
                # cap didn't move us forward, nudge +1 minute. Strict increase wins
                # over the soft NOW cap here — a deal's stages can't share an instant,
                # and a few minutes past NOW on a near-current final entry is realistic.
                if nxt <= cur:
                    nxt = cur + dt.timedelta(minutes=1)
                rows.append(_history_row(opp, st, cur, nxt))
                cur = nxt
    return rows


def _history_row(
    opp: dict[str, Any], stage: str, entered: dt.datetime, exited: "dt.datetime | None"
) -> dict[str, Any]:
    return {
        "history_id": new_uuid(),
        "opportunity_id": opp["opportunity_id"],
        "stage": stage,
        "entered_at": iso(entered),
        "exited_at": iso(exited) if exited is not None else None,
    }


# --- spec_lifecycle (the spine) ---------------------------------------------
def build_lifecycle(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One spine row per spec, linking transcript/spec/opportunity/account."""
    return [
        {
            "lifecycle_id": new_uuid(),
            "transcript_id": spec["transcript_id"],
            "spec_id": spec["spec_id"],
            "opportunity_id": spec["opportunity_id"],
            "account_id": spec["account_id"],
            "project_id": None,
            "created_at": spec["created_at"],
        }
        for spec in specs
    ]


# --- named-sample fixtures (block-5 EDIT 4) ----------------------------------
# A hand-pinned returning-account fixture the demo leans on, built with FIXED
# UUIDs and literal values (NOT the main `rng`/`_est_rng` streams), so it is
# byte-stable across reseeds AND never perturbs the protected organic counts
# (500 specs / 274 opps / 74 won / the DI cohort):
#
#   EDIT 4  Prior-spec history (2 approved + 1 rejected) on the EXISTING account
#           behind sample_transcript_01 (Meridian Synth), so running that
#           transcript demonstrates returning-account + prior-project enrichment.
#
# NOTE: sample_transcript_04_ambiguous is intentionally NOT seeded here — it is
# assessed live (the point of that demo is to isolate the low-confidence dial),
# and a pre-seeded fixture would collide with the live run and surface a spurious
# "returning account" line.

# Meridian Synth (sample_transcript_01) prior history. Tuples:
# (spec_id, lifecycle_id, transcript_id, task_type, color, status, confidence,
#  rejection_reason, age_days, approved_age_days). The rejected row carries a
# real rejection_reason so the returning-account line shows "last rejected for: …".
_MERIDIAN_HISTORY: list[tuple] = [
    ("0a4b0001-0001-4001-8001-000000000001", "0a4b0001-0001-4001-8001-000000000101",
     "txn_meridian_hist_01", "Content Gen", "green", "approved", 0.91, None, 150, 138),
    ("0a4b0001-0001-4001-8001-000000000002", "0a4b0001-0001-4001-8001-000000000102",
     "txn_meridian_hist_02", "Model Eval", "green", "approved", 0.88, None, 96, 84),
    ("0a4b0001-0001-4001-8001-000000000003", "0a4b0001-0001-4001-8001-000000000103",
     "txn_meridian_hist_03", "Data Labeling", "green", "rejected", 0.79,
     "missing_acceptance_criteria", 60, None),
]


def build_returning_history(account: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """EDIT 4: prior fct_spec + spine rows on an EXISTING account so it reads as a
    returning account with project history (2 approved + 1 rejected)."""
    specs: list[dict[str, Any]] = []
    lifecycle: list[dict[str, Any]] = []
    for (spec_id, lc_id, txn, task_type, color, status, conf, reason, age, appr_age) in _MERIDIAN_HISTORY:
        created = cap_now(NOW - dt.timedelta(days=age))
        approved_at = (
            iso(cap_now(NOW - dt.timedelta(days=appr_age))) if status == "approved" else None
        )
        specs.append(
            {
                "spec_id": spec_id,
                "transcript_id": txn,
                "account_id": account["account_id"],
                "domain": account["domain"],
                "task_type": task_type,
                "matrix_color": color,
                "escalation_flags": [],
                "confidence": conf,
                "ec_count": 7,
                "tdm_count": 1,
                "dops_count": 1,
                "fde_count": 1,
                "resource_flags": resource_flags(account["domain"], color, []),
                "status": status,
                "rejection_reason": reason,
                "opportunity_id": None,
                "estimated_value": 95000.0,
                "created_at": iso(created),
                "approved_at": approved_at,
            }
        )
        lifecycle.append(
            {
                "lifecycle_id": lc_id,
                "transcript_id": txn,
                "spec_id": spec_id,
                "opportunity_id": None,
                "account_id": account["account_id"],
                "project_id": None,
                "created_at": iso(created),
            }
        )
    return {"specs": specs, "lifecycle": lifecycle}


# --- insertion ---------------------------------------------------------------
# Tables this seed OWNS, in FK-safe delete order (children first). We do NOT
# clear dim_capability_matrix / escalation_rules — those are upserted reference
# data. (account_id etc. are never null, so "<pk>=not.is.null" matches all rows.)
_OWNED_TABLES: list[tuple[str, str]] = [
    ("fct_opportunity_stage_history", "history_id"),  # child of fct_opportunity
    ("spec_lifecycle", "lifecycle_id"),
    ("fct_opportunity", "opportunity_id"),
    ("spec_status_history", "history_id"),  # child of fct_spec (audit log)
    ("fct_spec", "spec_id"),
    ("stg_transcript_extracts", "extract_id"),
    ("spec_documents", "doc_id"),
    ("dim_account", "account_id"),
]


def clear_existing() -> None:
    """Make reruns idempotent by emptying the owned tables first.

    PostgREST exposes no TRUNCATE/RPC here (and we can't add one without
    touching the schema/client), so we issue an unfiltered-equivalent DELETE per
    table in FK-safe order, reusing the client's config + headers. These tables
    use uuid defaults (no serial identity), so DELETE is equivalent to
    TRUNCATE ... RESTART IDENTITY for our purposes.
    """
    dbclient._require_config()
    with httpx.Client(timeout=dbclient._TIMEOUT) as http:
        for table, pk in _OWNED_TABLES:
            response = http.delete(
                f"{dbclient.REST_ROOT}/{table}",
                headers=dbclient._headers(),
                params={pk: "not.is.null"},  # matches every row
            )
            dbclient._raise_for_status(response)


def insert_in_batches(table: str, rows: list[dict[str, Any]], size: int = 100) -> None:
    for start in range(0, len(rows), size):
        insert(table, rows[start : start + size])


def strip_private(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop helper keys (prefixed '_') that aren't real columns."""
    return [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows]


def main() -> None:
    print("Loading capability matrix from", MATRIX_JSON)
    matrix, matrix_rows, escalation_rows, _notes = load_matrix()

    print("Building rows in memory (deterministic, seed =", SEED, ")...")
    accounts = build_accounts()
    spec_documents = build_spec_documents(accounts)
    specs = build_specs(accounts, matrix)
    opportunities = build_opportunities(specs)
    lifecycle = build_lifecycle(specs)
    # Build stage history AFTER opportunities (it aligns each closed opp's
    # closed_at to its terminal stage entry, mutating the opp before insert).
    stage_history = build_stage_history(opportunities)

    # Named-sample fixture (block-5 EDIT 4). Built AFTER the organic dataset with
    # FIXED UUIDs / literal values, so it never perturbs the counts above.
    meridian = next(a for a in accounts if a["account_name"] == "Meridian Synth")
    returning = build_returning_history(meridian)

    approved = sum(1 for s in specs if s["status"] == "approved")
    closed_won = sum(1 for o in opportunities if o["stage"] == "Closed Won")
    print(
        f"  accounts={len(accounts)} matrix={len(matrix_rows)} "
        f"rules={len(escalation_rows)} docs={len(spec_documents)}"
    )
    print(
        f"  specs={len(specs)} (approved={approved}) "
        f"opportunities={len(opportunities)} (closed_won={closed_won}) "
        f"lifecycle={len(lifecycle)} stage_history={len(stage_history)}"
    )

    # Idempotency: clear owned tables so a rerun yields a single clean copy.
    clear_existing()
    print("Cleared existing rows (DELETE, FK-safe order) — rerun is idempotent.")

    # FK-safe insertion order.
    print("Inserting dim_account ...")
    insert_in_batches("dim_account", accounts)

    print("Upserting dim_capability_matrix ...")
    upsert("dim_capability_matrix", matrix_rows, on_conflict="domain,task_type")

    print("Inserting escalation_rules ...")
    upsert("escalation_rules", escalation_rows, on_conflict="rule_id")

    print("Inserting spec_documents ...")
    insert_in_batches("spec_documents", spec_documents)

    print("Inserting fct_spec ...")
    insert_in_batches("fct_spec", strip_private(specs))
    # Named-sample fixture (inserted separately: its column set differs from the
    # organic rows, and PostgREST bulk insert wants homogeneous rows per request).
    print("Inserting fct_spec named-sample fixture (EDIT 4) ...")
    insert("fct_spec", returning["specs"])      # EDIT 4: Meridian Synth prior history

    print("Inserting fct_opportunity ...")
    insert_in_batches("fct_opportunity", opportunities)

    print("Inserting fct_opportunity_stage_history ...")
    insert_in_batches("fct_opportunity_stage_history", stage_history)

    print("Inserting spec_lifecycle ...")
    insert_in_batches("spec_lifecycle", lifecycle)
    # Spine rows for the named-sample fixture (EDIT 4).
    insert("spec_lifecycle", returning["lifecycle"])

    print("Done. stg_transcript_extracts is left empty (populated at runtime).")


if __name__ == "__main__":
    main()
