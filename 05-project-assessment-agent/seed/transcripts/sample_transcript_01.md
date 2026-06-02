# Discovery Call — Meridian Synth (Technology) × Lorefi

**Date:** 2026-05-21
**Lorefi attendees:** Dana Okafor (Account Executive), Sam Petrov (Solutions)
**Customer attendees:** Riley Vance (VP, ML Platform), Jordan Kim (Staff ML Engineer)
**Recording ref:** rec_meridian_2026-05-21.m4a
**Transcript id:** txn_sample_01

---

**Dana (Lorefi):** Thanks for making the time, Riley. To set the stage — you reached out about labeling support for an intent classification model. Want to give us the shape of it?

**Riley (Meridian Synth):** Sure. So Meridian Synth builds developer tooling — we have an in-product assistant that routes user questions to the right help flow. Right now the router model is mediocre because our training labels are a mess. We need a clean, consistently labeled dataset of user messages mapped to intent categories.

**Sam (Lorefi):** Got it. When you say messages — what's the source and the language mix?

**Jordan (Meridian Synth):** They're support-chat and in-product messages, all English. US and a bit of UK/Australia, but English throughout. No other languages in scope.

**Sam (Lorefi):** Good. And is there anything sensitive in those messages — personal data, payment info, anything regulated?

**Jordan (Meridian Synth):** We scrub them before they'd ever come to you. The export we'd hand over is already PII-stripped — emails, names, tokens all redacted by our pipeline. So what you'd see is just the message text and a row id.

**Dana (Lorefi):** That's helpful, makes the data-handling side simple. Riley, what does the label space look like?

**Riley (Meridian Synth):** We've got a taxonomy of 14 intents — things like "billing question," "bug report," "how-to," "feature request," "account access," and so on. It's flat, no nested hierarchy. We have a draft labeling guide, maybe 6 pages, that we'd want you to refine with us.

**Sam (Lorefi):** Fourteen flat classes with a guide already drafted — that's very much in our wheelhouse. What volume are we talking, and what's the cadence?

**Jordan (Meridian Synth):** Initial batch is 40,000 messages. If quality is good we'd move to a steady 10,000 a week after that. We'd want a held-out gold set too, so we can measure model lift.

**Sam (Lorefi):** We'd build a gold set with adjudication, yes. What's your accuracy bar?

**Riley (Meridian Synth):** We'd want inter-annotator agreement above 0.85 Cohen's kappa on the gold set, and per-class F1 reported so we can see where the taxonomy is weak. If a class is ambiguous we'd rather you flag it than guess.

**Dana (Lorefi):** That flag-don't-guess instinct is exactly how we like to run. On delivery — where would the labels live? Any platform constraints, on-prem requirements, anything unusual?

**Jordan (Meridian Synth):** Nothing exotic. We'd hand you a CSV/JSONL export, you label in your standard tooling, and deliver back JSONL. We ingest it into our normal training pipeline. No on-prem, no special platform.

**Riley (Meridian Synth):** Timeline matters though. We have a model refresh targeted for end of Q3, so we'd want the first 40k batch turned around in about three weeks from kickoff.

**Sam (Lorefi):** Three weeks for 40k with a gold set and a kappa target is aggressive but doable with the right contributor pool. We'd staff expert contributors who know developer-support language, a delivery manager to run the cadence, and light data-ops for the ingest/export loop.

**Riley (Meridian Synth):** What about the success criteria on your side — how do we know it's working before we scale to the weekly cadence?

**Sam (Lorefi):** We'd define acceptance up front: kappa ≥ 0.85 on the gold set, per-class F1 reported, and a calibration round on the first 2,000 where we reconcile the guide with you before going to full volume. If we hit those, we open the weekly tap.

**Riley (Meridian Synth):** That all sounds right. No surprises — English text, scrubbed data, flat taxonomy, standard delivery. Let's get a proposal together.

**Dana (Lorefi):** Perfect. We'll write up the spec and resourcing and get it back to you this week.

---

**Lorefi notes (post-call):**
- Domain: Technology. Task type: Data Labeling (text intent classification).
- Clean single project. English-only, PII pre-scrubbed by customer, standard tooling/delivery.
- 14 flat intents, 6-page draft guide to refine. 40k initial batch, then 10k/week.
- Quality bar: Cohen's kappa ≥ 0.85 on gold set, per-class F1, calibration round on first 2k.
- No escalation flags expected. Maps to a green cell (Technology × Data Labeling).
- Timeline: first batch ~3 weeks from kickoff; aligns to customer's Q3 model refresh.
