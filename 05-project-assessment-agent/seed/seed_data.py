"""Seed the Project Assessment Agent demo with fictional Lorefi data.

Generates a self-consistent dataset and INSERTS it into Supabase via the
PostgREST client in ``backend/db/client.py``. It does **not** run on import —
run it yourself once the schema is applied and ``.env`` is filled:

    python seed/seed_data.py

What it creates (all fictional — Lorefi + invented customers):
    * ~41 customer accounts across 6 domains
    * the 36-cell capability matrix + 5 escalation rules (from the JSON)
    * 12 full ~1-page RAG spec documents
    * ~160 fct_spec rows over the last 6 months (realistic status mix)
    * ~90 fct_opportunity rows from approved specs (funnel + varied win rates)
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
    "Healthcare": [
        "Cedarbrook Health", "Vantage Medical", "Lumicare Diagnostics",
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

# Opportunity stage path + per-transition base gap (days) for stage velocity.
OPEN_STAGES = ["Discovery", "Proposal", "Negotiation"]
# index 0: Discovery->Proposal, 1: Proposal->Negotiation, 2: Negotiation->Closed
_STAGE_GAP_BOUNDS = [(5, 18), (7, 21), (7, 30)]
_SEGMENT_VELOCITY_FACTOR = {"Enterprise": 1.4, "Mid-Market": 1.0, "SMB": 0.8}


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


# --- fct_spec ----------------------------------------------------------------
def build_specs(
    accounts: list[dict[str, Any]],
    matrix: dict[tuple[str, str], str],
    n: int = 240,
) -> list[dict[str, Any]]:
    """~240 assessed/draft specs. matrix_color always agrees with the matrix."""
    task_types = sorted({tt for (_d, tt) in matrix})
    # Enterprise still attracts the most discovery, but the skew is gentle
    # (1.6 / 1.3 / 1.0) so SMB keeps a real share of specs (~20%) rather than
    # being crowded out — that's what gives SMB an open pipeline after top-up.
    acct_weights = [
        {"Enterprise": 1.6, "Mid-Market": 1.3, "SMB": 1.0}[a["segment"]]
        for a in accounts
    ]

    specs: list[dict[str, Any]] = []
    for i in range(n):
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
    fct_opportunity agree. ~45% of opportunities close naturally (resolved
    Won/Lost by win_rate). At ~240 specs the volume is enough that every segment
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
        # then maybe close it. ~45% close naturally.
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

        if rng.random() < 0.45:
            _close_opportunity(opp)

        # ACV (revenue): base range by segment, scaled up for won deals by win type
        # so new_logo > prior_loss_now_won > renewal > reactivation on average.
        lo_acv, hi_acv = ACV_RANGE[segment]
        mult = WIN_TYPE_ACV_MULT.get(opp["win_type"], 1.0)
        opp["acv"] = round(rng.uniform(lo_acv, hi_acv) * mult, -3)

        opportunities.append(opp)

    return opportunities


# --- fct_opportunity_stage_history -------------------------------------------
def build_stage_history(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per (opportunity, stage) — models Salesforce Opportunity History.

    Each opp's path is Discovery -> Proposal -> Negotiation -> (terminal). For an
    OPEN opp the current stage's exited_at is null; for a CLOSED opp the terminal
    Closed Won/Lost row's exited_at is null and we align opp.closed_at to it. The
    stage in fct_opportunity always equals the latest open (exited_at=null) stage
    here. Per-transition gaps (scaled by segment) make stage velocity computable.
    """
    rows: list[dict[str, Any]] = []
    for opp in opportunities:
        factor = _SEGMENT_VELOCITY_FACTOR.get(opp["segment"], 1.0)
        stage = opp["stage"]
        if stage in OPEN_STAGES:
            path = OPEN_STAGES[: OPEN_STAGES.index(stage) + 1]
            closed = False
        else:
            path = OPEN_STAGES + [stage]  # full path through to the terminal stage
            closed = True

        cur = dt.datetime.fromisoformat(opp["created_at"])  # entered Discovery
        for i, st in enumerate(path):
            if i == len(path) - 1:
                # current open stage OR terminal closed stage: still here (exited=null)
                rows.append(_history_row(opp, st, cur, None))
                if closed:
                    opp["closed_at"] = iso(cur)  # align closed_at to the terminal entry
            else:
                lo, hi = _STAGE_GAP_BOUNDS[i]
                gap = max(1, round(rng.randint(lo, hi) * factor))
                nxt = cap_now(cur + dt.timedelta(days=gap))
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

    print("Inserting fct_opportunity ...")
    insert_in_batches("fct_opportunity", opportunities)

    print("Inserting fct_opportunity_stage_history ...")
    insert_in_batches("fct_opportunity_stage_history", stage_history)

    print("Inserting spec_lifecycle ...")
    insert_in_batches("spec_lifecycle", lifecycle)

    print("Done. stg_transcript_extracts is left empty (populated at runtime).")


if __name__ == "__main__":
    main()
