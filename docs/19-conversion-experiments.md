# 19 — Conversion experiments: design

*v1, 2026-11-18. Designs the tests in `docs/17` §7. Nothing here has run: no letter has been sent and no lead sold or won. Labels: **[V]** measured on our data (snapshot through 2026-11-17), **[H]** assumption to replace with measurements. Sample sizes use a two-sided 5% test with 80% power.*

## 0. Why experiments, and what is already built

Historical rates ("15% of porch violations get a permitted repair within a year") say what happens without us. They cannot say what a letter adds, which letter works, or whether speed matters. Only randomized comparisons can. Built in this round (web, migration `008_lead_replies.sql`):

- **Reference code on every draft** (`web/src/lib/reply-code.ts`): 7 characters from the workspace and lead ids plus a check character, the same every time, printed on letters and emails and in the mail-merge CSV (`reply_code`). A misread character or two swapped neighbours are rejected when the code is typed in (all 416,000 single substitutions and 13,508 adjacent swaps in a 2,000-code test); this was added after a browser test typed `T` for `7` and the reply was saved against no lead.
- **Owner reply log** (`/leads/replies`): the founder records a reply by code (channel, date, what the owner said, the phone or email the owner chose to give). Stored only in Postgres. Replies show on the lead page and in the weekly report.
- **Ways to reach** on `/leads` (mail, email, phone, none) with a filter, and `ways_to_reach` in the CSV.
- **Holdout setting** (Settings → "Measure what the letters add"): 0/10/15/20% of letter leads are kept out of printed letters and the mail-merge file, and flagged on the lead page.

A public reply page that owners open themselves was **not** built: the published app is private (Cursor sign-in), so an owner could not open it. Until there is a public host (HANDOFF task 5), letters ask the owner to call or write and quote the code, and the founder logs it.

## 1. Funnel metrics (record weekly, per segment and lead age)

Segment = lead kind × trade × owner type; lead age at first touch in buckets 0–14, 15–45, 46–90, 91+ days.

| Stage | Source |
| --- | --- |
| Leads | `snapshot.json` |
| Contactable | ways to reach ≠ none (`/leads`, CSV) |
| Contacted | lead status Contacted (or later) |
| Replied | `lead_reply` rows with a lead id |
| Meeting / quote | status Meeting |
| Signed (won) | status Won + job value |
| Fee collected | prospect pipeline (Paying, fee model) |

## 2. E1 — Holdout: does the letter add anything?

- **Unit:** letter lead (every kind except investor purchases).
- **Assignment:** `bucket = FNV-1a-32("holdout-v1:" + leadId) mod 100`, held out if `bucket < share` (`web/src/lib/experiments.ts`). It depends only on the lead id, so it is the same in every workspace, cannot be changed by whoever mails, and can be recomputed offline. Randomization by hash also balances segments in expectation.
- **Treatment:** mailed (letter + follow-ups at weeks 6, 12, 24). **Control:** never contacted.
- **Primary outcome:** a permit for the lead's trade at the address within 365 days of the signal, read from city permits. Both arms are measured the same way without contacting anyone. **Secondary:** won jobs (mailed arm only, so not comparable).
- **Analysis:** intent to treat: every eligible lead in a workspace with the holdout on, by arm, whether or not it was actually mailed. Difference in permit rates with a 95% interval, overall and for porch + masonry violations.
- **Sample size [V rates, H effect]:** porch individual baseline about 14.7%. To detect +5 points with 15% held out takes about 3,200 leads (480 held out); +3 points takes about 8,800. At a 10% baseline: 2,350 and 6,400.
- **Flow [V]:** new letter leads with a mailing address per week, citywide over the last 8 full weeks: violations median 93, 311 building complaints 177, vacant 16, porch requests 5. Porch and masonry violations alone: 32–87 per week.
- **What that means [H]:** a +5-point effect on porch/masonry violations needs about a year of one citywide client mailing everything. Pooled across all letter kinds (about 290 a week) it needs about 11 weeks of enrollment. The readout then waits for the outcome window: the median time from citation to permit is about 172 days (`docs/13` H17), so expect a first look about 6 months after enrollment ends and the final one at 12. The holdout is worth running only if the letters are actually mailed at volume. Pool across client workspaces; never change the share or the experiment name mid-run.
- **Cost [H]:** the held-out share of leads is never worked. At 15%, a client loses about 1 in 7 letter leads. Offer it as an option (default off), and explain it as how we prove the list works.

## 3. E2 — Letter tests: which letter gets replies?

