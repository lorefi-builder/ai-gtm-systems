// ============================================================================
// static-data.js — STATIC REPLAY mode for the SpecOps demo (Vercel, no backend).
//
// PURE ADDITION. The mere PRESENCE of this file (included via <script> BEFORE
// app.js, in the DEPLOYED copy only) flips the app into replay mode: api() in
// app.js returns the baked payloads below instead of hitting the FastAPI
// backend. OMIT this file (local dev) and behavior is 100% unchanged — every
// call hits the real backend exactly as today (window.STATIC_REPLAY is then
// undefined → all the guards in app.js are no-ops).
//
// Load order (deployed): transcripts.js → static-data.js → app.js
// ============================================================================

window.STATIC_REPLAY = true;

// Delay (ms) before the replayed POST /spec resolves, so app.js's client-side
// "extracting… classifying… drafting…" pre-roll animation reads as a real
// multi-second pipeline run. Other paths resolve near-immediately.
window.STATIC_DELAY_MS = 1400;

// ----------------------------------------------------------------------------
// CAPTURED PAYLOADS — paste the real captured JSON over each `null` below.
// Each is the RESPONSE BODY of one live call (see frontend README / the capture
// notes). Capture them from ONE coherent happy-path run so the spec_id /
// opportunity_id chain is internally consistent across /spec, /review, /approve.
// ----------------------------------------------------------------------------

