"""Dashboard data route (Block 5C rebuild).

GET /dashboard-data computes three sections from WAREHOUSE MODELS ONLY
(fct_spec, fct_opportunity, fct_opportunity_stage_history, spec_lifecycle,
dim_account). Never from Slack-derived data — the warehouse is the single source
of truth.

Global query filters (apply across the response where they make sense):
  date_from, date_to (ISO YYYY-MM-DD), cadence (daily|weekly|monthly),
  use_case ("Domain · Task Type"), segment, region.

Soft-deleted specs (status='deleted') are excluded everywhere. Opp-stage figures
are kept fresh in PRODUCTION by Fivetran inbound batch (Salesforce -> warehouse);
the ``data_freshness`` field documents the production caveat.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Query

from api import to_error_response
from db.client import select

router = APIRouter(tags=["dashboard"])

STAGE_ORDER = ["Discovery", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
OPEN_STAGES = ["Discovery", "Proposal", "Negotiation"]
WIN_TYPES = ["new_logo", "prior_loss_now_won", "renewal", "reactivation"]

# win_type values render as these labels in the UI:
WIN_TYPE_LABELS = {
    "new_logo": "New Logo",
    "prior_loss_now_won": "Prior Loss · Now Won",
    "renewal": "Renewal",
    "reactivation": "Reactivation",
}

_FRESHNESS_NOTE = (
    "Opportunity-stage data is as of the last inbound sync (Fivetran), up to a "
    "few hours old in production. Spec-generation data is live from the "
    "warehouse. This demo reads live; the note documents the production "
    "eventual-consistency caveat."
)


def _use_case(domain: Optional[str], task_type: Optional[str]) -> Optional[str]:
    if not domain or not task_type:
        return None
    return f"{domain} · {task_type}"


# --- endpoint ----------------------------------------------------------------
@router.get("/dashboard-data")
def dashboard_data(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    cadence: str = Query("monthly"),
    use_case: Optional[str] = Query(None),
    segment: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
):
    try:
        return _build(date_from, date_to, cadence, use_case, segment, region)
    except Exception as exc:  # clean JSON error, never a stack trace
        return to_error_response(exc)


# --- filter helpers ----------------------------------------------------------
def _parse_multi(raw: Optional[str]) -> List[str]:
    """Parse a comma-joined multi-select param into a list of values. Empty/None
    -> [] (meaning "no filter on this dimension" — all pass). Use-case values
    contain no commas (they use ' · '), so the split is unambiguous."""
    if not raw:
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


# --- date helpers ------------------------------------------------------------
def _parse_date(s: Optional[str]) -> Optional[date]:
    if s is None or str(s).strip() == "":
        return None
    try:
        return date.fromisoformat(str(s).strip()[:10])
    except ValueError:
        raise ValueError(f"invalid date '{s}'; expected YYYY-MM-DD")


def _row_date(s: Any) -> Optional[date]:
    """The date portion of a stored ISO timestamp (tz-agnostic)."""
    try:
        return date.fromisoformat(str(s)[:10])
    except (ValueError, TypeError):
        return None


def _period_key(d: date, cadence: str) -> str:
    if cadence == "monthly":
        return f"{d.year:04d}-{d.month:02d}"
    if cadence == "weekly":
        return (d - timedelta(days=d.weekday())).isoformat()  # Monday of the week
    return d.isoformat()


def _enumerate_periods(start: date, end: date, cadence: str) -> List[str]:
    """Continuous list of period keys from start..end (so line x-axes have no gaps)."""
    if start > end:
        start = end
    out: List[str] = []
    if cadence == "monthly":
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            out.append(f"{y:04d}-{m:02d}")
            m += 1
            if m > 12:
                m, y = 1, y + 1
    elif cadence == "weekly":
        cur = start - timedelta(days=start.weekday())
        while cur <= end:
            out.append(cur.isoformat())
            cur += timedelta(days=7)
    else:  # daily
        cur = start
        while cur <= end:
            out.append(cur.isoformat())
            cur += timedelta(days=1)
    return out


# --- main builder ------------------------------------------------------------
def _build(
    date_from: Optional[str],
    date_to: Optional[str],
    cadence: str,
    use_case: Optional[str],
    segment: Optional[str],
    region: Optional[str],
) -> Dict[str, Any]:
    if cadence not in ("daily", "weekly", "monthly"):
        cadence = "monthly"

    # Multi-select filters: comma-joined params -> lists. Empty list = all pass.
    use_cases = _parse_multi(use_case)
    segments = _parse_multi(segment)
    regions = _parse_multi(region)

    today = datetime.now(timezone.utc).date()
    df, dt_to = _parse_date(date_from), _parse_date(date_to)
    if df is None and dt_to is None:
        start, end = date(today.year, 1, 1), today      # default: YTD
    else:
        start = df                                       # None -> earliest data
        end = dt_to if dt_to is not None else today      # blank -> today

    # --- pull warehouse models (deleted specs excluded) ----------------------
    # DI needs matrix_color / escalation_flags / estimated_value, plus account_id
    # to join a segment (and region) onto EVERY spec — including rejected / non-opp
    # ones, which the opportunity table can't segment (opps exist for approved only).
    specs = select(
        "fct_spec",
        {"status": "neq.deleted"},
        columns="spec_id,status,rejection_reason,domain,task_type,created_at,"
        "account_id,matrix_color,escalation_flags,estimated_value",
    )
    opps = select(
        "fct_opportunity",
        columns="opportunity_id,spec_id,stage,amount,acv,win_type,segment,region,is_won,created_at,closed_at",
    )
    hist = select(
        "fct_opportunity_stage_history",
        columns="opportunity_id,stage,entered_at,exited_at",
    )

    # dim_account join: account_id -> segment / region, attached onto each spec so
    # ALL declined demand (not just approved) can be sliced by segment/region.
    dim_accounts = select("dim_account", columns="account_id,segment,region")
    acct_segment = {a["account_id"]: a.get("segment") for a in dim_accounts}
    acct_region = {a["account_id"]: a.get("region") for a in dim_accounts}
    for s in specs:
        s["segment"] = acct_segment.get(s.get("account_id"))
        s["region"] = acct_region.get(s.get("account_id"))

    spec_meta = {s["spec_id"]: (s.get("domain"), s.get("task_type")) for s in specs}

    # Available filter options (for the UI dropdowns) — computed pre-filter.
    available_use_cases = sorted(
        {uc for s in specs if (uc := _use_case(s.get("domain"), s.get("task_type")))}
    )
    available_segments = sorted({o["segment"] for o in opps if o.get("segment")})
    available_regions = sorted({o["region"] for o in opps if o.get("region")})

    def in_range(created: Any) -> bool:
        d = _row_date(created)
        if d is None:
            return False
        if start is not None and d < start:
            return False
        return d <= end

    # filtered specs: date + use_case membership (segment/region don't apply to specs)
    f_specs = [
        s for s in specs
        if in_range(s.get("created_at"))
        and (not use_cases or _use_case(s.get("domain"), s.get("task_type")) in use_cases)
    ]

    # filtered opps: date + use_case (via the opp's spec) + segment + region membership
    def opp_uc(o: Dict[str, Any]) -> Optional[str]:
        dm, tt = spec_meta.get(o.get("spec_id"), (None, None))
        return _use_case(dm, tt)

    f_opps = [
        o for o in opps
        if in_range(o.get("created_at"))
        and (not use_cases or opp_uc(o) in use_cases)
        and (not segments or o.get("segment") in segments)
        and (not regions or o.get("region") in regions)
    ]
    opp_ids = {o["opportunity_id"] for o in f_opps}
    f_hist = [h for h in hist if h.get("opportunity_id") in opp_ids]

    # DI spec list: date + use_case + segment + region (specs now carry segment
    # and region via the dim_account join, so the segment/region multi-select
    # filters apply here too — consistent with f_opps. Kept separate from f_specs,
    # which stays date + use_case only so the existing spec sections are unchanged.
    di_specs = [
        s for s in specs
        if in_range(s.get("created_at"))
        and (not use_cases or _use_case(s.get("domain"), s.get("task_type")) in use_cases)
        and (not segments or s.get("segment") in segments)
        and (not regions or s.get("region") in regions)
    ]

    # Prior-period rows for scorecard deltas. Source: re-filter the RAW `specs` /
    # `opps` lists (still in scope here, before the f_* filter) to the immediately
    # preceding equal-length window — no refetch needed. Window length is the
    # current span in days; the prior window is [start - window_len, start) (half-
    # open so it doesn't double-count `start`, which belongs to the current
    # window). Non-date filters (use_case for specs; use_case + segment + region
    # for opps) are applied identically via the same closures. Skipped when
    # date_from is missing (start is None) -> prior stays None.
    prior_specs: Optional[List[Dict[str, Any]]] = None
    prior_opps: Optional[List[Dict[str, Any]]] = None
    if start is not None:
        window_len = (end - start).days
        prior_start = start - timedelta(days=window_len)

        def in_prior(created: Any) -> bool:
            d = _row_date(created)
            return d is not None and prior_start <= d < start

        prior_specs = [
            s for s in specs
            if in_prior(s.get("created_at"))
            and (not use_cases or _use_case(s.get("domain"), s.get("task_type")) in use_cases)
        ]
        prior_opps = [
            o for o in opps
            if in_prior(o.get("created_at"))
            and (not use_cases or opp_uc(o) in use_cases)
            and (not segments or o.get("segment") in segments)
            and (not regions or o.get("region") in regions)
        ]

    # Effective start (for period enumeration) when date_from is "earliest".
    eff_start = start
    if eff_start is None:
        dates = [d for d in (_row_date(r.get("created_at")) for r in f_specs + f_opps) if d]
        eff_start = min(dates) if dates else end
    periods = _enumerate_periods(eff_start, end, cadence)
    pof = lambda d: _period_key(d, cadence)  # noqa: E731

    return {
        "filters": {
            "applied": {
                "date_from": start.isoformat() if start else None,
                "date_to": end.isoformat(),
                "cadence": cadence,
                "use_case": use_cases,
                "segment": segments,
                "region": regions,
            },
            "available_use_cases": available_use_cases,
            "available_segments": available_segments,
            "available_regions": available_regions,
        },
        "win_type_labels": WIN_TYPE_LABELS,
        "data_freshness": _FRESHNESS_NOTE,
        "spec_generation": _section_spec_generation(f_specs, periods, pof),
        "spec_to_opportunity": _section_spec_to_opp(f_hist),
        "opportunity_to_won": _section_opp_to_won(f_opps, periods, pof),
        # Additive (read the already-filtered f_specs / f_opps — inherit filtering):
        "business_funnel": _section_business_funnel(f_specs, f_opps, prior_specs, prior_opps),
        "pipeline_flow": _section_pipeline_flow(f_hist, f_opps),
        "demand_intelligence": _section_demand_intelligence(di_specs),
    }


# --- SECTION 1: Spec Generation (time series) -------------------------------
def _section_spec_generation(
    specs: List[Dict[str, Any]], periods: List[str], pof: Callable[[date], str]
) -> Dict[str, Any]:
    date_of = lambda r: _row_date(r.get("created_at"))  # noqa: E731

    status_keys = ["draft", "in_review", "approved", "rejected"]
    spec_volume_by_status = _series(
        specs, periods, pof, date_of, lambda s: s.get("status"), status_keys
    )
    rejected = [s for s in specs if s.get("status") == "rejected" and s.get("rejection_reason")]
    rejection_volume_by_reason = _series(
        rejected, periods, pof, date_of, lambda s: s.get("rejection_reason"), None
    )
    approved = [s for s in specs if s.get("status") == "approved"]
    approval_volume_by_use_case = _series(
        approved, periods, pof, date_of,
        lambda s: _use_case(s.get("domain"), s.get("task_type")), None,
    )
    return {
        "cadence_periods": periods,
        "spec_volume_by_status": spec_volume_by_status,
        "rejection_volume_by_reason": rejection_volume_by_reason,
        "approval_volume_by_use_case": approval_volume_by_use_case,
    }


def _series(
    rows: List[Dict[str, Any]],
    periods: List[str],
    pof: Callable[[date], str],
    date_of: Callable[[Dict[str, Any]], Optional[date]],
    key_of: Callable[[Dict[str, Any]], Optional[str]],
    fixed_keys: Optional[List[str]],
) -> Dict[str, Any]:
    """Bucket rows into {period -> {key -> count}} and emit a zero-filled,
    period-aligned [{period, <key>: count, ...}] array plus the key set."""
    buckets = {p: Counter() for p in periods}
    seen: set = set()
    for r in rows:
        d = date_of(r)
        if d is None:
            continue
        p = pof(d)
        if p not in buckets:
            continue
        k = key_of(r)
        if not k:
            continue
        buckets[p][k] += 1
        seen.add(k)
    keys = fixed_keys if fixed_keys is not None else sorted(seen)
    data = [
        dict({"period": p}, **{k: buckets[p].get(k, 0) for k in keys}) for p in periods
    ]
    return {"keys": keys, "data": data}


# --- SECTION 2: Spec -> Opportunity (waterfall + velocity) ------------------
def _section_spec_to_opp(hist: List[Dict[str, Any]]) -> Dict[str, Any]:
    entered_ids = {st: set() for st in STAGE_ORDER}
    entered_at: Dict[str, Dict[str, date]] = defaultdict(dict)
    for h in hist:
        st, oid = h.get("stage"), h.get("opportunity_id")
        if st in entered_ids:
            entered_ids[st].add(oid)
            d = _row_date(h.get("entered_at"))
            if d is not None:
                entered_at[oid][st] = d

    # Funnel: distinct opps that entered each stage.
    stages = [{"stage": st, "volume": len(entered_ids[st])} for st in STAGE_ORDER]

    def avg_days(a: str, b_options: List[str]) -> Optional[float]:
        diffs = []
        for smap in entered_at.values():
            if a not in smap:
                continue
            for b in b_options:
                if b in smap:
                    diffs.append((smap[b] - smap[a]).days)
                    break
        return round(sum(diffs) / len(diffs), 1) if diffs else None

    velocity_days = [
        {"from": "Discovery", "to": "Proposal", "avg_days": avg_days("Discovery", ["Proposal"])},
        {"from": "Proposal", "to": "Negotiation", "avg_days": avg_days("Proposal", ["Negotiation"])},
        {"from": "Negotiation", "to": "Closed", "avg_days": avg_days("Negotiation", ["Closed Won", "Closed Lost"])},
    ]
    return {"stages": stages, "velocity_days": velocity_days}


# --- SECTION 3: Opportunity -> Closed Won -----------------------------------
def _section_opp_to_won(
    opps: List[Dict[str, Any]], periods: List[str], pof: Callable[[date], str]
) -> Dict[str, Any]:
    return {
        "pipeline_value_and_volume_by_segment": _value_and_volume(opps, "segment"),
        "win_rate_by_win_type": _win_rate_by_win_type(opps),
        "avg_deal_size_and_growth_by_segment": _avg_deal_size_growth(opps, "segment"),
        "running_acv": _running_acv(opps, periods, pof),
        "revenue_per_win_type": _revenue_per_win_type(opps),
    }


def _value_and_volume(opps: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    """Pipeline value (excludes Closed Lost) + deal volume, grouped by ``key``."""
    out: Dict[str, Dict[str, Any]] = {}
    for o in opps:
        g = out.setdefault(o.get(key) or "Unknown", {"deal_volume": 0, "pipeline_value": 0.0})
        g["deal_volume"] += 1
        if o.get("stage") != "Closed Lost":
            g["pipeline_value"] += float(o.get("amount") or 0.0)
    for g in out.values():
        g["pipeline_value"] = round(g["pipeline_value"], 2)
    return out


def _win_rate_by_win_type(opps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Per win type: win count (deal volume) + win_rate.

    Losses carry no win_type, so win_rate here = wins-of-type / total closed deals
    (won + lost). The four types therefore sum to the overall win rate — a
    composition of how closed pipeline resolved, not a per-type batting average.
    """
    total_closed = sum(1 for o in opps if o.get("stage") in ("Closed Won", "Closed Lost"))
    wins = Counter(
        o.get("win_type") for o in opps if o.get("stage") == "Closed Won" and o.get("win_type")
    )
    return {
        wt: {
            "wins": wins.get(wt, 0),
            "win_rate": round(wins.get(wt, 0) / total_closed, 3) if total_closed else None,
        }
        for wt in WIN_TYPES
    }


