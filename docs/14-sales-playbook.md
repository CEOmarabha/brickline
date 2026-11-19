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

**Where contact details come from** (nothing is guessed): first the free suggestions on each contractor's page (section 5c: Overture Maps, Chicago business licenses and owner records, the company's own website), then the company's own website or Google Business Profile and the Illinois Secretary of State business search for the registered agent and entity name. Apollo (`12` §3, ~$49/seat/month [V]) is deferred: buy it only if the free match rates prove too low for the weekly list. Record every source in the CRM (HubSpot free). If you can't find a business email or business phone in 10 minutes, skip the company and move on.

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

## 5b. Tracking outreach in the app (the pipeline)

`/prospects` doubles as a CRM-lite, private to the signed-in founder (never visible in a client workspace). Each contractor has a status (Not contacted → Emailed → Replied → Meeting → Pilot → Paying, or Not interested), contact fields you enter by hand (name, business email, phone, website), notes, and a history. The counts across the top of the page are your pipeline; click one to filter, or click **Due today / overdue** for the follow-ups to do now.

- **Weekly routine, Monday:** open **Due today / overdue** first and send those touches (day-4 and day-10 emails, calls to business lines). Then pick new best-fit prospects (`/prospects?fit=best&status=not_contacted`), research contacts (10-minute cap), and send the day-0 emails.
- On a contractor's page press **I sent email 1/2/3** right after sending. It sets the status to Emailed and the next follow-up: 4 days after email 1, 6 days after email 2 (day 10), none after email 3 (then wait 90 days, section 3). Change the status by hand when they reply, book a meeting, start a pilot or opt out; marking **Not interested** clears the follow-up. Record every opt-out here the same day.
- Record where each contact came from in the notes (section 8, "Records").
- **Export pipeline** (button on `/prospects`, or `/export/prospects`) downloads a CSV for your own records or a mail tool; it contains contact details, so keep it private.
- Section 7 metrics: emails sent, replies, meetings and pilots can be read straight from the status counts and history; bounce rates still come from the sending tool.

## 5c. Free contact enrichment (suggestions, not facts)

Each refresh (`scripts/refresh-data.sh`, step `engine.enrich.contacts`) matches prospects and the company owners and buyers on leads to free public sources and writes `web/data/contacts.json`:

- **Overture Maps Places** (open data): website, phone, sometimes a business email and address, matched by normalized company name, with a trade-compatible category required for contractors.
- **Chicago business licenses and business owners** (City data portal): a business address and an owner or officer name with title (preferring owner, sole proprietor, president, CEO, managing member, manager, member), matched by legal name or DBA.
- **The company's own website**: the homepage and at most two contact pages, fetched only for matched websites, honoring robots.txt, one request a second, cached 30 days. Emails and US phone numbers only.

**How to use it:** open `/prospects/<id>` and look for **Suggested from public sources** in the Pipeline card; each value shows its source (with a link when there is one), the date and the match strength (high = exact name plus trade-compatible category in Chicago; medium = same name outside the city, a missing category or a near-identical spelling). Press **Use these** to copy a value into the form, then **Save**; the button stays disabled when the field already holds something, and nothing is ever saved or overwritten for you. On `/prospects` the **Contact info** column shows which kinds of suggestion exist and **Has contact info** filters to them. Company owners and buyers show the same card on `/leads/<id>`.

**Verify before outreach:** open the website, confirm the company does this trade and works in Chicago, and make sure the name is not a different business that shares it. A name from the owner records is a *suggestion of who to address*, not a promise that the person still runs the company. Note the source in the pipeline notes (section 8, "Records").

**Compliance** (adds to section 8): business contacts only. Never pattern-guess an email, never collect personal social profiles, and never put a name from a public record into cold emails or teasers beyond what the person's own business listing supports. Email follows CAN-SPAM (real postal address, working opt-out, honored right away). Call published business lines manually; no autodialed, prerecorded or AI calls and no texts, even if an Overture or website number turns out to be a mobile.

**Coverage on 2026-11-13 data** (`research/findings/contact-enrichment-2026-11-13.md`): 28% of all 1,343 prospects have at least one suggestion (21% phone, 19% website, 11% email, 12% contact name) and 19.5% of the 215 best-fit prospects; only 3% of the 1,873 company owners and buyers, because most are single-property LLCs without a public listing. That is why the founder still researches by hand for the rest. Revisit paid enrichment only if these rates stay too low for the weekly send volume.

