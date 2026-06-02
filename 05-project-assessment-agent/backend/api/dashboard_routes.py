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

    today = datetime.now(timezone.utc).date()
    df, dt_to = _parse_date(date_from), _parse_date(date_to)
    if df is None and dt_to is None:
        start, end = date(today.year, 1, 1), today      # default: YTD
    else:
        start = df                                       # None -> earliest data
        end = dt_to if dt_to is not None else today      # blank -> today

    # --- pull warehouse models (deleted specs excluded) ----------------------
    specs = select(
        "fct_spec",
        {"status": "neq.deleted"},
        columns="spec_id,status,rejection_reason,domain,task_type,created_at",
    )
    opps = select(
        "fct_opportunity",
        columns="opportunity_id,spec_id,stage,amount,acv,win_type,segment,region,is_won,created_at,closed_at",
    )
    hist = select(
        "fct_opportunity_stage_history",
        columns="opportunity_id,stage,entered_at,exited_at",
    )

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

    # filtered specs: date + use_case (segment/region don't apply to specs)
    f_specs = [
        s for s in specs
        if in_range(s.get("created_at"))
        and (use_case is None or _use_case(s.get("domain"), s.get("task_type")) == use_case)
    ]

    # filtered opps: date + use_case (via the opp's spec) + segment + region
    def opp_uc(o: Dict[str, Any]) -> Optional[str]:
        dm, tt = spec_meta.get(o.get("spec_id"), (None, None))
        return _use_case(dm, tt)

    f_opps = [
        o for o in opps
        if in_range(o.get("created_at"))
        and (use_case is None or opp_uc(o) == use_case)
        and (segment is None or o.get("segment") == segment)
        and (region is None or o.get("region") == region)
    ]
    opp_ids = {o["opportunity_id"] for o in f_opps}
    f_hist = [h for h in hist if h.get("opportunity_id") in opp_ids]

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
                "use_case": use_case,
                "segment": segment,
                "region": region,
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