// <<< PASTE spec.json here — the POST /spec response body (status:"draft_created",
//     spec_id, slack_message, draft_spec, classification, …)
const SPEC_PAYLOAD = {
    "status": "draft_created",
    "spec_id": "466a68b4-e7bd-4843-8388-12cff4d2be71",
    "needs_human_review": false,
    "review_reason": null,
    "classification": {
        "domain": "Financial Services",
        "task_type": "Data Labeling",
        "color": "green",
        "confidence": 0.95,
        "reasoning": "The engagement is squarely in financial services (SEC filings, EDGAR, analyst queries, cash flow analysis) and the core deliverable is a custom annotated dataset: human experts labeling correct documents, hard negatives, passage-level spans, and reasoning-oriented answers for retrieval and QA tasks — all canonical data labeling work. No ambiguity exists about domain or task type.",
        "escalation_flags": [],
        "needs_human_review": false,
        "review_reason": null
    },
    "summary": "*Project Assessment — Draft Spec Ready*\n\n• *Project:* Veritas Analytics — Financial Services × Data Labeling\n    _deliverable: custom financial information-retrieval dataset: queries over a corpus of financial documents with labeled correct documents, hard negatives, passage-level provenance, and reasoning-oriented answers; taxonomy_label_space: binary relevance labels (not ranked); correct document(s) identified by EDGAR ID; passage-level spans; answer with reasoning; task complexity tiers (weighted toward tier 3); batch_sizes: not finalized; sample batch first, then ramp based on pricing agreement_\n• *Classification:* 🟢 GREEN — The engagement is squarely in financial services (SEC filings, EDGAR, analyst queries, cash flow analysis) and the core deliverable is a custom annotated datase…\n• *Resourcing:* EC 8 · TDM 2 · DOps 2 · FDE 1\n• *Risks / review:*\n    🆕 Net-new account (stub created in dim_account)\n• *Links:* spec_id `466a68b4-e7bd-4843-8388-12cff4d2be71` (live links added in Block 3)",
    "draft_spec": "# Project Specification — Veritas Analytics\n**Lorefi Engagement · Financial Services × Data Labeling · Capability: Green**\n*Draft for Customer Review*\n\n---\n\n## 1. Overview & Context\n\n**Account:** Veritas Analytics\n**Domain × Task Type:** Financial Services × Data Labeling\n**Capability Color:** Green — Lorefi has established delivery patterns for this domain and task type; no novel capability build is required before production ramp.\n\nVeritas Analytics is building a custom financial information-retrieval dataset to train and evaluate retrieval and reasoning models used by financial analysts. The core business problem is that existing public benchmarks do not reflect the query distributions, document complexity, or reasoning depth that characterize real analyst workflows. Veritas needs a purpose-built dataset grounded in actual user behavior and sourced from the authoritative public corpus of SEC filings via EDGAR.\n\nThe engagement covers four interconnected task types: multi-document retrieval with hard negatives, reasoning over extracted financial information, systematic extraction across companies and time periods, and passage-level annotation. The primary document source is public SEC filings (EDGAR); private documents are deprioritized due to sourcing complexity and are out of scope for this specification unless a written change order is issued.\n\n**Recommended Resourcing:**\n| Role | Count |\n|---|---|\n| Expert Contributors (EC) | 8 |\n| Technical Delivery Manager (TDM) | 2 |\n| Data Operations (DOps) | 2 |\n| Forward-Deployed Engineer (FDE) | 1 |\n\nFinance-domain experts are required for reasoning and retrieval tasks. Generalist contributors are acceptable for systematic extraction sub-tasks where judgment demands are lower.\n\n---\n\n## 2. Requirements\n\n### Sample-Level Requirements\n\nEach labeled item in the dataset must contain all of the following fields:\n\n| Field | Description |\n|---|---|\n| **Query** | A natural-language question reflecting a realistic analyst query, informed by Veritas's anonymized query cluster data. |\n| **Candidate Pool** | A set of hundreds of candidate documents per task, drawn from EDGAR, sufficient to make retrieval non-trivial. |\n| **Correct Document(s)** | Binary relevance label (relevant / not relevant — not ranked); each relevant document identified by its EDGAR filing ID. |\n| **Hard Negatives** | At minimum one hard negative per item, drawn from: same filing type / different company (same period); numerically similar but incorrect; or semantically similar but technically distinct. Hard negatives must be genuinely challenging, not superficially different. |\n| **Passage-Level Span(s)** | Character- or token-level span(s) within the correct document(s) that ground the answer; EDGAR document section and page reference included where available. |\n| **Answer with Reasoning** | A written answer that synthesizes the relevant passage(s); for tier 3 tasks, the answer must demonstrate multi-document reasoning and explicit chain-of-thought. |\n| **Task Complexity Tier** | Tier 1 (single-document extraction), Tier 2 (single-document reasoning), or Tier 3 (multi-document synthesis). Dataset must be weighted toward Tier 3. |\n| **Metadata** | EDGAR filing type (e.g., 10-K, 10-Q, 8-K), company identifier, reporting period, contributor ID, and timestamp. |\n\nItems that cannot be fully completed — e.g., because a passage span cannot be confidently identified — must be flagged for review rather than submitted with a guess.\n\n### Dataset-Level Requirements\n\n| Parameter | Specification |\n|---|---|\n| **Volume Target** | Queries in the tens of thousands; document corpus in the tens of thousands of filings. Exact volumes finalized in pricing agreement. |\n| **Complexity Weighting** | Tier 3 tasks constitute the majority of the dataset; exact split agreed at calibration gate. |\n| **Splits** | Train, validation, and test splits defined before production ramp; test split held out and not exposed to contributors after initial construction. |\n| **Gold Set** | A held-out gold set constructed during the pilot phase, adjudicated by senior finance experts, used for ongoing quality measurement and drift detection. |\n| **Hard Negative Ratio** | Minimum one hard negative per query item; target ratio and negative type distribution agreed at calibration gate. |\n| **Cadence** | Sample batch delivered first. Production ramp cadence (batch size, frequency) finalized following pricing agreement and pilot sign-off. |\n| **Document Source** | Public SEC filings via EDGAR. Veritas may supply target company lists or document identifiers; Veritas will share anonymized query clusters to inform query construction. |\n\n---\n\n## 3. Contributor Guidelines\n\n### Staffing\n\nFinance-domain expert contributors (EC) are required for all retrieval, reasoning, and passage annotation tasks. Generalist contributors may be assigned to systematic extraction sub-tasks (e.g., pulling 10–15 defined metrics across companies and time periods) where the label criteria are fully specified and judgment demands are low. All contributors are onboarded to the taxonomy before touching live data.\n\n### Taxonomy & Label Space\n\n- **Relevance labels** are binary: a document is either relevant to the query or it is not. Contributors do not rank documents.\n- **EDGAR IDs** are the required identifier for all correct documents; free-text document descriptions are not acceptable as a substitute.\n- **Passage spans** must be drawn directly from the source filing text; paraphrase or reconstruction is not permitted.\n- **Answers** must be grounded in the identified spans. For Tier 3 tasks, the reasoning chain must be explicit and traceable to specific passages across documents.\n- **Hard negatives** must be selected according to the approved negative typology (same filing type / different company; numerically similar but wrong; semantically similar but technically different). Contributors may not substitute easy negatives to complete a task faster.\n- **Complexity tier** is assigned by the contributor and reviewed by the TDM; when in doubt, tier up rather than down.\n\n### Edge-Case Handling\n\n- If a query cannot be answered from the available EDGAR corpus with high confidence, the item is **flagged**, not completed with a guess.\n- If a passage span is ambiguous across multiple sections, **all plausible spans are marked** and the item is escalated to a senior reviewer.\n- If a candidate document pool contains fewer than the required minimum number of candidates, the item is **held** and reported to DOps for pool augmentation before labeling proceeds.\n- Taxonomy questions and novel edge cases are escalated to the TDM in writing; contributors do not resolve ambiguity unilaterally.\n\n### Flag-Don't-Guess Policy\n\nAny item where the contributor is not confident in the correct document identification, passage span, or reasoning answer must be flagged for senior review. Submitting a low-confidence label as if it were high-confidence is a quality violation.\n\n---\n\n## 4. Acceptance Criteria\n\nThe following bars must be met before the engagement advances from pilot to production, and must be maintained throughout production delivery. All criteria are measurable against the gold set and/or sample review.\n\n| Criterion | Measurable Bar |\n|---|---|\n| **Retrieval Correctness** | ≥ 95% of gold-set items have the correct EDGAR-identified document(s) labeled as relevant; measured by exact-match against adjudicated gold labels. |\n| **Passage Provenance** | 100% of submitted items include at least one passage-level span; spans must fall within the identified correct document. Zero items submitted without a span. |\n| **Hard Negative Quality** | ≥ 90% of hard negatives reviewed in the gold set are assessed by senior reviewers as \"genuinely challenging\" per the approved typology; superficially easy negatives are a defect. |\n| **Candidate Pool Size** | 100% of task items have a candidate pool of at least 100 documents; target of hundreds per task confirmed at calibration gate. |\n| **Query Distribution Alignment** | Query set reviewed by Veritas against their internal query cluster analysis before production ramp; sign-off required that queries reflect realistic analyst distributions. |\n| **Complexity Tier Weighting** | Tier 3 tasks constitute the agreed majority share of delivered items; measured per batch and reported in delivery summary. |\n| **Inter-Annotator Agreement** | Agreement on binary relevance labels and passage span selection at or above the kappa threshold agreed at the calibration gate; reported per delivery batch. |\n| **Pilot Sign-Off** | Veritas provides written sign-off on the pilot sample before production ramp begins. No production work commences without this gate. |\n\n---\n\n## 5. Deliverables & Format\n\n### Primary Deliverable\n\nA custom financial information-retrieval dataset delivered as structured files, containing queries, candidate pools, binary relevance labels, EDGAR document identifiers, passage-level spans, reasoning answers, complexity tier labels, and full item-level metadata.\n\n### File Format\n\n| Asset | Format |\n|---|---|\n| Dataset (queries, labels, answers, metadata) | JSON Lines (`.jsonl`), one item per line; schema documented and versioned. |\n| Passage spans | Inline within the JSON item; character offsets relative to the source EDGAR document text. |\n| Gold set | Separate `.jsonl` file; adjudication notes included as a field. |\n| Delivery manifest | `.csv` per batch listing item IDs, contributor IDs, complexity tiers, and QA status. |\n| Quality report | `.pdf` or `.md` per batch summarizing agreement scores, defect rates, flag rates, and tier distribution. |\n\n### Delivery Mechanism\n\nFiles delivered via the secure transfer method agreed with Veritas during onboarding. The FDE is responsible for ingest and export integration with Veritas's receiving environment. EDGAR document text is sourced programmatically; Veritas may supply supplemental company target lists or document ID lists via the same secure channel.\n\n### Reporting\n\nA written quality report accompanies every batch delivery. The report includes: inter-annotator agreement on the gold set, defect counts by type, flag rate, hard negative quality assessment, tier distribution, and any open escalations. Anomalies are surfaced immediately; they are not held for the batch report.\n\n---\n\n## 6. Timeline & Milestones\n\n| Phase | Milestone | Gate Condition |\n|---|---|---|\n| **Onboarding** | Taxonomy finalized; contributor onboarding complete; EDGAR access and secure transfer confirmed; Veritas query cluster data received. | All inputs confirmed in writing before pilot work begins. |\n| **Pilot** | Sample batch delivered to Veritas for review. Batch size TBD at pricing agreement; representative of all task types and complexity tiers. | Pilot delivered within agreed timeline from onboarding completion. |\n| **Calibration Gate** | Veritas reviews pilot sample; inter-annotator agreement measured against gold set; hard negative quality reviewed; query distribution alignment confirmed. | Written sign-off from Veritas required. No production ramp without this gate. Defects above threshold trigger a remediation round before sign-off. |\n| **Production Ramp** | Batch delivery begins at cadence agreed in pricing; volume ramps to target over agreed schedule. | Cadence and batch sizes finalized in pricing agreement. |\n| **Ongoing Production** | Steady-state delivery with per-batch quality reports; gold set refreshed periodically to detect drift. | Quality bars from Section 4 maintained each batch; issues escalated within 24 hours. |\n| **Completion** | Full volume delivered; final dataset manifest and quality summary provided to Veritas. | Veritas confirms receipt and acceptance of final delivery. |\n\n> **Note on Timeline Dates:** Specific calendar dates are not fixed in this specification. They will be agreed in the pricing and project kickoff documents. This specification governs scope, quality, and process; the project plan governs dates.\n\n---\n\n*This specification is the reference document for the Veritas Analytics engagement. Any changes to scope, taxonomy, volume, or format require a written change order signed by both parties. Questions should be directed to the assigned Technical Delivery Manager.*",
    "slack_message": {
        "channel": "@U_DEMO",
        "text": "*Project Assessment — Draft Spec Ready*\n\n• *Project:* Veritas Analytics — Financial Services × Data Labeling\n    _deliverable: custom financial information-retrieval dataset: queries over a corpus of financial documents with labeled correct documents, hard negatives, passage-level provenance, and reasoning-oriented answers; taxonomy_label_space: binary relevance labels (not ranked); correct document(s) identified by EDGAR ID; passage-level spans; answer with reasoning; task complexity tiers (weighted toward tier 3); batch_sizes: not finalized; sample batch first, then ramp based on pricing agreement_\n• *Classification:* 🟢 GREEN — The engagement is squarely in financial services (SEC filings, EDGAR, analyst queries, cash flow analysis) and the core deliverable is a custom annotated datase…\n• *Resourcing:* EC 8 · TDM 2 · DOps 2 · FDE 1\n• *Risks / review:*\n    🆕 Net-new account (stub created in dim_account)\n• *Links:* spec_id `466a68b4-e7bd-4843-8388-12cff4d2be71` (live links added in Block 3)",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Project Assessment — Draft Spec Ready*\n\n• *Project:* Veritas Analytics — Financial Services × Data Labeling\n    _deliverable: custom financial information-retrieval dataset: queries over a corpus of financial documents with labeled correct documents, hard negatives, passage-level provenance, and reasoning-oriented answers; taxonomy_label_space: binary relevance labels (not ranked); correct document(s) identified by EDGAR ID; passage-level spans; answer with reasoning; task complexity tiers (weighted toward tier 3); batch_sizes: not finalized; sample batch first, then ramp based on pricing agreement_\n• *Classification:* 🟢 GREEN — The engagement is squarely in financial services (SEC filings, EDGAR, analyst queries, cash flow analysis) and the core deliverable is a custom annotated datase…\n• *Resourcing:* EC 8 · TDM 2 · DOps 2 · FDE 1\n• *Risks / review:*\n    🆕 Net-new account (stub created in dim_account)\n• *Links:* spec_id `466a68b4-e7bd-4843-8388-12cff4d2be71` (live links added in Block 3)"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Send to review"
                        },
                        "action_id": "send_to_review",
                        "value": "{\"spec_id\": \"466a68b4-e7bd-4843-8388-12cff4d2be71\"}",
                        "style": "primary"
                    }
                ]
            }
        ],
        "spec_id": "466a68b4-e7bd-4843-8388-12cff4d2be71",
        "needs_human_review": false
    }
};