## 5d. Two extra pilot lists (non-trade buyers)

These are for buyers outside the porch/masonry track. Both are pilots: say plainly that you are testing the list and want their outcomes.

- **Pest control (`/pilots/pest`).** Restaurants whose newest inspection shows a fresh pest finding, which is the first one at that license in 180 days. The latest week's list is small at first because inspections post late; the 28-day list gives a first batch. The page lists Chicago pest-control companies to pitch (Overture Maps) and has a cold-email draft. Offer one company a free 4-week list in exchange for filling in the `date_contacted`, `outcome` and `notes` columns of the CSV (`/export/pest`). Don't quote a chance of winning: none has been measured. Rows marked "general mention only" are a generic "pests" citation (often entry points), weaker than a rodent or roach finding. They call or visit the restaurants themselves (business lines, manual dialing only).
- **Closed restaurant spaces (`/commercial`, bottom section).** Addresses that just lost their restaurant and have no new food license yet. Use the computed rates on the page when pitching: about one in seven gets a new food business 31+ days after the closure, five times the rate at ordinary restaurants. Only about one in nine pulls a build-out permit, a weak signal, so don't promise construction work. Test it with build-out GCs, kitchen-equipment dealers, signage shops and commercial brokers. Each lead's letter goes to the property owner and never mentions the closure, the inspection or the City.

- **New business coming (`/commercial`, CSV `/export/new-business`).** Build-out permits at commercial, mixed-use and larger apartment buildings that have no business license yet. Use the computed rates on the page: about one in seven gets a new business license within a year (more for commercial/industrial buildings), typically 3 to 8 months after the permit, about ten times the rate at comparable addresses. Pitch it to sign shops, POS/payments sellers, insurance brokers, commercial cleaners, security installers, furniture dealers and brokers. It is a targeting list: the permit names the GC and applicant, not the future tenant.
- **Trades still open after big permits (`/commercial`).** For elevator, electrical, fire-alarm and sign contractors: after a $1M+ permit, these follow-on jobs usually go to a contractor who was not on the big permit. The table shows each trade's rate and timing, and the recent big permits show which trades have already appeared. Don't pitch it to plumbers, HVAC or roofers: about half of those jobs go to contractors already on the permit.

## 5e. Event services and brokered deals (`/deals`)

**Finding events (by hand):**
- City data: `/pilots/events` lists organization events in the next 120 days (festivals typically 2 months ahead), recurring series to contact the season before, and block parties (resident-filed: flyers or door hangers on the block a few weeks before, never personal contact).
- Social media: search public posts and local groups yourself (hashtags, neighborhood and school groups, "looking for a DJ/tent/caterer" requests). Paste the post link into **Quick add** on `/deals`. No bots, no scraping tools, no bulk follows or DMs: platforms ban accounts for that, and unsolicited mass messages hurt the brand. Reply to explicit requests where group rules allow.
- Venues and planners: ask banquet halls, churches and park fieldhouses whether they refer customers who need rentals or coordination.

**Contacting people:** one message per person, written for them, using the drafts on the deal page (DM, email, follow-up, quote note). Say who you are, what you offer and how to say no; never imply you're with the City or the platform; never claim "cheaper than the market" (say "one point of contact" and "a transparent flat planning fee"). If they say no or stop, mark **Opted out**: the app then refuses drafts and follow-ups for that contact.

**Doing the deal:** sign partner vendors first (`/deals/partners`: services, area, fee terms, agreement signed). The customer pays vendors directly; you charge a disclosed planning or referral fee. Record quote, fee and "fee collected" on the deal. Get a short written agreement for the planning fee and cancellations; consider event-planner liability insurance before taking on event-day responsibility.

**Measuring:** `/deals` shows contacted → replied → booked rates by source and fees collected. After 30 days, keep the sources that book and drop the rest.

## 6. Weekly pilot operations (about 2–3 hours per pilot per week at the start) [E]