def _avg_deal_size_growth(opps: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    """Avg ACV by group + growth (avg of the later half vs the earlier half, in time order)."""
    groups: Dict[str, List[tuple]] = defaultdict(list)
    for o in opps:
        acv, d = o.get("acv"), _row_date(o.get("created_at"))
        if acv is None or d is None:
            continue
        groups[o.get(key) or "Unknown"].append((d, float(acv)))

    out: Dict[str, Any] = {}
    for g, items in groups.items():
        items.sort(key=lambda t: t[0])
        acvs = [a for _, a in items]
        avg = round(sum(acvs) / len(acvs), 2) if acvs else 0.0
        growth = None
        if len(items) >= 2:
            mid = len(items) // 2
            first = [a for _, a in items[:mid]]
            second = [a for _, a in items[mid:]]
            fa = sum(first) / len(first) if first else 0.0
            sa = sum(second) / len(second) if second else 0.0
            growth = round((sa - fa) / fa, 3) if fa else None
        out[g] = {"avg_acv": avg, "growth": growth, "count": len(items)}
    return out


def _running_acv(
    opps: List[Dict[str, Any]], periods: List[str], pof: Callable[[date], str]
) -> List[Dict[str, Any]]:
    """Cumulative ACV (contract value booked) over the time buckets."""
    per = {p: 0.0 for p in periods}
    for o in opps:
        d, acv = _row_date(o.get("created_at")), o.get("acv")
        if d is None or acv is None:
            continue
        p = pof(d)
        if p in per:
            per[p] += float(acv)
    out, run = [], 0.0
    for p in periods:
        run += per[p]
        out.append({"period": p, "acv": round(per[p], 2), "running_acv": round(run, 2)})
    return out


def _revenue_per_win_type(opps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Avg ACV per win type (the efficiency story) + a leader-vs-next note."""
    sums: Dict[str, float] = defaultdict(float)
    counts: Counter = Counter()
    for o in opps:
        if o.get("stage") == "Closed Won" and o.get("win_type") and o.get("acv") is not None:
            sums[o["win_type"]] += float(o["acv"])
            counts[o["win_type"]] += 1
    by_type = {
        wt: {"avg_acv": round(sums[wt] / counts[wt], 2) if counts[wt] else None, "count": counts[wt]}
        for wt in WIN_TYPES
    }

    ranked = sorted(
        ((wt, by_type[wt]["avg_acv"]) for wt in WIN_TYPES if by_type[wt]["avg_acv"]),
        key=lambda t: t[1],
        reverse=True,
    )
    note = None
    if len(ranked) >= 2 and ranked[1][1]:
        lead, second = ranked[0], ranked[1]
        pct = round((lead[1] - second[1]) / second[1] * 100)
        note = (
            f"{WIN_TYPE_LABELS[lead[0]]} averages the highest ACV "
            f"(~{pct}% above {WIN_TYPE_LABELS[second[0]]})"
        )
    return {"by_type": by_type, "note": note}


# --- SECTION 4: Business funnel + scorecards ---------------------------------
def _funnel_metrics(
    specs: List[Dict[str, Any]], opps: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """The shared scorecard metrics over one (specs, opps) pair.

    Reused for both the current window and the prior window (so the deltas are
    apples-to-apples). Terminal state is keyed on ``stage`` (the canonical field):
    won = Closed Won, open = the three pre-terminal stages. ACV uses ``acv`` with
    ``amount`` as a fallback. Conversion rates are 0-1 floats (frontend formats as
    %), divide-by-zero guarded to None.
    """
    terminal = ("Closed Won", "Closed Lost")

    def acv_of(o: Dict[str, Any]) -> float:
        v = o.get("acv")
        return float(v) if v is not None else float(o.get("amount") or 0.0)

    won = [o for o in opps if o.get("stage") == "Closed Won"]
    open_opps = [o for o in opps if o.get("stage") not in terminal]
    n_specs, n_opps, n_won = len(specs), len(opps), len(won)

    return {
        "specs": n_specs,
        "opportunities": n_opps,
        "won": n_won,
        "won_acv": round(sum(acv_of(o) for o in won), 2),
        "open_pipeline": round(sum(float(o.get("amount") or 0.0) for o in open_opps), 2),
        # spec -> opp conversion (all opps / all specs)
        "spec_to_opp_rate": round(n_opps / n_specs, 4) if n_specs else None,
        # blended headline win rate: won over ALL opps (NOT win-among-closed)
        "win_rate_all": round(n_won / n_opps, 4) if n_opps else None,
    }


def _section_business_funnel(
    specs: List[Dict[str, Any]],
    opps: List[Dict[str, Any]],
    prior_specs: Optional[List[Dict[str, Any]]] = None,
    prior_opps: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Scalar scorecards + funnel counts for the current filter, plus a parallel
    ``prior`` block (same metrics over the immediately-preceding equal-length
    window) for MoM-style deltas.

    Inherits filtering for free: ``specs`` is f_specs (date + use_case; specs
    carry no segment) and ``opps`` is f_opps (date + use_case + segment + region).
    ``prior_specs`` / ``prior_opps`` are the same raw lists re-filtered to the
    prior window (computed in _build). ``prior`` is None when the prior window has
    no rows or date_from is missing (frontend then hides deltas).
    """
    terminal = ("Closed Won", "Closed Lost")
    result = _funnel_metrics(specs, opps)
    # `closed` is funnel-tier only (the Sankey/funnel SVG reads it); not in the
    # shared metric set and not needed in `prior`.
    result["closed"] = sum(1 for o in opps if o.get("stage") in terminal)

    if (prior_specs is None and prior_opps is None) or (not prior_specs and not prior_opps):
        result["prior"] = None
    else:
        result["prior"] = _funnel_metrics(prior_specs or [], prior_opps or [])
    return result


# --- SECTION 5: Pipeline FLOW (stage-to-stage transitions, dollar-weighted) ---
def _section_pipeline_flow(
    hist: List[Dict[str, Any]], opps: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Transition-FLOW aggregate: stage-to-stage deal journeys, dollar-weighted.

    Built from f_hist (already filtered) joined to f_opps for amount — amount lives
    on fct_opportunity, NOT on the history rows. For each opp we order its history
    rows by entered_at and pair consecutive (from -> to) transitions where the
    from-row has exited_at NOT NULL (the still-open/terminal row has exited_at
    NULL and is the LAST row; terminal Closed Won/Lost are real stages, so
    Negotiation -> Closed Won etc. fall out naturally). from==to pairs are excluded
    defensively. ``open_now`` carries deals still sitting in each non-terminal
    stage (exited_at IS NULL, stage in OPEN_STAGES) so no deals vanish from the
    diagram. Transitions are emitted in funnel order (by from-rank, then to-rank).

    Inherits filtering for free: in _build, f_hist is already restricted to
    f_opps' opportunity_ids, and f_opps carries the date/use_case/segment/region
    filter — so this aggregate is implicitly filtered the same way.
    """
    amount_of = {
        o["opportunity_id"]: float(o.get("amount") or 0.0)
        for o in opps
        if o.get("opportunity_id")
    }
    rank = {st: i for i, st in enumerate(STAGE_ORDER)}

    by_opp: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for h in hist:
        by_opp[h.get("opportunity_id")].append(h)

    trans_deals: Counter = Counter()
    trans_amount: Dict[tuple, float] = defaultdict(float)
    open_deals: Counter = Counter()
    open_amount: Dict[str, float] = defaultdict(float)

    for oid, rows in by_opp.items():
        amt = amount_of.get(oid, 0.0)
        # Order by entered_at; among any ties, a still-open (exited_at IS NULL) row
        # sorts last so it never becomes a `from` of a transition.
        rows.sort(key=lambda r: (str(r.get("entered_at") or ""), r.get("exited_at") is None))
        for i in range(len(rows) - 1):
            a, b = rows[i], rows[i + 1]
            if a.get("exited_at") is None:
                continue  # didn't transition out (defensive)
            frm, to = a.get("stage"), b.get("stage")
            if not frm or not to or frm == to:
                continue  # exclude from==to (defensive)
            trans_deals[(frm, to)] += 1
            trans_amount[(frm, to)] += amt
        for r in rows:
            if r.get("exited_at") is None and r.get("stage") in OPEN_STAGES:
                open_deals[r.get("stage")] += 1
                open_amount[r.get("stage")] += amt

    transitions = [
        {
            "from": frm,
            "to": to,
            "deals": trans_deals[(frm, to)],
            "amount": round(trans_amount[(frm, to)], 2),
        }
        for (frm, to) in sorted(
            trans_deals, key=lambda p: (rank.get(p[0], 99), rank.get(p[1], 99))
        )
    ]
    open_now = [
        {"stage": st, "deals": open_deals[st], "amount": round(open_amount[st], 2)}
        for st in OPEN_STAGES
        if open_deals[st] > 0
    ]
    return {"transitions": transitions, "open_now": open_now}


# --- SECTION 6: Demand Intelligence (capability-gap / declined demand) --------
def _flags(spec: Dict[str, Any]) -> List[str]:
    """escalation_flags as a list of flag names. PostgREST/jsonb usually decodes
    to a list already, but handle a JSON-string form too (defensive)."""
    v = spec.get("escalation_flags")
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []
    return []


def _section_demand_intelligence(specs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Demand-Intelligence aggregates over the DI-filtered spec list.

    Definitions (decided for this tab):
      * GAP (capability-gap / escalated demand) = matrix_color == 'red' OR a
        non-empty escalation_flags list.
      * DECLINED = status == 'rejected' (demand actually turned away).
      * All dollar figures use estimated_value (present on EVERY spec, all
        statuses), so declined/escalated demand can be dollar-weighted.

    Specs already carry a `segment` (and `region`) from the dim_account join, so
    a spec lands in the (domain, segment) heatmap cell of its account.

    NOTE: the dollar figures here are computed from a synthetic, deterministic seed
    (fixed RNG) and are illustrative of the MECHANISM — how capability gaps and
    declined demand would be dollar-weighted — not a measurement of any real market.
    """
    def ev(s: Dict[str, Any]) -> float:
        return float(s.get("estimated_value") or 0.0)

    def is_gap(s: Dict[str, Any]) -> bool:
        return s.get("matrix_color") == "red" and bool(_flags(s))

    gap = [s for s in specs if is_gap(s)]
    rejected = [s for s in specs if s.get("status") == "rejected"]

    # --- headline ------------------------------------------------------------
    dom_gap_val: Dict[str, float] = defaultdict(float)
    for s in gap:
        dom_gap_val[s.get("domain")] += ev(s)
    top_domain = max(dom_gap_val, key=dom_gap_val.get) if dom_gap_val else None

    headline = {
        "gap_value": round(sum(ev(s) for s in gap), 2),
        "gap_specs": len(gap),
        "declined_value": round(sum(ev(s) for s in rejected), 2),
        "declined_specs": len(rejected),
        "top_domain": top_domain,
    }

    # --- heatmap: one (domain, segment) cell per cell with GAP demand --------
    cells: Dict[tuple, Dict[str, Any]] = defaultdict(
        lambda: {"value": 0.0, "specs": 0, "declined_specs": 0}
    )
    for s in gap:
        c = cells[(s.get("domain"), s.get("segment") or "Unknown")]
        c["value"] += ev(s)
        c["specs"] += 1
        if s.get("status") == "rejected":
            c["declined_specs"] += 1  # rejected among this cell's gap demand
    heatmap = sorted(
        (
            {
                "domain": d, "segment": seg,
                "value": round(c["value"], 2),
                "specs": c["specs"],
                "declined_specs": c["declined_specs"],
            }
            for (d, seg), c in cells.items()
        ),
        key=lambda x: x["value"], reverse=True,
    )

    # --- by_reason: each escalation flag a bucket (a spec with N flags counts in
    #     N reasons); RED specs with NO flag -> a "RED (capability)" bucket so
    #     every gap spec is represented at least once. -------------------------
    reason_val: Dict[str, float] = defaultdict(float)
    reason_cnt: Counter = Counter()
    for s in gap:
        flags = _flags(s)
        if flags:
            for fl in flags:
                reason_val[fl] += ev(s)
                reason_cnt[fl] += 1
        else:
            reason_val["RED (capability)"] += ev(s)
            reason_cnt["RED (capability)"] += 1
    by_reason = sorted(
        (
            {"reason": r, "value": round(reason_val[r], 2), "specs": reason_cnt[r]}
            for r in reason_val
        ),
        key=lambda x: x["value"], reverse=True,
    )

    # --- by_domain: gap_* over gap specs; declined_* over all rejected specs --
    dom: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"gap_value": 0.0, "gap_specs": 0, "declined_value": 0.0, "declined_specs": 0}
    )
    for s in gap:
        d = dom[s.get("domain")]
        d["gap_value"] += ev(s)
        d["gap_specs"] += 1
    for s in rejected:
        d = dom[s.get("domain")]
        d["declined_value"] += ev(s)
        d["declined_specs"] += 1
    by_domain = sorted(
        (
            {
                "domain": dn,
                "gap_value": round(v["gap_value"], 2),
                "gap_specs": v["gap_specs"],
                "declined_value": round(v["declined_value"], 2),
                "declined_specs": v["declined_specs"],
            }
            for dn, v in dom.items()
        ),
        key=lambda x: x["gap_value"], reverse=True,
    )

    return {
        "headline": headline,
        "heatmap": heatmap,
        "by_reason": by_reason,
        "by_domain": by_domain,
    }
