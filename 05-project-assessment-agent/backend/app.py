"""FastAPI app — the warehouse-centric orchestration API (Block 3).
ARCHITECTURE PRINCIPLE: the data warehouse (Supabase) is the HUB — the single
source of truth and the single audit log. Slack, the admin UI, and (in
production) Salesforce are SPOKE CLIENTS that read from and write to the
warehouse, never directly to each other. Every endpoint here is a
warehouse-mutating action; every state change is a queryable row.
This app serves NO UI (that's Block 4). It mounts the routers and exposes the
interactive docs at /docs. Launch with:
    uvicorn app:app --reload      # run from the backend/ directory
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dashboard_routes import router as dashboard_router
from api.review_routes import router as review_router
from api.spec_routes import router as spec_router

app = FastAPI(
    title="Project Assessment Agent — Orchestration API (Block 3)",
    version="0.3.0",
    description=(
        "Warehouse-centric orchestration for the Project Assessment Agent. "
        "Supabase is the hub (source of truth + audit log); Slack/UI/Salesforce "
        "are spoke clients. FastAPI stands in for the production triggers and "
        "both Salesforce sync legs (Fivetran inbound batch, Hightouch outbound "
        "event-driven on approval)."
    ),
)

# CORS — demo only. Lets the Block 4 frontend (served on a different port, or
# opened as a file://) call this API from the browser. allow_credentials must be
# False when allow_origins is the "*" wildcard; this also covers the null origin
# a file:// page sends. Tighten allow_origins for any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spec_router)
app.include_router(review_router)
app.include_router(dashboard_router)


@app.get("/", tags=["meta"])
def root():
    """Liveness + a pointer to the principle this service encodes."""
    return {
        "service": "project-assessment-agent",
        "block": 3,
        "warehouse": "Supabase (hub / single source of truth + audit log)",
        "docs": "/docs",
    }