// <<< PASTE review.json here — the POST /review response body
//     (status:"in_review", spec_id, slack_message). Its spec_id MUST match SPEC_PAYLOAD.
const REVIEW_PAYLOAD = {
    "status": "in_review",
    "spec_id": "466a68b4-e7bd-4843-8388-12cff4d2be71",
    "slack_message": {
        "channel": "#spec-review",
        "text": "Spec `466a68b4-e7bd-4843-8388-12cff4d2be71` is ready for review (from @U_DEMO).",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Review requested* by @U_DEMO\nSpec `466a68b4-e7bd-4843-8388-12cff4d2be71` is now *in review*. Approvers: @tdm-oncall · @solutions-lead"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Approve"
                        },
                        "action_id": "approve_spec",
                        "value": "{\"spec_id\": \"466a68b4-e7bd-4843-8388-12cff4d2be71\"}",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Reject"
                        },
                        "action_id": "reject_spec",
                        "value": "{\"spec_id\": \"466a68b4-e7bd-4843-8388-12cff4d2be71\"}",
                        "style": "danger"
                    }
                ]
            }
        ],
        "spec_id": "466a68b4-e7bd-4843-8388-12cff4d2be71"
    }
};

// <<< PASTE approve.json here — the POST /approve response body
//     (status:"approved", spec_id, opportunity_id, slack_message). spec_id MUST match.
const APPROVE_PAYLOAD = {
    "status": "approved",
    "spec_id": "466a68b4-e7bd-4843-8388-12cff4d2be71",
    "opportunity_id": "f2b2b963-ea21-4711-b9ae-3007881cf1fe",
    "slack_message": {
        "channel": "#deal-tracking",
        "text": ":white_check_mark: Spec `466a68b4-e7bd-4843-8388-12cff4d2be71` approved by @U_DEMO — opportunity created.",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":white_check_mark: *Spec approved* by @U_DEMO\nOpportunity `f2b2b963-ea21-4711-b9ae-3007881cf1fe` created at *Discovery*.\n*Veritas Analytics – Data Labeling Program* — Mid-Market / NA · $146,049 · owner unassigned@lorefi.com"
                }
            }
        ],
        "spec_id": "466a68b4-e7bd-4843-8388-12cff4d2be71",
        "opportunity_id": "f2b2b963-ea21-4711-b9ae-3007881cf1fe"
    }
};