1. **Refresh the data:** `scripts/refresh-data.sh` (about 5 minutes, mostly downloads). Commit `web/data/snapshot.json`, `web/data/pest.json`, `web/data/prospects.json` and `web/data/contacts.json`, republish. The agent's weekly timer (HANDOFF next tasks) does this on Monday mornings; run it by hand if the timer isn't active.
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
- **Phone and text (TCPA, Do-Not-Call, Illinois ITSA; revised 2026-11-18, D-027):** business lines and individuals alike may be called or texted **by hand, one at a time**. No autodialed, prerecorded or AI-voice calls and no automated or bulk texts without prior express written consent. Every number to a person comes from a provider whose terms allow marketing and is scrubbed against the National Do Not Call Registry (within 31 days) and our opt-out list first. Call 9:00–20:00 (law: 8:00–21:00). Open with your name, company and purpose and ask to continue; stop and record the opt-out on request.
- **Individual homeowners and event hosts:** mail or door hanger first, then a hand-dialed call or text under the rule above. Letters are signed by the contractor, give a real return address, and never imitate City correspondence.
- **Letters must open with a not-a-bill box (Illinois 815 ILCS 505/2PP, since 2024-01-01).** At the very top, in at least 14-point bold type inside a black-outlined box: it is not a bill, it is a solicitation, and the sender is not affiliated with the City or any government agency. The app prints it on every letter draft and in the mail-merge CSV (`disclosure_box`). Read on ilga.gov 2026-11-18 (`docs/18` §6).
- **Letters print the contractor's Chicago license number** (Municipal Code 4-6-280(2): "the license number shall appear in any advertisement placed by or on behalf of a home repair contractor"). Set it in Settings; drafts show `[license number]` until then.
- **Every draft carries a reference code;** owners who call or write quote it and the reply is logged at `/leads/replies` (phone or email they give stay in the database, never in shipped files). Call back only the number the owner gave, by hand.
- **Emails say they are an advertisement** (CAN-SPAM 15 USC 7704(a)(5)); the investor email draft does.
- **Never imply City affiliation.** Not in subject lines, envelopes, letterhead or scripts. Say "public records" and name the source.
- **No owner names in prospecting material** (emails, teasers, social posts). Names appear only in client workspaces after the pilot starts.
- **Honesty:** every number comes from the snapshot (`models` and leads). Say "historical rate" and "floor"; never "guaranteed" or "exclusive". Label estimates as estimates.
- **Records:** log consent, opt-outs, and sources for each contact.

## 9. 30-day schedule to land three pilots

| Days | Do |
| --- | --- |
| **1–3** | Run `scripts/refresh-data.sh`; open `/prospects?fit=best` and pick the first 60 (porch and masonry). Create the sending domain, mailboxes and warm-up (`12` §3); set up HubSpot. Fill `[Your name]` and the postal address template. Read section 8 once more |
| **4–7** | Research contacts for the 60 (start with the free suggestions on each teaser page, then website and state registry). Skip anyone without a business email or phone. Send the first 15 day-0 emails per day once warm-up allows |
| **8–14** | Day-0 emails continue to ~120 contacts total. Day-4 touches go out for the earliest batch. Start phone calls to business lines on day 4 after each email. Book meetings; prepare each meeting by opening the contractor's teaser |
| **15–21** | Day-10 touches for the first batch. Run 15-minute meetings: show the contractor's own teaser, then the real lead list for their neighborhoods in the app. Offer the pilot. Create the workspaces for the first yes answers and deliver the first weekly report within 48 hours of the yes |
| **22–28** | Second wave of 60 prospects (continue best-fit list). First weekly operations cycle for pilots (section 6): reports, letters, outcome marking. Collect feedback; fix wording or data issues found |
| **29–30** | Review metrics (section 7): reply rate, meetings, pilots started. Write down what worked in `decision-log.md`. Decide: double down on the winning trade and subject line, or change the offer. If fewer than three pilots started, interview the "no" replies for the real reason before changing anything |

**Fallbacks if replies are low:** shorten the email and put the counts in the subject; try the phone first for companies with no email; offer a free sample list for one neighborhood (a "free 2-week trigger list for your area", as in `11` §6) before asking for a pilot; test a small batch of our own direct mail to contractor business addresses (`12` §3 budgets ~$300–$600 for letters).