- **Unit:** mailed letter lead; arms assigned by the same hash with a new experiment name (e.g. `letter-offer-v1`). Not built yet; add when the first three clients mail.
- **Primary outcome:** reply within 30 days (reference code), fast and countable. **Secondary:** meeting and won.
- **Arms, in priority order:**
  1. *Offer framing:* "free porch assessment" (current) vs "written estimate with two prices, no obligation". The Illinois consumer pamphlet warns about "Persons offering to inspect your home for free" (`docs/18` §6), so the current framing may cost trust.
  2. *Sender:* contractor letterhead (current) vs "on behalf of [contractor], introduced by Brickline". Matters for the vendor-paid model (`docs/17` §3).
  3. *Language:* English vs English + Spanish, **only** in community areas with a high Spanish-speaking share. Published studies found gains only when targeted and losses otherwise (`docs/18` §5). Needs ACS language data by community area, not yet in the warehouse.
  4. *Envelope:* printed vs handwritten-look (costs more; evidence for cold sales mail is thin).
  5. *Follow-ups:* one vs two (weeks 6 and 12).
- **Sample size [H baseline]:** cold home-repair letters, assume 1–2% replies. Detecting 1% vs 2% takes about 2,300 letters per arm; 2% vs 3%, about 3,800 per arm. Test one factor at a time, pooled across clients, and stop a variant early only for complaints or opt-out spikes.
- **Fixed in every arm:** the 815 ILCS 505/2PP top box, the license number, the opt-out, and the not-affiliated line (`docs/18` §6).

## 4. E3 — Speed to lead (investor purchases)

- **Why:** PTAX puts a purchase in front of us days after recording instead of 63+ days later. The first permit after a company purchase comes at a median 83 days (single-family; 25th percentile 35), 94 days (2–6 flats; 42), 113 days (7+ units; 50) and 116 days (commercial; 49) [V, 2012–mid-2025 Assessor history]. A contractor who arrives after the first permit is usually too late.
- **Current stock [V]:** 2,424 investor leads; by age 106 are 0–30 days, 272 are 31–60, 642 are 61–120 and 1,404 are over 120 (the 240-day window keeps older ones for the repeat-buyer view).
- **Design:** among PTAX leads 30 days old or less, randomize the first email to "now" or "in 6 weeks" (hash, experiment `speed-v1`). A 6-week delay harms no one. **Outcome:** reply and meeting within 60 days of the first email; won within 180. **Also, observational:** reply and win rates by age at first touch, for all investor leads.
- **Volume [H]:** about 70 new investor purchases a week citywide [V: the June–September weeks average 74]. One GC client covering a few areas will see a fraction of that, so pool clients or run it with the founder working the citywide list by hand.

## 5. E4 — Contractor-first routing

- **Fact [V]:** 744 of 2,424 investor leads (31%) name a general contractor the buyer used within 540 days of an earlier purchase. These GCs are fragmented: 372 different companies; the top 10 cover 20% of those leads, and 27 GCs with five or more leads cover 255.
- **Design:** when a panel contractor is the buyer's prior GC, offer them the lead first with a two-business-day answer window; otherwise use normal rotation. Randomize at lead level among matched leads (relationship-first vs normal rotation). **Outcome:** accepted within 2 business days, signed within 90 days, fee collected.
- **Precondition:** a signed panel. First count how many of the 744 leads name a panel contractor. Run the test only at 50 or more matched leads per quarter; otherwise just use relationship-first routing, since it costs nothing.
- **Recruiting angle [H]:** the 27 repeat GCs are natural panel candidates: they already work for these buyers.

## 6. E5 — Targeting

- Send only above an expected-value threshold once measured reply rates exist (cut-off set from E2 data, not guessed).
- Signal combinations only after a backtest. **H42 (scofflaw list): no lift** (24.3% vs 26.4% any permit within a year, 387 listed addresses vs 9,493 same-month cited addresses; `research/findings/signal-lab-2026-11-18.partial.md`). The flag stays as evidence only. Complaint + vacant and complaint + violation overlaps are still untested.

## 7. Guardrails (every experiment)

- Holdout leads are never contacted by anyone. Assignment comes only from the hash; nobody overrides it.
- Humans approve every send; no autodialed, prerecorded or AI calls or texts (`docs/17` §6).
- Contact details owners give stay in Postgres, never in shipped files.
- Stop a variant on any regulator or consumer complaint, or an opt-out rate above 2× control [H threshold].
- Each experiment gets a one-paragraph pre-registration in this file before it starts: arms, metric, sample size, readout date.
