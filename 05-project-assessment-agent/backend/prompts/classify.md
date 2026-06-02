Classify this discovery call into Lorefi's canonical taxonomy.

You MUST choose exactly one value from each fixed list — do not invent new
categories.

Valid domains: {{domains}}
Valid task types: {{task_types}}

Agent 1 already extracted:
- candidate_domain: {{candidate_domain}}
- candidate_task_type: {{candidate_task_type}}
- domain_signals: {{signals}}
- scope: {{scope}}

Return a SINGLE JSON object with EXACTLY these keys:

- "domain": string — one of the valid domains, exactly as written above.
- "task_type": string — one of the valid task types, exactly as written above.
- "confidence": number between 0 and 1 — your honest confidence in this
  (domain, task_type) pair given the transcript. Lower it when the call is
  ambiguous, mixes multiple projects, or lacks detail.
- "reasoning": string — one or two sentences justifying the choice.
- "escalation_flags": array of strings — include ONLY the LLM-judged flags that
  clearly apply, each exactly one of:
    "nonstandard_platform"  (on-prem / air-gapped / bespoke tooling / unusual delivery)
    "extreme_complexity"    (taxonomy depth or expertise bar far above baseline)
    "new_modality_av"       (audio or video data outside standard pipelines)
  Do NOT include PII or non-English flags here — those are detected separately.

Output JSON only. No prose, no code fences.

TRANSCRIPT:
---
{{transcript}}
---
