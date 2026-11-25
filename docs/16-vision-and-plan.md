# 16 — Vision, where we are, and what to do now vs later

*v1.1, 2026-11-18 (founder chose to test event services and brokered referrals; see the update in §4).* *v1, 2026-11-17. Written after testing the event, brokerage, cleaning, dumpster and national-expansion ideas against real Chicago records (signal lab round 6). Numbers come from `13-signal-lab.md`, the backtests and the snapshot; anything not measured is labelled [hypothesis].*

## 1. The vision in one paragraph

Brickline finds **who is about to buy, from public records, before it is obvious**, measures how often that exact signal turned into a purchase in the past, and hands a seller the next action (who to contact, when, with a drafted message). The moat is not the AI or the data access, which competitors can copy; it is (1) signals that were tested on years of history, (2) a growing record of which leads actually closed, and (3) relationships with the sellers who use it. Chicago is the lab. Owner-facing trades are the cash wedge; B2B pilot lists are the second track; other industries and cities come only after the first paying customers prove the loop.

## 2. Where we are (2026-11-17)

**Built and working:** a weekly pipeline over about 30 public sources (plus 7 weekly archives); 41 tested hypotheses (wins and failures recorded); 6 lead kinds with historical chance of work and letters; 4 B2B pilot lists (closed restaurant spaces, new business coming, trades still open after big permits, pest control) with buyer lists and pitch emails on `/pilots`; the founder's sales pipeline with an assistant that drafts emails, call briefs and outreach status; measured revenue tracking (job value on won leads, deal value on paying prospects); live private app.

**Not yet true:** no paying customer, no recorded outcome, no case study. Every rate in the product is a historical proxy (permits, licenses), not a sale.

**The bottleneck is selling, not data.** We have more validated lists than buyers. Every idea below is judged by one question: does it get the first paying customers faster, or does it add surface area before anyone pays?

## 3. The incoming ideas, debated

| Idea | The claim | What we checked | Verdict |
| --- | --- | --- | --- |
| **Event intelligence** (permits, social media, venues → rental/catering leads) | Find events 3–9 months ahead while organizers still choose vendors | Park District permits have no application date, no attendance, and name an organization on 0.6% of recurring series; real events are first listed a median 3 days after they start; CDOT shows big events ~31 days ahead (15–25% visible 90+ days). Only *recurring* series predict next year (53.4% vs 18.5%, median 198 days ahead). Social media at scale: TikTok/Meta research APIs are not for commercial lead gen; Eventbrite public search is deprecated | **Later, and only if a rental company asks.** New events can't be found early; recurring events can, but without organizer contacts. Not a product now |
| **Event brokerage / coordination** (become the middleman, take a fee) | Fast first dollars, plus outcome data | No vendor network, no event clients, liability for event-day failures, sales-tax questions if we rent in our own name, ~15 hours per event [hypothesis], and the same cold-outreach problem we already have | **No.** It is a second service business that competes for the founder's only scarce resource (time). The good part — *use real sales to measure lead quality* — we adopt through pilots with outcome tracking (built) |
| **Referral / pay-per-won-job** | Vendors pay only when a referred job closes | Job-value tracking now exists; attribution uses lead IDs; legal limits: no acting as a contractor, no reselling, no healthcare referral fees (anti-kickback), state rules differ (e.g. California referral services) | **Yes, as a pricing option on what we already sell** ("free sample → 30-day pilot → subscription, or a fee per won job"). Not as a brokerage operation |
| **Opportunity Router, vendor matching, bidding network, marketplace** | Route each lead to SaaS / referral / brokerage by expected profit per hour | There are zero transactions to route | **Later** (after ~10 closed deals). Until then a one-line rule in the playbook is the router |
| **Brokerage CRM, attribution, case-study generator** | Prove results to the next buyer | Lead statuses + won job value + prospect deal value + `/results` exist; lead IDs are stable | **Done (minimal).** Case-study pages come after the first won jobs, built from `/results` |
| **Commercial cleaning** | Post-construction and pre-opening cleaning, recurring janitorial | No public "construction complete" signal in Chicago; the H33 build-out-permit list *is* the pre-opening list (15.2% become a new business within a year, median 157 days); restaurants show a pre-opening inspection a median 14 days before the license (~29/week); janitorial contracts are not public | **Now, with what exists:** sell the "New business coming" list to cleaning companies (buyers already on `/pilots`). Post-construction cleaning and government janitorial bids: no |
| **Dumpster / roll-off** | Demolition and renovation permits → dumpster orders | Public-way dumpster permits follow a project permit 9.6% of the time (13.6×) but top-10 haulers hold 83%, and 70% of GCs reuse a hauler they used before (14% expected by chance) | **No** as a product. The market is concentrated and relationship-driven |
| **Portable restrooms, fencing** | Same as dumpsters | Not tested; likely the same structure | **Later**, only if a buyer asks |
| **Property-management accounts** | One manager buys many trades across many buildings | 915 company mailing addresses control 10+ Chicago parcels (19,396 parcels); 130 of those portfolios had a city violation in the last 90 days (a shared mailing address can also be a tax agent) | **Next lab test.** Promising because one account = many jobs and our data already links owners to buildings and violations |
| **Lifecycle intelligence / relationship graph** | Follow a property from zoning to permits to opening to operations | The pieces exist and are validated separately: zoning → permit (H34), big permit → follow-on trades (H29), build-out → new business (H33), closure → new tenant (H26) | **Later, as a demo first:** an address timeline page would make pitches concrete. No graph database |
| **National discovery, regional execution** | Monitor the whole US, broker selectively | Our adapters, address keys and validations are Chicago-specific; another city means new sources and new tests. Census permits are aggregate counts, not leads | **Year 2.** Chicago depth first; a second city only after Chicago customers pay |
| **Pricing tiers ($99–$999), 3-day trial** | Subscription ladder | Untested; a 3-day trial is too short for any lead to close | **Pilot pricing now** (free 5-row sample → 30-day pilot with outcome recording → subscription or per-won-job). Tiers after 5 paying customers |
| **Income projections ($2k–$20k/month)** | Funnel math | Large cold-email studies show ~0.24% positive replies; our targeting should do better but is unproven | **Plan on our own funnel:** measure the first 100 conversations, then project |

