# Sales Playbook: Landing the First Three Brickline Pilots

*v1, 2026-11-15. This is a **plan**, not results: every rate, price and schedule here is a hypothesis until pilots confirm it. Labels as elsewhere: [V] verified, [E] estimate, [H] hypothesis. Pricing and tools come from `06-business-model.md`, `11-lead-generation-strategy.md` and `12-build-order-and-budget.md`; change them there first, then here.*

Who this is for: khaled, selling cold with no industry contacts. The goal of the first 30 days is **three contractors using Brickline for free or at pilot price, giving weekly feedback and outcome data**. Revenue comes after that.

## 1. Ideal first customers

The app's **Prospects** page (`/prospects`, data from `engine/leads/prospects.py`) lists every Chicago contractor doing 3–60 permitted jobs a year in porch, masonry, roofing, plumbing and electrical. Start with the slice most likely to say yes:

| Filter (fields on the Prospects page) | Why |
| --- | --- |
| **Violation-driven jobs > 0** | They already win work that starts with a city violation, so "who got cited this week" is a product they instantly understand |
| **5–40 jobs a year** | Busy enough to need steady work, small enough that the owner reads his own email and answers his own phone; above ~40 they often have sales staff |
| **Porch or masonry first** | Strongest validated signals (violation → permit lifts of 14× for porch and 8× for masonry in the backtests, see `HANDOFF.md` and `11` §3; the teaser shows the current rate); Chicago-specific demand |
| **Jobs flat or falling vs the prior 12 months** (the Trend arrow) | A contractor whose volume fell has the clearest reason to look for work. A rising one is a fine second-wave target |
| **Last job within ~90 days** | Still operating, so the email address and phone are likely alive |

The **Best fit only** toggle applies the first two rules. On the 2026-11-13 data that is 215 contractors across trades, 130 of them porch or masonry (105 masonry, 25 porch) [V, count from `web/data/prospects.json`]; it changes each refresh. Work masonry and porch in parallel, roofing/plumbing/electrical later: their violation-to-permit signals are weaker or less tested.

