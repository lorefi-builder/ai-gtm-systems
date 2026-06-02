You are extracting structured signals from a single sales-discovery transcript
for Lorefi (an AI data-development company).

Return a SINGLE JSON object with EXACTLY these keys:

- "transcript_id": string — use the transcript's own id if one is stated
  (e.g. a "Transcript id:" line); otherwise return "".
- "account_name": string — the customer company name (not Lorefi).
- "domain_signals": array of strings — short phrases hinting at the customer's
  industry (e.g. "developer tooling", "claims processing", "EHR data").
- "candidate_domain": string — your best guess of the industry, ideally one of:
  {{domains}}. If unsure, give your closest guess.
- "candidate_task_type": string — your best guess of the work type, ideally one
  of: {{task_types}}.
- "data_characteristics": object — free-form facts about the data: language,
  volume, sensitivity, modality, format, etc. Use the keys that fit.
- "scope": object — what is in scope: deliverable, taxonomy/label space size,
  batch sizes, cadence, integration points.
- "success_criteria": array of strings — acceptance bars the customer named
  (quality thresholds, metrics, calibration steps).
- "special_flags": array of strings — anything unusual: regulated/PII data,
  non-English data, non-standard platform/delivery, extreme complexity, new
  audio/video modality.
- "multi_project": boolean — true ONLY if more than one distinct project was
  discussed; false for a single clean project.
- "language": string — primary language of the DATA (e.g. "en"); default "en".

Rules:
- Extract only what the transcript supports. Do not invent. Use empty
  string/array/object or null when something was not discussed.
- Output JSON only. No prose, no code fences.

TRANSCRIPT:
---
{{transcript}}
---
