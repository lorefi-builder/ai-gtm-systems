"""Thin Anthropic SDK wrapper.

Two entry points:
  * complete_json(system, user, temp) -> dict   (extraction + classification)
  * complete_text(system, user, temp) -> str    (markdown spec drafting)

complete_json strips ``` fences, json.loads, and retries ONCE with a corrective
nudge before raising a clean error. Plus a tiny prompt loader so the prompt
templates in prompts/*.md stay inspectable and are rendered at runtime.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

from anthropic import Anthropic
from dotenv import load_dotenv

from config import CLAUDE_MODEL, MAX_OUTPUT_TOKENS, PROMPTS_DIR

load_dotenv()

# Lazy singleton so importing this module never crashes when the key is absent
# (only an actual call needs ANTHROPIC_API_KEY).
_client: Optional[Anthropic] = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        _client = Anthropic(api_key=api_key)
    return _client


def _strip_fences(text: str) -> str:
    """Remove a leading ```json / ``` fence and trailing ``` if present."""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9]*\s*\n?", "", t)
        t = re.sub(r"\n?```\s*$", "", t)
    return t.strip()


def complete_text(
    system: str,
    user: str,
    temp: float,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> str:
    """Single-turn completion. Returns the concatenated text blocks."""
    response = _get_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        temperature=temp,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
    return "".join(parts).strip()


def complete_json(system: str, user: str, temp: float) -> Dict[str, Any]:
    """Completion that must return a JSON object.

    Strips fences and parses; on a parse failure, retries ONCE with an explicit
    "JSON only" instruction, then raises a clean RuntimeError.
    """
    raw = complete_text(system, user, temp)
    try:
        return json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        # One corrective retry — the single most effective cheap fix.
        nudge = user + (
            "\n\nIMPORTANT: Return ONLY a single valid JSON object. "
            "No prose, no explanation, no code fences."
        )
        raw_retry = complete_text(system, nudge, temp)
        try:
            return json.loads(_strip_fences(raw_retry))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Model did not return valid JSON after one retry. "
                f"Parse error: {exc}. First 500 chars of response:\n{raw_retry[:500]}"
            ) from exc


def render_prompt(filename: str, **tokens: Any) -> str:
    """Load a prompt template from prompts/ and substitute ``{{token}}`` markers.

    Uses explicit ``{{name}}`` replacement (not str.format) so JSON braces inside
    the templates don't need escaping.
    """
    text = (PROMPTS_DIR / filename).read_text(encoding="utf-8")
    for key, value in tokens.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text