Sole proprietors (a person's name instead of a company name) are still fine to email at a business address; just never mix in home addresses or personal social accounts.

**Where contact details come from** (the list has none; nothing is guessed): the company's own website or Google Business Profile, the Illinois Secretary of State business search for the registered agent and entity name, and Apollo (`12` §3, ~$49/seat/month [V]) for email addresses. Record every source in the CRM (HubSpot free). If you can't find a business email or business phone in 10 minutes, skip the company and move on.

## 2. The pilot offer

> "Free first month of a weekly list of Chicago properties likely to need your trade, in your neighborhoods, with the evidence for each one and a drafted letter. In return: ten minutes of feedback a week, and you tell us which leads turned into jobs."

- **Month 1: free** in exchange for weekly feedback and outcome data (`06` §3.4 allows "free for the first month in exchange for weekly feedback and outcome data").
- **Months 2–3: pilot price, $250–$500 a month** (`06` §3.4). Keep the same weekly deliverable (`06`: 20–50 reviewed items a week, evidence, contact, drafted outreach).
- **After month 3: standard $750–$1,500 a month** depending on items per week and markets (`06` §3.4). `11` §6 uses a lower $300–$750 range [H] for early Track 1 customers; if pilots balk at $750, use that range for the first paying customers and write down why in `decision-log.md`.
- **Mail at cost-plus** for letters we print and send (`11` §6). No price beyond these ranges is promised until `06` is updated with delivery-hour data from the first three clients.
- Be explicit about what it is: a lead list with evidence and chance of work, not a guarantee of jobs. Show the Results page as the proof method (section 5).
- Run each pilot as its own client workspace in the app (Settings → trade, neighborhoods, business name, mailing address) so the weekly report and letters are theirs.

## 3. Cold-email sequence (3 touches: day 0, 4, 10)

Open the contractor's page under `/prospects`, check the numbers, copy the draft, fill in `[Your name]` and `[your mailing address]`, and send from your own mailbox on a separate sending domain (`12` §3). The page also prints as a one-page PDF teaser to attach on request.

**Rules for every email:** your real name and Brickline; the postal address; a one-line opt-out you honor immediately and record in the CRM; no "Re:" or "Fwd:" subjects; no fake familiarity; never name property owners (use counts, masked addresses and neighborhoods); say plainly that you found them in public permit records. Review each email by hand before sending: the drafts are drafts.

| Day | Content | Notes |
| --- | --- | --- |
| **0** | The teaser's draft: subject with their real counts (e.g. "N porch repair notices and M investor purchases in <areas>"), where you found them, counts for their neighborhoods, the historical rate from the snapshot, the free first month, "want the one-page summary?" | One ask: a yes/no reply |
| **4** | Short follow-up with a **new** fact, not "just checking in": one masked sample lead from their teaser (for example "28xx W Polk St, a porch violation issued Nov 13, historically ~X% turn into a permit"), then the same offer and the opt-out | Use the sample lead's chance of work from the teaser; do not quote a rate you didn't read off the page |
| **10** | Close-the-loop note: "I'll stop here. If lead flow isn't a problem right now, no worries. If it ever is, here is what I'd send." Offer to send the PDF; repeat opt-out and address | The last touch, always. Mark "no response" and do not email again for 90 days |

Pace: 15–20 new contractors a day maximum from a warmed-up sending domain, ~200 in the first 30 days (`11` §6 targets ~200 contacted, 20 conversations, 5 free pilots) [H].

## 4. Phone script (business lines, manual dialing only)

Call the business number listed for the company (website, Google profile, state registry) after the day-4 email, between 8:00 and 17:00 on weekdays. Dial by hand. **No autodialer, no prerecorded or AI voice, no texting.** If someone says "stop" or "don't call again", apologize, say yes, and record it in the CRM so it never happens again.

> "Hi, is this [Name]? This is [Your name] with Brickline here in Chicago. I'm not selling a lead-gen subscription over the phone. I emailed you a couple of days ago: I found your company in the city's permit records and built a weekly list of properties that just got porch or masonry violations in [neighborhood]. Do you have 30 seconds for me to tell you what's in it?"
>
> If yes: "There were [N] in [neighborhood] this week. Historically about [rate from the teaser] of owners in that position pull a permit within a year, and the ones who hear from a contractor first are usually the ones who get the job. I'm giving a few Chicago contractors the first month free if they tell me which leads were any good. Can I send you this week's one-pager, and could we talk for 15 minutes on [day]?"
>
> If no or busy: "Understood. Is there a better time, or should I take you off my list?"

Goal of the call: a yes to the one-pager or a 15-minute meeting, not a sale. Log every call outcome. Voicemail: name, company, one sentence, number, and "reply to my email or call back"; no more than one voicemail per contact.

## 5. Objections and honest answers

| Objection | Honest answer |
| --- | --- |
| "I already get leads from Angi / HomeAdvisor / Thumbtack." | "Those sell the same inquiry to several contractors. These aren't inquiries: they're properties with a city repair order or a recent complaint, and the owner hasn't hired anyone yet. Keep Angi; this is a second source, and you contact the owner first." Don't claim exclusivity of the data: the records are public, and other contractors can find them. Brickline's edge is that it's already collated, ranked and drafted |
| "I get enough work." | "Then you may not need it. Your permits show [jobs this year vs the year before from the teaser]. If you're full, say so and I'll check back next season." Don't push; pilot spots are limited by your own time anyway |
| "How do I know these convert?" | "Here are the historical rates from Chicago's own records, with the number of cases behind each (on the teaser and in each lead's detail page). They're floors, since permits miss unpermitted work. During the pilot you mark each lead won/lost, and the **Results** page replaces my averages with *your* measured close rate once you've decided 10 leads. If it isn't working for you, you'll see it in your own numbers." Never promise a close rate; the app's defaults (win rate, margin) are labeled assumptions |
| "I don't do computers / I don't read email." | "The weekly report prints on paper, and the letters print ready to sign and mail. I can walk you through it on the phone once." |
| "Is this legal? Are you the City?" | "Brickline is independent and not affiliated with the City. Everything comes from public records, and letters never imitate a City notice." |
| "What does it cost?" | State section 2: first month free; then the pilot price; then the standard range. No surprises, cancel any time (write the cancel terms into the pilot agreement) |
| "Send me something." | Send the printed teaser PDF and propose a time. Never send names of property owners before they are a client |

## 6. Weekly pilot operations (about 2–3 hours per pilot per week at the start) [E]

1. **Refresh the data:** `scripts/refresh-data.sh` (about 5 minutes, mostly downloads). Commit `web/data/snapshot.json` and `web/data/prospects.json`, republish. Until the scheduled refresh exists (HANDOFF next tasks), do this manually each Monday.
2. **Open the client's workspace** (switcher in the sidebar) and check Settings: trade, neighborhoods, business name, phone, mailing address.
3. **Review the weekly report** (`/report`): scan the act-now leads, drop anything that looks wrong, read the recommendations.
4. **Send it:** print the summary or export as PDF and send to the client; send the mail-merge CSV if they want to do the mailing; or print the letters (`/report?view=letters`) for the client to sign and mail.
5. **Mark outcomes:** every Monday ask the client which leads they contacted, which turned into meetings or jobs, and which were bad; set statuses (Contacted, Meeting booked, Won, Lost, Not relevant) and notes in the app.
6. **Review Results** (`/results`): measured close rate per signal and owner type, compared with the default assumptions.
7. **Ten-minute feedback call or message:** what was useful, what wasn't, what was missing. Write it in `decision-log.md` if it changes a decision.
8. **Track delivery hours** per pilot; `06` §3.4 needs real hours to replace estimates.

## 7. Metrics to track

Keep these in the CRM or a sheet, by week.

| Metric | Definition | Plan target [H] |
| --- | --- | --- |
| Emails sent / delivered / bounced | From the sending tool | Bounce rate low enough to protect the domain (pause above ~3%) |
| **Reply rate** | Replies of any kind / delivered | Learn first; adjust copy if under 3% after 100 sends |
| Positive replies and **meetings** | Asked for the teaser or booked a call | 20 conversations in 30 days (`11` §6) |
| **Pilots started** | Client workspace created, first report delivered | 3 in 30 days, 5 by day 60 (`11` §6) |
| **Conversion to paid** | Pilots that agree to the month 2–3 price / pilots started | Learn; the goal is a clear yes or no with a reason |
| **Close rate per signal** | Won / (won + lost) by lead kind, from `/results` | Replaces `snap.meta.assumptions` after 10 decided leads per owner type |
| Time to first contact | Days from lead signal to contractor outreach | Falling over time |
| Delivery hours per pilot per week | From your time log | Falls toward the 3–6 hours in `06` §3.4 |
| Opt-outs | Count, honored within one business day | Zero missed |

## 8. Compliance rules

These are operating rules for outreach, not legal advice. Have a lawyer review the templates and the pilot terms before scale (`12` §3 budgets $500–$1,500 for LLC formation and a basic legal review).

- **Email (CAN-SPAM):** true sender and subject (no "Re:", no misleading claims); your real postal address in every email; a clear opt-out that works for at least 30 days and is honored within 10 business days (we do it the same day); no purchased or harvested lists from places that forbid it; send from your own identity.
- **Phone (TCPA and Do-Not-Call):** manual dialing of **business lines** only. No autodialed, prerecorded or AI-voice calls and no texts to cell phones without prior express written consent. Check the National Do Not Call Registry for any number that might be personal. Call only 8:00–21:00 local time (we use 8:00–17:00). Keep an internal do-not-call list.
- **Individual homeowners:** mail only. Letters are signed by the contractor, give a real return address, and never imitate City correspondence. The weekly report letters follow this already.
- **Never imply City affiliation.** Not in subject lines, envelopes, letterhead or scripts. Say "public records" and name the source.
- **No owner names in prospecting material** (emails, teasers, social posts). Names appear only in client workspaces after the pilot starts.
- **Honesty:** every number comes from the snapshot (`models` and leads). Say "historical rate" and "floor"; never "guaranteed" or "exclusive". Label estimates as estimates.
- **Records:** log consent, opt-outs, and sources for each contact.

## 9. 30-day schedule to land three pilots

| Days | Do |
| --- | --- |
| **1–3** | Run `scripts/refresh-data.sh`; open `/prospects?fit=best` and pick the first 60 (porch and masonry). Create the sending domain, mailboxes and warm-up (`12` §3); set up HubSpot. Fill `[Your name]` and the postal address template. Read section 8 once more |
| **4–7** | Research contacts for the 60 (website, state registry, Apollo). Skip anyone without a business email or phone. Send the first 15 day-0 emails per day once warm-up allows |
| **8–14** | Day-0 emails continue to ~120 contacts total. Day-4 touches go out for the earliest batch. Start phone calls to business lines on day 4 after each email. Book meetings; prepare each meeting by opening the contractor's teaser |
| **15–21** | Day-10 touches for the first batch. Run 15-minute meetings: show the contractor's own teaser, then the real lead list for their neighborhoods in the app. Offer the pilot. Create the workspaces for the first yes answers and deliver the first weekly report within 48 hours of the yes |
| **22–28** | Second wave of 60 prospects (continue best-fit list). First weekly operations cycle for pilots (section 6): reports, letters, outcome marking. Collect feedback; fix wording or data issues found |
| **29–30** | Review metrics (section 7): reply rate, meetings, pilots started. Write down what worked in `decision-log.md`. Decide: double down on the winning trade and subject line, or change the offer. If fewer than three pilots started, interview the "no" replies for the real reason before changing anything |

**Fallbacks if replies are low:** shorten the email and put the counts in the subject; try the phone first for companies with no email; offer a free sample list for one neighborhood (a "free 2-week trigger list for your area", as in `11` §6) before asking for a pilot; test a small batch of our own direct mail to contractor business addresses (`12` §3 budgets ~$300–$600 for letters).
