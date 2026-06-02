Write a draft project specification for a Lorefi engagement, in markdown.

Follow these SIX sections, in this exact order, using these exact headings:

## 1. Overview & Context
## 2. Requirements
## 3. Contributor Guidelines
## 4. Acceptance Criteria
## 5. Deliverables & Format
## 6. Timeline & Milestones

Guidance per section:
- Overview & Context: who the customer is, the business problem, and the
  assessment outcome (domain × task type, capability color).
- Requirements: split into sample-level (what one labeled/processed item must
  contain) and dataset-level (volume, splits, gold set, cadence).
- Contributor Guidelines: who staffs this and the rules they follow
  (taxonomy, edge-case handling, flag-don't-guess policy).
- Acceptance Criteria: measurable bars (carry over the customer's stated
  success criteria; make them concrete and testable).
- Deliverables & Format: file formats, delivery mechanism, reporting.
- Timeline & Milestones: a Pilot → Production progression with a calibration
  gate before scaling.

Ground everything in the inputs below and the example specs. Do NOT add scope
the customer did not ask for. Aim for roughly 3-4 pages. Output markdown only.

=== ASSESSMENT ===
Account: {{account}}
Domain × Task type: {{domain}} × {{task_type}}
Capability color: {{color}}
Recommended resourcing: {{resourcing}}

=== EXTRACTED SCOPE ===
{{scope}}

=== DATA CHARACTERISTICS ===
{{requirements}}

=== CUSTOMER SUCCESS CRITERIA ===
{{success_criteria}}

=== RETRIEVED EXAMPLE SPECS (for grounding tone + structure) ===
{{rag_examples}}
