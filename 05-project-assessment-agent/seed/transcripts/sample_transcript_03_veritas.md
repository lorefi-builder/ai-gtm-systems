# Discovery Call — Veritas Analytics (Financial Services) × Snorkel

**Date:** 2026-02-26 → 2026-03-16 (two calls, combined)
**Snorkel attendees:** Sarah Chen (Account Development Rep), Marcus Webb (Head of Pre-Sales), Priya Kapoor (Senior Strategy & Ops Manager), Daniel Torres (Senior Forward Deployed Engineer), Amit Patel (AI Solutions Engineer)
**Customer attendees:** Erik Lindgren (Member of Technical Staff), Rachel Kim (Applied Research Lead)
**Recording ref:** rec_veritas_combined_2026-02-26_2026-03-16.zoom
**Transcript id:** txn_veritas_combined

---

VERITAS ANALYTICS — DISCOVERY CALL TRANSCRIPTS
Prospect: Veritas Analytics (Finance / Legal AI Platform)
Source: anonymized sample discovery transcript (both calls), combined for ingestion.

================================================================
CALL 1: Initial Discovery
Recorded February 26, 2026 via Zoom | 30 minutes

Snorkel Team:
- Sarah Chen, Account Development Representative
- Marcus Webb, Head of Pre-Sales
- Priya Kapoor, Senior Strategy & Operations Manager
- Daniel Torres, Senior Forward Deployed Engineer

Veritas Analytics:
- Erik Lindgren, Member of Technical Staff
- Rachel Kim, Applied Research Lead
================================================================

