# Discovery Call — Brightshelf (Commerce / Retail-Tech) × Lorefi

**Date:** 2026-05-29
**Lorefi attendees:** Theo Nguyen (Account Executive), Priya Rao (Solutions)
**Customer attendees:** Casey Lund (Head of Product), Morgan Ellis (Lead ML Engineer)
**Recording ref:** rec_brightshelf_2026-05-29.m4a
**Transcript id:** txn_sample_04_ambiguous

---

**Theo (Lorefi):** Thanks for the time, Casey, Morgan. On the intro you said you've got an AI initiative that needs data help but you weren't quite sure how to frame the ask — let's figure it out together. Want to give us the shape of it?

**Casey (Brightshelf):** Sure. So Brightshelf is a software platform — we sell catalog-management software to online retailers. Think of us as a vertical SaaS company that lives inside the retail and e-commerce world. Our product has an assistant that helps a merchant turn a bare-bones product upload into a polished catalog listing — the title, the description, the category it belongs in, the attribute tags. Right now those generated listings are mediocre and inconsistent, and we want to make them better.

**Priya (Lorefi):** Got it. So is the core ask that you want our team to *write* a set of high-quality example listings — gold descriptions the model can learn from — or that you want us to *label and categorize* listings that already exist? Those are pretty different engagements on our side.

**Morgan (Brightshelf):** Honestly, that's the exact thing we've been going back and forth on internally, and I'd love your read. Part of what we want is people producing example content — given a product's raw attributes, write the ideal merchant-facing description, in a clean house style. That's the content-generation flavor. But the other part is, we already have millions of past listings our merchants uploaded, and we want those labeled — is the category right, are the attribute tags correct, does the description meet the style bar, tag the failure mode if not. That's more of a labeling and annotation job. We genuinely don't know which of those is the primary ask versus the supporting one.

**Casey (Brightshelf):** Right. Some days it feels like the real deliverable is the freshly authored gold descriptions and the labeling is just QA on top. Other days it feels like the categorization and tagging of our existing catalog is the main asset and the authored examples are just to fill gaps. We were hoping you'd help us decide.

**Priya (Lorefi):** That's a fair thing to be unsure about, and it's exactly what discovery is for. Let me ask some scoping questions and we'll see which way it leans. First — the data. What's the source material, and is there anything sensitive in it?

**Morgan (Brightshelf):** It's all product-catalog content — product titles, descriptions, category paths, attribute values like color, material, dimensions. It's merchandise data, not people data. No shopper information at all — no names, no addresses, no orders, no payment details. None of that ever comes near this project. All English, all US market. We'd hand you a normal catalog export and you'd work in your standard tooling; nothing on-prem, no special environment.

**Casey (Brightshelf):** Yeah, we're not a sensitive-data situation. It's product listings for things like home goods and apparel. The tricky part isn't compliance, it's that "a good listing" is genuinely subjective and our own merchandisers disagree.

**Priya (Lorefi):** Understood — so the hard part is the quality bar, not the data handling. On that: do you have a style guide or rubric today, and what would "good" look like when we're done?

**Morgan (Brightshelf):** We have a rough 4-page style guide. We'd want you to refine it with us. For success — I'd say if we can get to consistent agreement between reviewers on whether a listing is "publish-ready," plus a measurable lift in our model's listing quality, we'd be thrilled. We haven't pinned an exact number yet.

**Casey (Brightshelf):** And volume — we're not totally sure. We have a huge back-catalog we could pull from, and we could also commission new authored examples. We'd probably want to start with a pilot and see which flavor — authoring versus labeling — actually moves the needle, then scale that one.

**Theo (Lorefi):** That's helpful. So to play it back: one coherent project — improving the catalog-listing assistant — and within it two ways we could deliver, authoring gold listings or labeling your existing catalog, and you're genuinely open on which is primary.

**Morgan (Brightshelf):** Exactly. Same goal, same data, same team on our side. We just can't tell you today whether to file this under "content generation" or "data labeling," and we're also not sure if you'd call us a tech vendor or a retail company. We're kind of both.

**Priya (Lorefi):** That's useful for us to hear plainly, because it shapes how we staff and price it — the two flavors pull different expertise. Here's what we'll do: we'll write up an initial assessment that treats this as one project, name the domain and task-type call as the open question, and propose a pilot designed to resolve which flavor is primary before we scale. We'll be explicit that we're not yet certain how to classify it.

**Casey (Brightshelf):** That's perfect, honestly. Tell us what you think we are. Send it over and we'll react.

**Theo (Lorefi):** Will do. We'll get the assessment back to you this week.

---

**Lorefi notes (post-call):**
- ONE coherent project: improve Brightshelf's merchant-facing catalog-listing assistant.
- Domain is genuinely ambiguous: Brightshelf is a vertical-SaaS / retail-tech vendor — reads equally as **Technology** (software platform company) and **Retail** (commerce/merchandising). Confidence should be low.
- Task-type is genuinely ambiguous: customer wants both **producing example listings** (Content Gen) and **labeling/categorizing existing catalog items** (Data Labeling) and is openly unsure which is primary.
- No PII / no consumer data: product-catalog content only (titles, descriptions, categories, attributes) — no shopper names, addresses, orders, or payment data. English, US market. Standard export + standard tooling, no special platform.
- No policy escalation flags expected — every candidate cell (Technology/Retail × Content Gen/Data Labeling) is GREEN, and there is no regulated/personal data — so the ONLY review trigger is low classification confidence (agent uncertainty), not any escalation rule.
- Rough 4-page style guide to refine; quality bar (reviewer agreement + model lift) not yet quantified; volume not yet scoped — pilot first.
