"""Orchestration layer (Block 3).

Stands in for warehouse-triggered jobs and the two Salesforce sync legs:
  * orchestrator.py — runs the agent pipeline (LISTEN/NOTIFY trigger analog)
  * lifecycle.py    — guarded status transitions + audit log + approval fan-out
                      (the Hightouch reverse-ETL analog)
  * slack_messages.py — Slack-faithful payloads (not posted; rendered in Block 4)
"""