// <<< PASTE dashboard-data.json here — the GET /dashboard-data response body
//     (filters, spec_generation, …, business_funnel, pipeline_flow, demand_intelligence).
const DASHBOARD_PAYLOAD = {
    "filters": {
        "applied": {
            "date_from": "2025-12-01",
            "date_to": "2026-06-03",
            "cadence": "monthly",
            "use_case": [],
            "segment": [],
            "region": []
        },
        "available_use_cases": [
            "Financial Services · Code Review",
            "Financial Services · Content Gen",
            "Financial Services · Conversational AI",
            "Financial Services · Data Labeling",
            "Financial Services · Doc Process",
            "Financial Services · Model Eval",
            "Government · Code Review",
            "Government · Content Gen",
            "Government · Conversational AI",
            "Government · Data Labeling",
            "Government · Doc Process",
            "Government · Model Eval",
            "Healthcare · Code Review",
            "Healthcare · Content Gen",
            "Healthcare · Conversational AI",
            "Healthcare · Data Labeling",
            "Healthcare · Doc Process",
            "Healthcare · Model Eval",
            "Legal · Code Review",
            "Legal · Content Gen",
            "Legal · Conversational AI",
            "Legal · Data Labeling",
            "Legal · Doc Process",
            "Legal · Model Eval",
            "Retail · Code Review",
            "Retail · Content Gen",
            "Retail · Conversational AI",
            "Retail · Data Labeling",
            "Retail · Doc Process",
            "Retail · Model Eval",
            "Technology · Code Review",
            "Technology · Content Gen",
            "Technology · Conversational AI",
            "Technology · Data Labeling",
            "Technology · Doc Process",
            "Technology · Model Eval"
        ],
        "available_segments": [
            "Enterprise",
            "Mid-Market",
            "SMB"
        ],
        "available_regions": [
            "APAC",
            "EMEA",
            "LATAM",
            "NA"
        ]
    },
    "win_type_labels": {
        "new_logo": "New Logo",
        "prior_loss_now_won": "Prior Loss · Now Won",
        "renewal": "Renewal",
        "reactivation": "Reactivation"
    },
    "data_freshness": "Opportunity-stage data is as of the last inbound sync (Fivetran), up to a few hours old in production. Spec-generation data is live from the warehouse. This demo reads live; the note documents the production eventual-consistency caveat.",
    "spec_generation": {
        "cadence_periods": [
            "2025-12",
            "2026-01",
            "2026-02",
            "2026-03",
            "2026-04",
            "2026-05",
            "2026-06"
        ],
        "spec_volume_by_status": {
            "keys": [
                "draft",
                "in_review",
                "approved",
                "rejected"
            ],
            "data": [
                {
                    "period": "2025-12",
                    "draft": 0,
                    "in_review": 0,
                    "approved": 13,
                    "rejected": 1
                },
                {
                    "period": "2026-01",
                    "draft": 0,
                    "in_review": 0,
                    "approved": 33,
                    "rejected": 2
                },
                {
                    "period": "2026-02",
                    "draft": 0,
                    "in_review": 0,
                    "approved": 65,
                    "rejected": 16
                },
                {
                    "period": "2026-03",
                    "draft": 0,
                    "in_review": 9,
                    "approved": 92,
                    "rejected": 18
                },
                {
                    "period": "2026-04",
                    "draft": 10,
                    "in_review": 39,
                    "approved": 62,
                    "rejected": 15
                },
                {
                    "period": "2026-05",
                    "draft": 62,
                    "in_review": 51,
                    "approved": 9,
                    "rejected": 3
                },
                {
                    "period": "2026-06",
                    "draft": 0,
                    "in_review": 0,
                    "approved": 2,
                    "rejected": 1
                }
            ]
        },
        "rejection_volume_by_reason": {
            "keys": [
                "data_sensitivity_unaddressed",
                "insufficient_contributor_guidelines",
                "missing_acceptance_criteria",
                "scope too broad. multiproject. pii_regulated",
                "scope_too_broad",
                "wrong_task_type"
            ],
            "data": [
                {
                    "period": "2025-12",
                    "data_sensitivity_unaddressed": 0,
                    "insufficient_contributor_guidelines": 0,
                    "missing_acceptance_criteria": 0,
                    "scope too broad. multiproject. pii_regulated": 0,
                    "scope_too_broad": 0,
                    "wrong_task_type": 1
                },
                {
                    "period": "2026-01",
                    "data_sensitivity_unaddressed": 0,
                    "insufficient_contributor_guidelines": 0,
                    "missing_acceptance_criteria": 2,
                    "scope too broad. multiproject. pii_regulated": 0,
                    "scope_too_broad": 0,
                    "wrong_task_type": 0
                },
                {
                    "period": "2026-02",
                    "data_sensitivity_unaddressed": 5,
                    "insufficient_contributor_guidelines": 3,
                    "missing_acceptance_criteria": 2,
                    "scope too broad. multiproject. pii_regulated": 0,
                    "scope_too_broad": 2,
                    "wrong_task_type": 4
                },
                {
                    "period": "2026-03",
                    "data_sensitivity_unaddressed": 2,
                    "insufficient_contributor_guidelines": 5,
                    "missing_acceptance_criteria": 3,
                    "scope too broad. multiproject. pii_regulated": 0,
                    "scope_too_broad": 6,
                    "wrong_task_type": 2
                },
                {
                    "period": "2026-04",
                    "data_sensitivity_unaddressed": 4,
                    "insufficient_contributor_guidelines": 2,
                    "missing_acceptance_criteria": 6,
                    "scope too broad. multiproject. pii_regulated": 0,
                    "scope_too_broad": 1,
                    "wrong_task_type": 2
                },
                {
                    "period": "2026-05",
                    "data_sensitivity_unaddressed": 1,
                    "insufficient_contributor_guidelines": 1,
                    "missing_acceptance_criteria": 1,
                    "scope too broad. multiproject. pii_regulated": 0,
                    "scope_too_broad": 0,
                    "wrong_task_type": 0
                },
                {
                    "period": "2026-06",
                    "data_sensitivity_unaddressed": 0,
                    "insufficient_contributor_guidelines": 0,
                    "missing_acceptance_criteria": 0,
                    "scope too broad. multiproject. pii_regulated": 1,
                    "scope_too_broad": 0,
                    "wrong_task_type": 0
                }
            ]
        },
        "approval_volume_by_use_case": {
            "keys": [
                "Financial Services · Code Review",
                "Financial Services · Content Gen",
                "Financial Services · Conversational AI",
                "Financial Services · Data Labeling",
                "Financial Services · Doc Process",
                "Financial Services · Model Eval",
                "Government · Code Review",
                "Government · Content Gen",
                "Government · Conversational AI",
                "Government · Data Labeling",
                "Government · Doc Process",
                "Government · Model Eval",
                "Healthcare · Code Review",
                "Healthcare · Content Gen",
                "Healthcare · Conversational AI",
                "Healthcare · Data Labeling",
                "Healthcare · Doc Process",
                "Healthcare · Model Eval",
                "Legal · Code Review",
                "Legal · Content Gen",
                "Legal · Conversational AI",
                "Legal · Data Labeling",
                "Legal · Doc Process",
                "Legal · Model Eval",
                "Retail · Code Review",
                "Retail · Content Gen",
                "Retail · Conversational AI",
                "Retail · Data Labeling",
                "Retail · Doc Process",
                "Retail · Model Eval",
                "Technology · Code Review",
                "Technology · Content Gen",
                "Technology · Conversational AI",
                "Technology · Data Labeling",
                "Technology · Doc Process",
                "Technology · Model Eval"
            ],
            "data": [
                {
                    "period": "2025-12",
                    "Financial Services · Code Review": 0,
                    "Financial Services · Content Gen": 0,
                    "Financial Services · Conversational AI": 0,
                    "Financial Services · Data Labeling": 0,
                    "Financial Services · Doc Process": 0,
                    "Financial Services · Model Eval": 1,
                    "Government · Code Review": 0,
                    "Government · Content Gen": 2,
                    "Government · Conversational AI": 0,
                    "Government · Data Labeling": 0,
                    "Government · Doc Process": 0,
                    "Government · Model Eval": 1,
                    "Healthcare · Code Review": 2,
                    "Healthcare · Content Gen": 0,
                    "Healthcare · Conversational AI": 0,
                    "Healthcare · Data Labeling": 0,
                    "Healthcare · Doc Process": 1,
                    "Healthcare · Model Eval": 1,
                    "Legal · Code Review": 1,
                    "Legal · Content Gen": 0,
                    "Legal · Conversational AI": 0,
                    "Legal · Data Labeling": 0,
                    "Legal · Doc Process": 0,
                    "Legal · Model Eval": 1,
                    "Retail · Code Review": 0,
                    "Retail · Content Gen": 0,
                    "Retail · Conversational AI": 1,
                    "Retail · Data Labeling": 1,
                    "Retail · Doc Process": 0,
                    "Retail · Model Eval": 0,
                    "Technology · Code Review": 0,
                    "Technology · Content Gen": 1,
                    "Technology · Conversational AI": 0,
                    "Technology · Data Labeling": 0,
                    "Technology · Doc Process": 0,
                    "Technology · Model Eval": 0
                },
                {
                    "period": "2026-01",
                    "Financial Services · Code Review": 1,
                    "Financial Services · Content Gen": 0,
                    "Financial Services · Conversational AI": 2,
                    "Financial Services · Data Labeling": 1,
                    "Financial Services · Doc Process": 1,
                    "Financial Services · Model Eval": 1,
                    "Government · Code Review": 0,
                    "Government · Content Gen": 1,
                    "Government · Conversational AI": 1,
                    "Government · Data Labeling": 1,
                    "Government · Doc Process": 0,
                    "Government · Model Eval": 1,
                    "Healthcare · Code Review": 1,
                    "Healthcare · Content Gen": 1,
                    "Healthcare · Conversational AI": 0,
                    "Healthcare · Data Labeling": 0,
                    "Healthcare · Doc Process": 1,
                    "Healthcare · Model Eval": 0,
                    "Legal · Code Review": 2,
                    "Legal · Content Gen": 2,
                    "Legal · Conversational AI": 1,
                    "Legal · Data Labeling": 0,
                    "Legal · Doc Process": 2,
                    "Legal · Model Eval": 2,
                    "Retail · Code Review": 1,
                    "Retail · Content Gen": 2,
                    "Retail · Conversational AI": 1,
                    "Retail · Data Labeling": 1,
                    "Retail · Doc Process": 0,
                    "Retail · Model Eval": 2,
                    "Technology · Code Review": 0,
                    "Technology · Content Gen": 1,
                    "Technology · Conversational AI": 0,
                    "Technology · Data Labeling": 1,
                    "Technology · Doc Process": 2,
                    "Technology · Model Eval": 0
                },
                {
                    "period": "2026-02",
                    "Financial Services · Code Review": 1,
                    "Financial Services · Content Gen": 1,
                    "Financial Services · Conversational AI": 2,
                    "Financial Services · Data Labeling": 3,
                    "Financial Services · Doc Process": 1,
                    "Financial Services · Model Eval": 1,
                    "Government · Code Review": 0,
                    "Government · Content Gen": 5,
                    "Government · Conversational AI": 2,
                    "Government · Data Labeling": 1,
                    "Government · Doc Process": 3,
                    "Government · Model Eval": 3,
                    "Healthcare · Code Review": 1,
                    "Healthcare · Content Gen": 2,
                    "Healthcare · Conversational AI": 4,
                    "Healthcare · Data Labeling": 1,
                    "Healthcare · Doc Process": 1,
                    "Healthcare · Model Eval": 1,
                    "Legal · Code Review": 2,
                    "Legal · Content Gen": 1,
                    "Legal · Conversational AI": 3,
                    "Legal · Data Labeling": 1,
                    "Legal · Doc Process": 1,
                    "Legal · Model Eval": 1,
                    "Retail · Code Review": 2,
                    "Retail · Content Gen": 0,
                    "Retail · Conversational AI": 2,
                    "Retail · Data Labeling": 3,
                    "Retail · Doc Process": 4,
                    "Retail · Model Eval": 1,
                    "Technology · Code Review": 2,
                    "Technology · Content Gen": 4,
                    "Technology · Conversational AI": 2,
                    "Technology · Data Labeling": 0,
                    "Technology · Doc Process": 2,
                    "Technology · Model Eval": 1
                },
                {
                    "period": "2026-03",
                    "Financial Services · Code Review": 7,
                    "Financial Services · Content Gen": 2,
                    "Financial Services · Conversational AI": 1,
                    "Financial Services · Data Labeling": 2,
                    "Financial Services · Doc Process": 2,
                    "Financial Services · Model Eval": 2,
                    "Government · Code Review": 4,
                    "Government · Content Gen": 2,
                    "Government · Conversational AI": 4,
                    "Government · Data Labeling": 2,
                    "Government · Doc Process": 0,
                    "Government · Model Eval": 5,
                    "Healthcare · Code Review": 2,
                    "Healthcare · Content Gen": 4,
                    "Healthcare · Conversational AI": 4,
                    "Healthcare · Data Labeling": 3,
                    "Healthcare · Doc Process": 4,
                    "Healthcare · Model Eval": 1,
                    "Legal · Code Review": 2,
                    "Legal · Content Gen": 2,
                    "Legal · Conversational AI": 1,
                    "Legal · Data Labeling": 3,
                    "Legal · Doc Process": 2,
                    "Legal · Model Eval": 3,
                    "Retail · Code Review": 2,
                    "Retail · Content Gen": 3,
                    "Retail · Conversational AI": 1,
                    "Retail · Data Labeling": 1,
                    "Retail · Doc Process": 5,
                    "Retail · Model Eval": 2,
                    "Technology · Code Review": 1,
                    "Technology · Content Gen": 1,
                    "Technology · Conversational AI": 3,
                    "Technology · Data Labeling": 4,
                    "Technology · Doc Process": 4,
                    "Technology · Model Eval": 1
                },
                {
                    "period": "2026-04",
                    "Financial Services · Code Review": 0,
                    "Financial Services · Content Gen": 6,
                    "Financial Services · Conversational AI": 2,
                    "Financial Services · Data Labeling": 1,
                    "Financial Services · Doc Process": 1,
                    "Financial Services · Model Eval": 3,
                    "Government · Code Review": 3,
                    "Government · Content Gen": 0,
                    "Government · Conversational AI": 2,
                    "Government · Data Labeling": 4,
                    "Government · Doc Process": 5,
                    "Government · Model Eval": 3,
                    "Healthcare · Code Review": 0,
                    "Healthcare · Content Gen": 0,
                    "Healthcare · Conversational AI": 2,
                    "Healthcare · Data Labeling": 1,
                    "Healthcare · Doc Process": 2,
                    "Healthcare · Model Eval": 1,
                    "Legal · Code Review": 4,
                    "Legal · Content Gen": 0,
                    "Legal · Conversational AI": 4,
                    "Legal · Data Labeling": 1,
                    "Legal · Doc Process": 2,
                    "Legal · Model Eval": 0,
                    "Retail · Code Review": 4,
                    "Retail · Content Gen": 0,
                    "Retail · Conversational AI": 0,
                    "Retail · Data Labeling": 0,
                    "Retail · Doc Process": 4,
                    "Retail · Model Eval": 0,
                    "Technology · Code Review": 2,
                    "Technology · Content Gen": 2,
                    "Technology · Conversational AI": 2,
                    "Technology · Data Labeling": 1,
                    "Technology · Doc Process": 0,
                    "Technology · Model Eval": 0
                },
                {
                    "period": "2026-05",
                    "Financial Services · Code Review": 0,
                    "Financial Services · Content Gen": 0,
                    "Financial Services · Conversational AI": 0,
                    "Financial Services · Data Labeling": 0,
                    "Financial Services · Doc Process": 0,
                    "Financial Services · Model Eval": 0,
                    "Government · Code Review": 0,
                    "Government · Content Gen": 1,
                    "Government · Conversational AI": 0,
                    "Government · Data Labeling": 0,
                    "Government · Doc Process": 0,
                    "Government · Model Eval": 1,
                    "Healthcare · Code Review": 0,
                    "Healthcare · Content Gen": 0,
                    "Healthcare · Conversational AI": 2,
                    "Healthcare · Data Labeling": 0,
                    "Healthcare · Doc Process": 0,
                    "Healthcare · Model Eval": 0,
                    "Legal · Code Review": 0,
                    "Legal · Content Gen": 0,
                    "Legal · Conversational AI": 0,
                    "Legal · Data Labeling": 0,
                    "Legal · Doc Process": 1,
                    "Legal · Model Eval": 0,
                    "Retail · Code Review": 1,
                    "Retail · Content Gen": 1,
                    "Retail · Conversational AI": 0,
                    "Retail · Data Labeling": 0,
                    "Retail · Doc Process": 1,
                    "Retail · Model Eval": 1,
                    "Technology · Code Review": 0,
                    "Technology · Content Gen": 0,
                    "Technology · Conversational AI": 0,
                    "Technology · Data Labeling": 0,
                    "Technology · Doc Process": 0,
                    "Technology · Model Eval": 0
                },
                {
                    "period": "2026-06",
                    "Financial Services · Code Review": 0,
                    "Financial Services · Content Gen": 0,
                    "Financial Services · Conversational AI": 0,
                    "Financial Services · Data Labeling": 1,
                    "Financial Services · Doc Process": 0,
                    "Financial Services · Model Eval": 0,
                    "Government · Code Review": 0,
                    "Government · Content Gen": 0,
                    "Government · Conversational AI": 0,
                    "Government · Data Labeling": 0,
                    "Government · Doc Process": 0,
                    "Government · Model Eval": 0,
                    "Healthcare · Code Review": 0,
                    "Healthcare · Content Gen": 0,
                    "Healthcare · Conversational AI": 1,
                    "Healthcare · Data Labeling": 0,
                    "Healthcare · Doc Process": 0,
                    "Healthcare · Model Eval": 0,
                    "Legal · Code Review": 0,
                    "Legal · Content Gen": 0,
                    "Legal · Conversational AI": 0,
                    "Legal · Data Labeling": 0,
                    "Legal · Doc Process": 0,
                    "Legal · Model Eval": 0,
                    "Retail · Code Review": 0,
                    "Retail · Content Gen": 0,
                    "Retail · Conversational AI": 0,
                    "Retail · Data Labeling": 0,
                    "Retail · Doc Process": 0,
                    "Retail · Model Eval": 0,
                    "Technology · Code Review": 0,
                    "Technology · Content Gen": 0,
                    "Technology · Conversational AI": 0,
                    "Technology · Data Labeling": 0,
                    "Technology · Doc Process": 0,
                    "Technology · Model Eval": 0
                }
            ]
        }
    },
    "spec_to_opportunity": {
        "stages": [
            {
                "stage": "Discovery",
                "volume": 274
            },
            {
                "stage": "Proposal",
                "volume": 181
            },
            {
                "stage": "Negotiation",
                "volume": 130
            },
            {
                "stage": "Closed Won",
                "volume": 74
            },
            {
                "stage": "Closed Lost",
                "volume": 71
            }
        ],
        "velocity_days": [
            {
                "from": "Discovery",
                "to": "Proposal",
                "avg_days": 13.2
            },
            {
                "from": "Proposal",
                "to": "Negotiation",
                "avg_days": 15.2
            },
            {
                "from": "Negotiation",
                "to": "Closed",
                "avg_days": 13.9
            }
        ]
    },
    "opportunity_to_won": {
        "pipeline_value_and_volume_by_segment": {
            "Enterprise": {
                "deal_volume": 151,
                "pipeline_value": 52458000.0
            },
            "Mid-Market": {
                "deal_volume": 84,
                "pipeline_value": 8052097.56
            },
            "SMB": {
                "deal_volume": 41,
                "pipeline_value": 1641000.0
            }
        },
        "win_rate_by_win_type": {
            "new_logo": {
                "wins": 30,
                "win_rate": 0.207
            },
            "prior_loss_now_won": {
                "wins": 14,
                "win_rate": 0.097
            },
            "renewal": {
                "wins": 24,
                "win_rate": 0.166
            },
            "reactivation": {
                "wins": 6,
                "win_rate": 0.041
            }
        },
        "avg_deal_size_and_growth_by_segment": {
            "Enterprise": {
                "avg_acv": 367801.32,
                "growth": -0.011,
                "count": 151
            },
            "Mid-Market": {
                "avg_acv": 134426.83,
                "growth": -0.005,
                "count": 82
            },
            "SMB": {
                "avg_acv": 36731.71,
                "growth": 0.123,
                "count": 41
            }
        },
        "running_acv": [
            {
                "period": "2025-12",
                "acv": 165000.0,
                "running_acv": 165000.0
            },
            {
                "period": "2026-01",
                "acv": 3863000.0,
                "running_acv": 4028000.0
            },
            {
                "period": "2026-02",
                "acv": 11546000.0,
                "running_acv": 15574000.0
            },
            {
                "period": "2026-03",
                "acv": 19923000.0,
                "running_acv": 35497000.0
            },
            {
                "period": "2026-04",
                "acv": 21603000.0,
                "running_acv": 57100000.0
            },
            {
                "period": "2026-05",
                "acv": 10967000.0,
                "running_acv": 68067000.0
            },
            {
                "period": "2026-06",
                "acv": 0.0,
                "running_acv": 68067000.0
            }
        ],
        "revenue_per_win_type": {
            "by_type": {
                "new_logo": {
                    "avg_acv": 321733.33,
                    "count": 30
                },
                "prior_loss_now_won": {
                    "avg_acv": 330357.14,
                    "count": 14
                },
                "renewal": {
                    "avg_acv": 275041.67,
                    "count": 24
                },
                "reactivation": {
                    "avg_acv": 164666.67,
                    "count": 6
                }
            },
            "note": "Prior Loss · Now Won averages the highest ACV (~3% above New Logo)"
        }
    },
    "business_funnel": {
        "specs": 503,
        "opportunities": 276,
        "won": 74,
        "won_acv": 21866000.0,
        "open_pipeline": 36985097.56,
        "spec_to_opp_rate": 0.5487,
        "win_rate_all": 0.2681,
        "closed": 145,
        "prior": null
    },
    "pipeline_flow": {
        "transitions": [
            {
                "from": "Discovery",
                "to": "Proposal",
                "deals": 181,
                "amount": 55487000.0
            },
            {
                "from": "Discovery",
                "to": "Negotiation",
                "deals": 26,
                "amount": 7179000.0
            },
            {
                "from": "Discovery",
                "to": "Closed Lost",
                "deals": 11,
                "amount": 3269000.0
            },
            {
                "from": "Proposal",
                "to": "Negotiation",
                "deals": 104,
                "amount": 32588000.0
            },
            {
                "from": "Proposal",
                "to": "Closed Won",
                "deals": 14,
                "amount": 6390000.0
            },
            {
                "from": "Proposal",
                "to": "Closed Lost",
                "deals": 12,
                "amount": 2887000.0
            },
            {
                "from": "Negotiation",
                "to": "Closed Won",
                "deals": 60,
                "amount": 18776000.0
            },
            {
                "from": "Negotiation",
                "to": "Closed Lost",
                "deals": 48,
                "amount": 13034000.0
            }
        ],
        "open_now": [
            {
                "stage": "Discovery",
                "deals": 56,
                "amount": 15114000.0
            },
            {
                "stage": "Proposal",
                "deals": 51,
                "amount": 13622000.0
            },
            {
                "stage": "Negotiation",
                "deals": 22,
                "amount": 7957000.0
            }
        ]
    },
    "demand_intelligence": {
        "headline": {
            "gap_value": 34692000.0,
            "gap_specs": 126,
            "declined_value": 16365000.0,
            "declined_specs": 56,
            "top_domain": "Government"
        },
        "heatmap": [
            {
                "domain": "Government",
                "segment": "Enterprise",
                "value": 9077000.0,
                "specs": 21,
                "declined_specs": 2
            },
            {
                "domain": "Legal",
                "segment": "Enterprise",
                "value": 8669000.0,
                "specs": 20,
                "declined_specs": 3
            },
            {
                "domain": "Healthcare",
                "segment": "Enterprise",
                "value": 7138000.0,
                "specs": 16,
                "declined_specs": 4
            },
            {
                "domain": "Financial Services",
                "segment": "Enterprise",
                "value": 2838000.0,
                "specs": 7,
                "declined_specs": 3
            },
            {
                "domain": "Government",
                "segment": "Mid-Market",
                "value": 2782000.0,
                "specs": 18,
                "declined_specs": 1
            },
            {
                "domain": "Legal",
                "segment": "Mid-Market",
                "value": 1703000.0,
                "specs": 13,
                "declined_specs": 0
            },
            {
                "domain": "Healthcare",
                "segment": "Mid-Market",
                "value": 1479000.0,
                "specs": 12,
                "declined_specs": 3
            },
            {
                "domain": "Government",
                "segment": "SMB",
                "value": 834000.0,
                "specs": 16,
                "declined_specs": 2
            },
            {
                "domain": "Healthcare",
                "segment": "SMB",
                "value": 108000.0,
                "specs": 2,
                "declined_specs": 0
            },
            {
                "domain": "Financial Services",
                "segment": "SMB",
                "value": 64000.0,
                "specs": 1,
                "declined_specs": 0
            }
        ],
        "by_reason": [
            {
                "reason": "pii_regulated",
                "value": 22636000.0,
                "specs": 82
            },
            {
                "reason": "non_english",
                "value": 5823000.0,
                "specs": 22
            },
            {
                "reason": "nonstandard_platform",
                "value": 5713000.0,
                "specs": 23
            },
            {
                "reason": "new_modality_av",
                "value": 2643000.0,
                "specs": 10
            },
            {
                "reason": "extreme_complexity",
                "value": 1620000.0,
                "specs": 9
            }
        ],
        "by_domain": [
            {
                "domain": "Government",
                "gap_value": 12693000.0,
                "gap_specs": 55,
                "declined_value": 4618000.0,
                "declined_specs": 14
            },
            {
                "domain": "Legal",
                "gap_value": 10372000.0,
                "gap_specs": 33,
                "declined_value": 1469000.0,
                "declined_specs": 5
            },
            {
                "domain": "Healthcare",
                "gap_value": 8725000.0,
                "gap_specs": 30,
                "declined_value": 3793000.0,
                "declined_specs": 13
            },
            {
                "domain": "Financial Services",
                "gap_value": 2902000.0,
                "gap_specs": 8,
                "declined_value": 1517000.0,
                "declined_specs": 6
            },
            {
                "domain": "Technology",
                "gap_value": 0.0,
                "gap_specs": 0,
                "declined_value": 2872000.0,
                "declined_specs": 9
            },
            {
                "domain": "Retail",
                "gap_value": 0.0,
                "gap_specs": 0,
                "declined_value": 2096000.0,
                "declined_specs": 9
            }
        ]
    }
};

// ----------------------------------------------------------------------------
// Lookup keyed by request PATH. /spec, /review, /approve match exactly; the live
// GET /dashboard-data appends a query string (?date_from=…&cadence=…) and is
// matched by app.js on its BASE path (everything before "?").
// ----------------------------------------------------------------------------
window.STATIC_RESPONSES = {
  "/spec": SPEC_PAYLOAD,
  "/review": REVIEW_PAYLOAD,
  "/approve": APPROVE_PAYLOAD,
  "/dashboard-data": DASHBOARD_PAYLOAD,
};