0:00 | Sarah: Hey, hello? Hi, Erik. Hi, Rachel.
0:06 | Erik: How's it going?
0:08 | Sarah: Good. Thank you. How are you?
0:11 | Rachel: Doing good.
0:16 | Sarah: Just checking if we have everyone on the call. Yeah, cool. Thank you both for making the time. Great to meet you. If it's okay with you, it would be great to start with some brief introductions on both sides. I'm Sarah, I'm part of the sales team, based out of London, although I work mostly US hours. I've been here for the past year and a half. Marcus, go ahead.
1:16 | Marcus: Yeah, hey. Marcus Webb, I'm head of pre-sales. Been with the company about two years now.
1:25 | Daniel: Hi, I'm Daniel Torres, one of the senior post-sales forward deployed engineers. Been here since September, so about six months.
1:40 | Rachel: Cool. I can start. My name is Rachel. I'm on the applied research team, mostly working on evals and also developing our document understanding and reasoning capabilities.
2:02 | Erik: Yeah, Erik, also on the research team. We're working a lot with retrieval as one of our primary concerns. Just, you know, accuracy, how can we get datasets of like financial documents that are... I guess I'd rather if you guys led with the data front, but, yeah.
2:33 | Sarah: Thank you. Priya, do you want to do a quick intro?
2:40 | Priya: Yeah, sorry guys, technical issues. I'm Priya, I've been here almost a year and I lead up our data series work. We make investments on what we think will be the next quarter's hot thing in a couple different spaces and we develop that data with partners across frontier labs and niche industry AI vendors, along with our research partners. Then we distribute it non-exclusively, which is the only way it really works with the level of investment we put in.
3:48 | Sarah: So yeah, before we jump right into it, maybe I'll share a little context. We're a data research lab. We build high-quality expert-authored datasets, both off-the-shelf and custom, to train and evaluate advanced AI systems. We work with most of the frontier labs and a lot of vertical AI platforms across high-stakes domains like finance, legal, healthcare, software engineering, and STEM. I initially reached out about our financial analytics benchmark—a commercial-grade dataset with 700 plus tasks built to stress-test financial workflows. It spans analytical reporting, structured financial records analysis, cross-entity performance analysis, and asset price evaluation. Was there anything that specifically resonated?
5:38 | Erik: Sure. We're interested in financial datasets broadly speaking. As I understand it, your dataset is very similar to a terminal bench setup where there's a task and a reward specification. What we're looking for today is a little bit different. We're looking for more granular, clearly labeled task instructions. We're less concerned with end-to-end automation as much as actually going into the details—like, hey, do these documents match, or is this a good answer given this source. Does that make sense?
6:40 | Marcus: Erik, so maybe just to say it back—I actually spent like 20 years at a major bank in credit. Would a task be like, you've got balance sheet and income statements and you're trying to do some kind of cash flow analysis? Or if you get new financials you want to see does previous quarters match what was reported? Like you want to reconcile footnotes and modifications?
7:21 | Erik: Part of it is that, but there's also this implicit fetching the documents we care about—the retrieval side. I'm biased because that's mostly what I've been focusing on. But there's definitely value in ad hoc extraction tasks in isolation given this data. But the more holistic aggregating—information retrieval—I think that's what we'd be most interested in.
8:03 | Marcus: Okay. So it's a bit more of like you need an environment where all these documents exist. Part of the task is the retrieval element. Part is extracting the data, doing analysis, coming up with the final answer. So there's some retrieval, some tool calls, calculations. More of an end-to-end workflow than just a pure extraction problem?
8:29 | Erik: Yeah. And the environment thing—do you guys offer environments to train reinforcement learning, or is this like actual data?
8:47 | Marcus: Yeah, we offer both. The dataset Sarah shared is kind of that terminal bench setup where there's files and things the agent has to find but it's not really a full ecosystem with databases and policies and document stores. We also partner with labs on building custom environments. Most have been set up around enterprise workflows, a little more generic than what you're looking at. But it's definitely a place where we've done a lot of partnering.
9:29 | Erik: I think our bias is more towards the pure data as opposed to environment stuff, given where our product is at. So what do you have along those lines?
9:49 | Marcus: When you say the data, is that like the raw data, the actual documents?
9:57 | Erik: If I had to summarize, the categories of data we're most interested in: the documents themselves, the things people are asking over these documents, and how they interact. We have some SEC filings, some queries, some outputs from an agent. But the key thing—if I could highlight one thing that's most important—it would be retrieval.
10:39 | Marcus: Makes sense. Is it something where the data that would be helpful is you've already got documents and need to know for a given query, are the right documents being retrieved? Or are you looking for us to provide those documents as well as traces?
11:15 | Erik: I think we could be open to either. I'd have to talk with someone else internally about specifics. Rachel, thoughts?
11:28 | Rachel: Yeah, in general, having the documents—one thing we were discussing is the distinction between having a query and a document to answer over, versus finding the correct document among many. We're interested in finding the correct document given a bunch of documents. So how do we source that set of candidate documents? We need the correct document but also hard negatives that make this actually hard. We could throw together a huge set but the question is whether we'd have relevant documents that create a challenging problem.
12:31 | Marcus: Makes sense. So you guys have kind of documents, and we would want to work with that population, draft questions, test retrieval, and validate against the whole population to say if it retrieved the correct ones or not.
13:00 | Rachel: That's one way. Another thing—if we use public financial documents, you wouldn't need to provide them. But yeah, in general, that's what we're thinking.
13:12 | Marcus: If we're dealing with public documents like SEC filings, I think we would set up an environment with all those documents, run tasks within that environment, and have experts review the output for a given query and create the reward signal.
13:31 | Rachel: Great. Yeah, that seems pretty aligned. Erik, what do you think?
13:35 | Erik: Yeah, that makes sense.
13:40 | Erik: I think the main thing—to get out in front of it—we were curious about a very rough ballpark estimate of pricing. We're piloting with a couple other adjacent data provider companies for similar services. We're very interested, but we just want to understand how you guys think about pricing.
14:11 | Marcus: Yeah, and I'll start with the non-answer: it depends. If you guys have an API we can hit with documents and we're just testing, then it's more of an annotation task where we're paying per task. There's however long it takes to write the query, do the research, translate that into an hourly rate for a finance expert. Ballpark, it comes down to how much data you need annotated. On the other end, if we need to build a full realistic environment with thousands of documents, sourcing, accounting systems, tools, policies—a simple environment would start around 250K, a complex one at least a million. That includes the environment plus annotated tasks. For the per-task model, if it takes an hour per task and we pay people 100 bucks an hour, then it's just cost times volume. Could be under 100K, under 50K, depending on volume.
16:08 | Erik: Gotcha. That makes sense.
16:11 | Sarah: Have you had a chance to review the samples I sent over?
16:19 | Erik: I've looked at them, not in depth. I saw the general format and structure. I understand it's more environment and task oriented.
17:07 | Erik: I guess to wrap up, it would be great to get some rough ballpark numbers. Our top interests are information retrieval datasets specifically for finance, tough document distributions. I can send a follow-up with specifics. Generally it's financial question answering and information retrieval. We have documents. Are they real? Can you find them? Do they answer the question? Is the question answered correctly? The question may require multiple documents. That's what we're interested in. And from you guys, a rough breakdown of how you think about pricing.
18:36 | Marcus: Yeah. We can definitely do that.
18:38 | Priya: I think we can definitely put that together. We work with different customers at different complexity and price sensitivities, so it's certainly not a blocker. Daniel, any thoughts on the document retrieval side?
19:22 | Daniel: My question after hearing all that is—what kind of final answers are you looking at? Is it more than just numeric answers? Is there semantic checking in addition to numerical validation?
19:43 | Erik: I'll give the non-answer: basically anything you would expect a model could respond to a query with should be represented.
20:04 | Rachel: I'd say extractive queries are valuable but not as valuable as reasoning on top of extracted information. A lot of the queries we're getting from customers are more complex—analyze things in the lens of some computation. Numerical verifiable questions are interesting to a degree, but more semantic and reasoning is the most valuable for us.
21:23 | Marcus: So if I understand—you maybe have a solution or dataset on the answer generation side, or at least that's not your focus. You're really looking for a dataset on that first step, the retrieval side. Am I understanding correctly?
22:02 | Rachel: In a way. We probably have the most data on extraction right now. So retrieval is really valuable. Even synthesis after extraction is valuable. That said, we're always in the market for data for all three. But extraction alone isn't as valuable because it's a sub-step—a user would say find this information then reason over it. Extraction is a primitive we have to solve, but it's not the most valuable data.
22:50 | Marcus: That makes sense. You have to have the right context and documents to even have a chance at the right answer. And I suspect if you have the right documents, you're probably very accurate on the final answer. If you don't, it's not accurate. That tracks with our experience building RAG systems in enterprise.
23:37 | Priya: More tactically—for a single retrieval task, is there a set amount of documents that would make it interesting? Is it 10, 50, 100 in the candidate pool?
24:13 | Erik: I'd put the number in the hundreds is where it starts to become interesting.
24:21 | Priya: And is it single-shot or are you interested in multi-turn as well?
24:44 | Erik: Start with single-turn for now. Definitely interested in multi-turn, but we should walk before we run.
25:00 | Marcus: Just to make sure we have a good follow-up—what would be most interesting is if we came back with a point of view on how we'd build that dataset. The samples we shared aren't retrieval problems over documents. It's an example of work we've done but not your use case. We don't have that off the shelf but we'd be interested in developing a specification.
25:47 | Rachel: Definitely interested in seeing that back. Erik and I would have to go to the upper levels for anything money-related, but yeah.
26:11 | Marcus: Can you give us a sense of volume? How much data, how many queries?
26:34 | Erik: Gun to my head—tens of thousands of documents would be ideal. But there's value in the intermediary. A million would also be great. Very tough to say. A lot depends on pricing and the complexity of the tasks you source.
27:24 | Marcus: Also, there's a lot of initial setup work. If we show you something with five candidate documents and it retrieves the right one, you won't be impressed. So it's a lot of setup to get a repository of thousands. We'll need to discuss internally.
28:01 | Sarah: Should we aim to put something together and check in second week of March?
28:30 | Erik: Sure, works for me. We're pretty flexible on calendars.
29:33 | Sarah: I'll propose the eleventh. If there are changes, we'll touch base offline. Thank you, great to meet you.
29:52 | Marcus: Nice to meet you guys.
29:55 | Erik: Thanks, bye.

