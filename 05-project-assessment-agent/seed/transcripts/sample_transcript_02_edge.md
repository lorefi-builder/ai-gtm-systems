# Discovery Call — Cedarbrook Health Network (Healthcare) × Lorefi

**Date:** 2026-05-28
**Lorefi attendees:** Dana Okafor (Account Executive), Mara Lindqvist (Solutions)
**Customer attendees:** Dr. Naomi Feld (Chief Medical Information Officer), Owen Castellano (Director, Digital Health Products)
**Recording ref:** rec_cedarbrook_2026-05-28.m4a
**Transcript id:** txn_sample_02_edge

---

**Dana (Lorefi):** Thanks for the time, Dr. Feld, Owen. You mentioned on the intro call you've got an AI initiative that needs data help — want to walk us through it?

**Dr. Feld (Cedarbrook Health Network):** Yes. Cedarbrook runs a regional network of clinics and two hospitals. The big bet this year is a patient-facing assistant — a chatbot, basically — that patients talk to before a visit. It asks about symptoms, does a first-pass triage, and tells them whether to book a video visit, come in, or go to the ER. So it's conversational, multi-turn, and it has to handle people describing real medical problems in their own words.

**Mara (Lorefi):** Got it — so a conversational triage assistant, not a static FAQ bot. The model needs to hold a dialogue and reason about symptoms. What data are you planning to train and evaluate it on?

**Owen (Cedarbrook):** That's where we need you. We have years of real patient interactions we want to draw from — message-center threads between patients and our nurses, some transcribed nurse-line phone calls, and visit notes. We'd want your team to label the conversations: intent per turn, symptom mentions, urgency level, the works. And then evaluate the assistant's responses for safety and accuracy against what a clinician would say.

**Dr. Feld (Cedarbrook):** It has to be grounded in our actual patient population, which means the training material is genuine medical records. These are full PHI — patient names, dates of birth, the medical record numbers, the whole chart context in some of the notes. We operate under HIPAA, obviously, so anything touching this data is governed by our BAA process.

**Mara (Lorefi):** Understood, and that's an important flag for how we'd scope and staff this. Before we go further — when you say the conversations include patient names and DOBs and medical record numbers, is the plan to share that data as-is, or to de-identify before it reaches us?

**Owen (Cedarbrook):** Honestly, that's still being worked out internally. Ideally de-identified, but some of the clinical nuance lives in the identified notes, and our data science folks have been resistant to stripping it because they think it hurts the model. So assume for now that what you'd be labeling could contain real PHI.

**Dana (Lorefi):** That's good for us to know early — it changes the compliance and contributor side meaningfully. Let's come back to data handling. On the chatbot itself, what does success look like? How will you judge whether it's good enough to put in front of patients?

**Dr. Feld (Cedarbrook):** That's... a fair question, and I'll be honest that we haven't fully landed it. We know we don't want it to miss anything dangerous — under-triage is the nightmare. Beyond that it's a bit fuzzy. "Clinically appropriate, most of the time" is roughly where leadership is. We haven't set a hard number.

**Mara (Lorefi):** And volume — how many conversations are we talking about, and over what cadence?

**Owen (Cedarbrook):** Hard to say precisely. We have a lot — could be tens of thousands of threads, could be more once we pull the phone transcripts. We haven't scoped the exact pull yet. We'd want to start somewhere and see. I know that's vague.

**Mara (Lorefi):** That's okay — discovery is exactly where that vagueness is allowed to live. We'll note it as something we'd tighten before any commitment.

**Dr. Feld (Cedarbrook):** There's actually a second thing, while we have you, and it's pretty different from the chatbot. Our intake is still drowning in paper. When a new patient registers, they fill out these multi-page forms — history, insurance, consent — and a lot of it comes in as scanned PDFs and faxes. We want to pull the structured fields out of those scanned intake forms automatically: name, DOB, insurance member ID, medications listed, allergies. Right now a person keys it in by hand.

**Owen (Cedarbrook):** Right, that one's more of a document-extraction problem. Different team owns it, different timeline, but if Lorefi could help build the labeled dataset for the form-field extraction, that'd save us a lot of manual keying. It's separate from the triage assistant — we just figured we'd raise both since you're here.

**Mara (Lorefi):** Makes sense, and you're right that they're quite different efforts — one's a conversational model on clinical dialogue, the other's field extraction off scanned documents. We'd want to scope them separately so neither gets muddied. For today let's keep the triage assistant as the primary, and we'll note the intake-forms extraction as a distinct second track.

**Dana (Lorefi):** Exactly. And on the forms side, just flagging — those intake scans are also full of patient identifiers and insurance data, so the same HIPAA and PHI handling applies there too.

**Owen (Cedarbrook):** Understood. Both touch protected health information, no way around it.

**Dr. Feld (Cedarbrook):** On the assistant — one more constraint. Anything we do has to run inside our environment. Our security team won't allow patient data to leave our cloud tenant, so labeling and evaluation would need to happen in a walled-off setup we provision, not your standard tooling. I don't know all the technical details, but "it has to live in our environment" is a hard line from security.

**Mara (Lorefi):** That's a significant one and we'll take it seriously — a customer-provisioned, isolated environment is a different delivery model than our standard platform, and it affects tooling and timeline. I'd rather surface that now than discover it later.

**Dr. Feld (Cedarbrook):** I appreciate the candor. I'll be upfront that this is early for us — leadership wants the triage assistant this year, but the acceptance bar, the data pull, the de-identification question, all of that is unsettled.

**Dana (Lorefi):** That's genuinely useful context. Here's what we'll do: we'll write up an initial assessment for the triage assistant as the primary engagement, note the open questions on scope and success criteria, and capture the intake-forms extraction as a separate second track. We'll be clear-eyed about the compliance and environment constraints in there.

**Dr. Feld (Cedarbrook):** Perfect. Send it over and we'll react.

---

**Lorefi notes (post-call):**
- Primary: Cedarbrook patient-facing triage **chatbot** — Healthcare × Conversational AI. Multi-turn clinical dialogue, safety-critical (under-triage risk).
- Data is **real patient records** — PHI, names/DOBs, medical record numbers, under HIPAA/BAA. De-identification still undecided; assume identified data could reach us.
- Scope and success criteria are **vague** — no firm volume ("tens of thousands, maybe more"), no hard acceptance threshold ("clinically appropriate, most of the time").
- Delivery constraint: must run **inside customer's isolated cloud environment** — non-standard platform/tooling.
- **Second, distinct project raised:** structured field extraction from **scanned intake forms** (Healthcare × Doc Process) — different team/timeline, also PHI. Keep as a separate track.
