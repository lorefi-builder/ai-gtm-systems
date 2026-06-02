"""Thin Supabase PostgREST client.

Talks to Supabase's auto-generated REST API directly over httpx — no
`supabase` SDK. Uses the SERVICE key only, so this module is **server-side
only**; never ship the service key to a browser or client.

Environment:
    SUPABASE_URL          e.g. https://<project-ref>.supabase.co
    SUPABASE_SERVICE_KEY  the service_role key (bypasses RLS)

PostgREST reference: https://postgrest.org/en/stable/references/api.html
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

# --- configuration ----------------------------------------------------------

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")

# PostgREST is mounted under /rest/v1 on Supabase.
REST_ROOT = f"{SUPABASE_URL}/rest/v1"

# Tune for bulk seeding; PostgREST itself has no hard request timeout.
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _require_config() -> None:
    """Fail fast with an actionable message if env is missing."""
    missing = [
        name
        for name, value in (
            ("SUPABASE_URL", SUPABASE_URL),
            ("SUPABASE_SERVICE_KEY", SUPABASE_SERVICE_KEY),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing env var(s): {', '.join(missing)}. "
            "Copy .env.example to .env and fill in your Supabase project values."
        )


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Standard auth + content headers for every PostgREST call."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def _raise_for_status(response: httpx.Response) -> None:
    """Surface PostgREST's JSON error body instead of a bare status code."""
    if response.is_error:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise httpx.HTTPStatusError(
            f"PostgREST {response.status_code} for {response.request.method} "
            f"{response.request.url}: {detail}",
            request=response.request,
            response=response,
        )


# --- public API -------------------------------------------------------------


def insert(table: str, rows: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    """Insert one row (dict) or many (list of dicts) into ``table``.

    Returns the inserted rows (PostgREST ``return=representation``), which is
    handy for grabbing server-generated defaults like ``gen_random_uuid()``
    when you did not supply the id yourself.
    """
    _require_config()
    payload = rows if isinstance(rows, list) else [rows]
    if not payload:
        return []

    with httpx.Client(timeout=_TIMEOUT) as client:
        response = client.post(
            f"{REST_ROOT}/{table}",
            headers=_headers({"Prefer": "return=representation"}),
            json=payload,
        )
    _raise_for_status(response)
    return response.json()


def select(
    table: str,
    filters: dict[str, Any] | None = None,
    *,
    columns: str = "*",
    order: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Select rows from ``table``.

    ``filters`` maps column -> value for simple equality (``col=eq.value``).
    For other operators pass the PostgREST form as the value, e.g.
    ``{"amount": "gte.1000"}`` or ``{"status": "in.(approved,in_review)"}``.
    """
    _require_config()
    params: dict[str, str] = {"select": columns}

    for column, value in (filters or {}).items():
        # If the caller already encoded an operator (e.g. "gte.1000"), pass it
        # through; otherwise default to equality.
        params[column] = value if _has_operator(value) else f"eq.{value}"

    if order is not None:
        params["order"] = order
    if limit is not None:
        params["limit"] = str(limit)

    with httpx.Client(timeout=_TIMEOUT) as client:
        response = client.get(
            f"{REST_ROOT}/{table}",
            headers=_headers(),
            params=params,
        )
    _raise_for_status(response)
    return response.json()


def upsert(
    table: str,
    rows: list[dict[str, Any]] | dict[str, Any],
    *,
    on_conflict: str | None = None,
) -> list[dict[str, Any]]:
    """Insert rows, updating on primary-key (or ``on_conflict``) collision.

    ``on_conflict`` is a comma-separated column list naming the unique
    constraint to merge on, e.g. ``"domain,task_type"`` for the matrix.
    """
    _require_config()
    payload = rows if isinstance(rows, list) else [rows]
    if not payload:
        return []

    params: dict[str, str] = {}
    if on_conflict is not None:
        params["on_conflict"] = on_conflict

    with httpx.Client(timeout=_TIMEOUT) as client:
        response = client.post(
            f"{REST_ROOT}/{table}",
            headers=_headers(
                {"Prefer": "resolution=merge-duplicates,return=representation"}
            ),
            params=params,
            json=payload,
        )
    _raise_for_status(response)
    return response.json()


# --- helpers ----------------------------------------------------------------

# PostgREST operators that may appear as a "<op>.<value>" filter value.
_OPERATORS = (
    "eq.", "neq.", "gt.", "gte.", "lt.", "lte.", "like.", "ilike.",
    "in.", "is.", "cs.", "cd.", "fts.", "match.",
)


def _has_operator(value: Any) -> bool:
    """True if a filter value is already an encoded PostgREST operator."""
    return isinstance(value, str) and value.startswith(_OPERATORS)