================================================================
CALL 2: Spec Review & Scoping
Recorded March 16, 2026 via Zoom | 39 minutes

Snorkel Team:
- Sarah Chen, Account Development Representative
- Marcus Webb, Head of Pre-Sales
- Amit Patel, AI Solutions Engineer

Veritas Analytics:
- Erik Lindgren, Member of Technical Staff
- Rachel Kim, Applied Research Lead
================================================================

0:00 | Sarah: Hey, Sarah. Hey, Marcus. How are you?
0:03 | Erik: Doing well. Hello. How's it going?
0:07 | Marcus: Hey, doing well. How are you, Erik?
0:10 | Erik: All right. Happy Monday.
2:28 | Sarah: Cool. Thank you for making time. You mentioned last week, Rachel, that you'd had some internal conversations. Before we dive into the spec walkthrough, any questions or things you'd like to discuss?
3:12 | Rachel: Yeah, overall the spec looked good. We talked to our manager and he seemed on board with what you'd provide. We do have some questions, but I think they'll naturally come up as we go through the spec.
4:45 | Marcus: The way I like to focus on a spec—first thing is task components. What is the expert going to do? What are all the data points we're going to deliver? Any feedback on the overall task design? It's pretty straightforward given the retrieval focus, but did you have questions on what we'd call a task here?
5:42 | Erik: The schema and definition all makes sense and seems pretty aligned. My biggest questions are around how you're making them, where you're sourcing them, where the labels are coming from. But directionally correct.
6:06 | Marcus: On sourcing—do you mean the corpus or the individual documents for a task?
6:12 | Erik: Both.
6:14 | Marcus: The corpus was one of the biggest things to clear up. Last call you mentioned you could provide documents. Is that the direction you want to go, since it's what you're already working with?
6:44 | Rachel: For public stuff—SEC filings, anything publicly available—that shouldn't be a problem. But we probably couldn't go past that. We'd probably want some coverage on private-related documents. Erik, thoughts?
7:19 | Erik: There's generally going to be more value in things we don't already have—things that aren't public. But the complexity of sourcing private documents, the cost, the quality control—my instinct is that it would approach the value and cost of just starting with labeling public.
8:00 | Marcus: Yeah, that's my gut too. I'm not confident we'd be able to source non-public documents. But to your point about value being the relationship between questions and docs—we can build a lot of that off public documents. If we do focus on public, we could have annotators use EDGAR as a tool to find documents and annotate with their identifiers. Would that work?
12:24 | Erik: Yeah, that's pretty straightforward. Rachel, any strong opinion on if we should give a list of identifiers or if there's value in exploratory work?
12:41 | Rachel: I think it should be relatively easy to map everything. Our data sourcing for public is pretty extensive. It's worth maybe a quick internal sync about diversity direction or specific types of companies we'd care most about.
13:18 | Erik: I imagine there's probably some intuitive stuff—recent major market-moving acquisitions, interesting events.
13:33 | Marcus: If there are certain companies you want us to target, we can take that as input. Directionally—working with public documents, accessing through EDGAR, providing keyed off of EDGAR IDs—that works for you?
13:58 | Erik: Whatever format works is going to be easy enough to map. I'd defer—whatever you guys can set up most easily.
14:12 | Marcus: Cool. Next question. You mentioned reasoning being more valuable—requiring multiple parts of a document, multiple documents. Do you have any interest in extraction at all? The level of expert we need for extraction is more generalist versus reasoning which requires finance knowledge. Pricing would be different. What's the balance you're looking for?
15:15 | Rachel: There is value in extraction but on a more systematic level. Like, extract these 10-15 metrics from these documents for these four companies. Each document can have a different company and we want the same properties extracted across different documents. That type of query is interesting. But in general, more value in reasoning—that expert opinion is where the value comes from.
16:04 | Erik: Basically exactly what I was going to say. If I had to pick one, definitely reasoning. A blended world could make sense, but reasoning moves the needle more.
16:25 | Marcus: And Rachel, I like the way you framed extraction—it's more like multiple companies, multiple time periods. More interesting than one fact from one document.
16:54 | Rachel: Yeah, singular extraction is something our system does pretty well already. The more comprehensive extraction tests are more interesting.
17:07 | Marcus: On complexity—I assume you want to weight toward more complex tasks?
17:27 | Rachel: Even tier two would still be interesting, but definitely weight toward tier three.
17:36 | Marcus: And on hard negatives. Last call we talked about documents that look similar—same type of filing, similar company, same time period but different company. AMD versus Intel, for example. Is that how we should think about it? And how many hard negatives per task?
18:29 | Erik: Number of hard negatives—roughly less than or up to the same as the number of positives. In terms of the nuance—companies are similar but different, the number is similar but wrong, the semantic definition is similar but technically different. That's probably the most fundamental failure mode I've seen.
20:46 | Marcus: Makes sense.
20:48 | Erik: I can give you more along those lines as a follow-up.
21:06 | Marcus: On quality measurements—obviously the question should be right, right documents retrieved. But we want to avoid sending data we think looks good and you don't. The QA is probably more on the types of questions people write. Any general thoughts on quality, or examples of good questions?
22:25 | Erik: I'm about to do an analysis over the last quarter of the questions our users are asking. Obviously can't share direct source data, but I can probably summarize it—what analysts are actually asking and caring about.
23:11 | Marcus: If you had those clusters and we could try to hit distributions that match what you're seeing from users—that prevents us from sending questions and you saying this isn't what people are actually asking.
23:34 | Erik: I'd also posit that things not always being asked don't necessarily represent where things are going. Sometimes people don't ask things because we're not good at it yet. Expert opinion of what makes sense—what I wish our system could do—I'd almost defer to that over current usage patterns.
25:00 | Marcus: Last thing—volume. The next step is usually producing samples so you can see what the data looks like. The spec is 'here's what we'll produce,' the samples are proof we can actually produce it. Can you give us a sense of target volumes, ramp plans? We have to go request resources to work on this and need to make a case for it.
26:16 | Erik: Kind of depends on pricing more than anything.
27:48 | Sarah: Basically how we price—it's the average handling time for the workflow times the expertise tier. A generalist costs much less than a finance expert. It depends on task complexity and expertise tier.
28:08 | Erik: To give a ballpark frame of reference—we were imagining spends between the high tens to mid hundreds of thousands of dollars on data. We could land anywhere in that range. The more the better, the higher quality the better. But it all depends on the marginal rate.
33:16 | Marcus: Quick question on the spec—do you guys need just the document that the answer came from, or do you want passage-level? Like this section or paragraph?
33:35 | Erik: Passage would definitely be helpful. Does that significantly change pricing?
33:49 | Marcus: If you've already found the passage to answer the question, recording it shouldn't significantly increase the handling time. The cognitive load's already there, it's more of a data capture thing.
34:18 | Erik: Yeah, we'd probably want that.
34:32 | Rachel: Yeah, I think so too.
37:02 | Amit: Hi guys. Quick question—would you want ordering of passages by relevance, or is it binary?
37:56 | Rachel: My initial reaction is no. They should all be what's needed to answer the question. Any ranking—it should almost be binary.
38:15 | Erik: Same. I prefer the straightforward simple binary approach.
38:29 | Sarah: Should we look to schedule our next conversation a week from today?
38:46 | Erik: Yeah, roughly then should work.
38:57 | Sarah: Cool. If there are changes, let me know. Thank you and speak next week.
39:13 | Marcus: Thanks, guys. Bye.