## 4. The plan

**Now (next 30 days) — get the first 3 paying pilots. Founder work, no new features.**
1. Contractor track (main): 10–15 best-fit porch, masonry and roofing contractors from `/prospects`; email 1–3 via the assistant drafts; offer a free sample of their area's leads and a 30-day done-for-you pilot (weekly report, print-ready letters).
2. B2B track: pick **two** pilot lists only — "New business coming" (cleaning companies, sign shops) and "Trades still open" (elevator, fire-alarm contractors). 10 buyers each from `/pilots`; send the 5-row sample; offer a 4-week pilot in exchange for recorded outcomes.
3. Record everything: replies, meetings, pilots, won jobs with values, deal terms. This is the data that becomes the case study and the pricing evidence.

**Update 2026-11-18 — founder decision: run two brokerage tests alongside the pilots, tracked in `/deals`.**
- **Event services:** khaled offers end-to-end event planning/coordination with partner vendors (customer pays vendors directly; khaled charges a disclosed planning fee). Leads: organization events from city permits (`/pilots/events`: festivals are visible a median 59 days ahead, 43% name an organization), recurring series the season before, block parties by flyer only, the **daily scanner** (`/events?tab=scanner`, D-029), and social posts messaged one at a time (no bulk follows or DMs; honor every opt-out). Venue partnerships remain a hand source.
- **Porch referral test:** letters in khaled's own brand to porch-notice owners, inbound calls, hand-off to 2–3 partner porch contractors with a written fee per appointment or per job.
- **What makes these worth it:** every deal is recorded from first contact to fee collected, so after 30 days we know cost and conversion per source instead of guessing. Same gate at day 60, counting brokerage fees as paying customers.

**Gate at day 60:** 3+ paying pilots → build client logins and move lead data out of shipped files (HANDOFF task). 0 pilots after ~100 real conversations → change the offer or the audience before building anything else.

**Next (60–120 days), only after the gate:**
- Property-management portfolio test (lab round 7) and, if it wins, an account-level list.
- Zoning pipeline list (H34/H35) for GCs.
- Case-study page generated from `/results` once 3+ won jobs exist.
- Client logins (security work first).

**Later (after ~10 paid outcomes):** opportunity router and vendor matching, address timeline demo, recurring-event alerts if a rental buyer appears, paid contact enrichment, a second city.

**Never (or until the law and the business change):** bulk DMs or follows, fake-account farms, captcha-solving services, reselling rentals or contracting work in our own name, referral fees in healthcare, autodialed or AI calls, texts without consent. Authenticated social *collection* with the team's own sessions is in D-029 / `docs/21` (Omar accepted the account risk); stop it if a platform objects.

## 5. How to pitch (from computed numbers)

- **Porch / masonry contractor:** "Last year X porch repair notices in your neighborhoods; historically about 1 in 7 led to a permitted porch job within a year. We send the owners a letter in your name every week." (Use the teaser page for exact counts.)
- **Cleaning company / sign shop:** "These are commercial spaces with a build-out permit and no business yet. About 1 in 7 gets a new business within a year — 10× the rate at similar addresses — typically 3 to 8 months after the permit. You reach them before they open."
- **Elevator / fire-alarm contractor:** "After a $1M+ permit, most elevator and fire-alarm follow-on work goes to a contractor who wasn't on the original permit. Here are this month's big permits and which trades have already shown up."

Never promise wins; quote the rate, the timing and the evidence, then offer the sample.
