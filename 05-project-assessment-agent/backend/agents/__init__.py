"""Project Assessment Agent — the AI core (Block 2).

Two agents wired by a CLI orchestrator:

    Agent 1 (extract) -> dedup -> Agent 2 (classify -> estimate -> draft)
    -> Slack-style summary -> write to DB.

Three layers are kept visibly separate throughout:
    VERIFIED  — facts read from the DB via the existing client (estimate.py)
    JUDGMENT  — LLM calls (extract.py, classify.py, draft.py)
    LOOKUP    — deterministic capability-matrix color (classify.py)

Entry point: ``python -m agents.run <transcript.md>``.
"""
