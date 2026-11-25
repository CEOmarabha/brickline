# 17 — Contact coverage, conversion, and the vendor-paid introduction model

*v1, 2026-11-18; status added the same day after the build (section 4a). Written at the end of a research session. Everything marked [V] was measured against live public data by `research/probes/contact_sources_probe.py` (aggregate output in `research/findings/contact-sources-2026-11-18.md`). Everything marked [H] is a hypothesis for the next agent to test or research. Rates for permit/license outcomes are historical proxies, not sales; no lead has been sold or won yet.*

## 1. The problem in numbers

- 6,768 open leads, 5,778 with an owner name, 4,139 with a mailing address. **Phone or email exists on 106 leads (72 companies)**: all from Overture, Chicago business licenses/owners and company websites [V, `contacts.json`].
- Prospects (contractors to sell to): 1,343, of which 286 have a phone and 158 an email. Best-fit 215: 30 phone, 18 email.
- Most owners are individuals: 1,737 of 2,243 violation leads and 1,623 of 1,969 complaint leads. **No open record carries a homeowner's phone or email.** For them the letter is the channel.
- The best lead type, investor purchases (1,700), has 64 mailing addresses (the tax roll lags the sale) and starts at 63 days old because Assessor sales stop at 2026-09-15.

## 2. What the 2026-11-18 research found [V unless noted]

| Source | Adds | Result |
| --- | --- | --- |
| Cook County Assessor parcel addresses (`3723-97qp`, current roll year) matched to the investor buyer's exact name | Mailing address, portfolio size | **580 of 1,636** investor leads without a mailing address have a buyer already on the roll (487 names; 44 are the purchased property itself; 131 buyers own 3+ parcels). Exact-name match, so a floor. The warehouse already has `parcels`; use it instead of live queries |
| Overture places matched by that mailing address | Phone, email, website at the address | 61 of 487 addresses have a listing; 59 with phone, 38 with email. A suggestion only: the business at the address may not be the buyer |
| Illinois PTAX-203 transfer declarations (`illinois-edp.data.socrata.com/resource/it54-y4c6`, 2014-) | **Fresher sales**, buyer company name, PIN, buyer's agent in 7% | Newest record 2026-11-13 vs Assessor 2026-09-15. 8,507 Chicago transfers since 2026-09-16, 3,760 with a company buyer (before our filters). **No phone or email columns.** Line 10l ("buyer is a real estate investment trust", not "an investor"; corrected 2026-11-18) is ticked on 2 of 8,507. Preparers are closers/title/clerking firms (2,218 distinct; top 12 hold 19%): not a route to the buyer |
| Chicago Foreclosed Rental Property registry (`yhcw-iu53`) | Notice agent phone and email | 22 leads that had neither (mostly investor purchases and violations); 586 rows, 99 registered in the last 12 months. Only 5 of 19 agents look like companies: treat individuals' numbers under the playbook rules |
| Illinois contractor registries: CDB vendors (`3dh9-yktq`, phone on all 2,885), IDPH Lead Contractor Registration (`vpwp-h7xr`), IDPH Asbestos Contractors (`kt5u-9dcu`, phone and email) | Contractor phones | **23 of 1,343 prospects newly reachable** (19 CDB, 4 lead; asbestos 0) |
| Chicago Building Code Scofflaw List (`crg5-4zyp`) | No contact; a priority flag | **23 leads** sit on it (9 violation, 8 investor, 4 complaint, 2 vacant). Not backtested; do not rank on it before a test |
| Chicago business licenses matched by mailing address | — | 19 of 487: dead end, and the license data has no phone column |
| Vacant-building violations (`kc9i-wq85`) | — | 1 address matched: dead end |

Catalog sweep of the Chicago, Cook County and Illinois Socrata portals for phone/email columns: nothing for contractors or owners beyond the rows above (the rest are schools, clinics, ward offices, lobbyists, veteran-owned businesses 2018). Illinois Secretary of State (`apps.ilsos.gov`), `chicago.gov` (contractor license lookup) and SAM.gov returned 403 or need a key from the cloud VM: retry from the founder's network or ask him to look up the top leads by hand.

## 3. The model we are pursuing (decided with the founder 2026-11-17)

Vendor-paid introduction, not a contractor business. The owner hires a licensed contractor directly; the contractor pays Brickline on a signed job that started from our lead. Panel of three contractors per trade, 30-day exclusive per lead, reply within two business days or the lead moves on. Fees to test: porch/masonry flat $750-$1,500 or 5-8%; GC on investor renovations flat $2,500-$5,000 or 3-5% [H]. Brickline never prices the job, hires the crew, supervises work or touches the owner's money (Chicago's General Contractor license covers bids, hiring and supervising; a Home Repair license cannot hire others). Never touch insurance claims (Illinois treats paid public-adjuster lead generation as public-adjuster activity). Have a lawyer read the one-page vendor agreement before the first fee. See `docs/16` for the rest of the vision.

## 4. Work list (in order)

Each item: what, where, how to know it is done. Commit each separately; run the checks in `docs/HANDOFF.md`.

1. **PTAX-203 as the source of fresh investor leads.** New collector `engine/collect/ptax.py` (pattern: `engine/collect/socrata.py`, shared retries in `engine/collect/http.py`) → warehouse table `ptax_transfers` (`engine/warehouse.py` sync/build) → `engine/leads/snapshot.py` investor section (around the `sales` queries, lines 228, 310, 507, 567) uses PTAX for sales newer than the Assessor's newest sale and the Assessor as the deeper history. Match PTAX to parcels by `line_1_primary_pin` (check the digit count against the 14-digit Assessor PIN and `pin10`). Filter like the existing `filtered_out` logic: exempt/related-party (`line_10b`), bank REO (`line_10h` is a signal of its own, not an investor purchase), court-ordered, condo-unit duplicates. Company detection must use the same `INVESTOR_RE`. Done when: the snapshot's newest investor lead is days old, the investor models (`snap.models.investorPurchase`) still come from the Assessor history and are unchanged, a note in `docs/13` or `docs/15` records the PTAX-vs-Assessor reconciliation (do the two agree on overlapping months?), and lead counts per week match the ~27/week the Assessor feed implies.
2. **Fill investor mailing addresses and portfolio size from the roll by buyer name.** Join `parcels` in the warehouse (owner/mailing names) to the buyer name in `engine/leads/snapshot.py`; set `owner.mailing` with a note ("mailing from other parcels this buyer owns") and `buyer.otherProperties`; leave blank when the best address is the purchased property. Done when: investor leads with a mailing address go from 64 toward ~640 and the lead page labels the source.
3. **Contact sources.** Add the foreclosed-rental registry (by property address, leads), CDB vendors, IDPH lead and asbestos registries (by exact normalized name, prospects) and "listing at the buyer's mailing address" (Overture, medium confidence, labelled "at this address") to `engine/enrich/contacts.py` and the `ContactSource` type in `web/src/lib/contacts.ts`; add the sources to `docs/data-source-registry.md` with licenses (Socrata open data; Overture needs attribution). Also read Overture `socials` for **business pages only** (never personal profiles; see §6). Done when: `research/findings/contact-enrichment-<date>.md` shows the new coverage and the app shows source labels.
4. **Scofflaw flag, then a backtest.** Collect `crg5-4zyp`, show it as evidence on the 23 leads; run a signal-lab hypothesis (H42: scofflaw-listed address → permit within 365 days vs matched controls) before ranking.
5. **Contactability and reply tracking (migration `006_*.sql`, additive only).** (a) Per-lead "ways to reach" (mail, email, phone, none) shown on `/leads` and in `snapshot.json`; (b) a unique reply code per lead on every letter and email draft (`web/src/lib/outreach.ts`, `draftOutreach`), a short public route that records a reply (code, time, optional phone/email the owner types) in Postgres, and the weekly report listing replies. The owner contacts us: this is how individual owners become reachable. Never put a real person's data in shipped files (see HANDOFF task 5).
6. **Deep research (§5)** produces `docs/18-contact-research.md` before more code is written for social or email extraction.
7. **Conversion experiments (§7)**, designed first, run with the first panel contractors.
8. **Founder actions** (not code): sign the panel (3 masonry, 2 porch, 1-2 GCs for investor leads), one-page vendor agreement reviewed by a lawyer, the 111 company-owned porch/masonry citations (act-now and this week) and 20 first-time investor buyers worked by hand, outcomes recorded on the leads. Also still open from HANDOFF: confirm the publish, re-create the weekly timer.

## 4a. Status after the 2026-11-18 build (measured on data through 2026-11-17)

1. **Done.** `engine/collect/ptax.py` → `ptax_transfers`; investor leads read Assessor sales plus the declarations it lacks. Newest investor lead 11 days old (was 67); 2,424 investor leads, 1,302 from PTAX; models unchanged (byte-identical). The plan's "~27/week" was wrong: the Assessor history implies about 75 company purchases a week in fully loaded weeks (83 combined); June–September now 74 a week instead of 22. Reconciliation: `docs/15` §6b. The Assessor does not just lag: it skips whole recording weeks.
2. **Done.** 1,102 of 2,424 investor leads have a mailing address (was 64 of 1,700): 91 where the roll already shows the buyer, 1,011 from the tax roll under the buyer's exact name (owner or tax-bill name). Lead page labels the source; `buyer.parcelsOnRoll` holds the count.
3. **Done.** Registries add a phone to 34 prospects (22 only through a registry); foreclosed-rental registry 15 leads matched, 1 shipped (company agent; 6 private agents not shipped); Overture at the mailing address 131 company-owned leads; business pages for 84 prospects and 27 company owners. 239 of 7,528 leads have a phone or email (was 106 of 6,768). Findings: `research/findings/contact-enrichment-2026-11-17.md`.
4. **Done, no signal.** 30 leads at listed addresses carry the scofflaw evidence; H42 lift 0.92× (`docs/13` round 7). Not used for ranking (D-025).
5. **Done (founder-logged replies).** Migration `008_lead_replies.sql`: reference codes on every draft, `/leads/replies`, ways to reach on `/leads`, holdout and license-number settings. A public reply page was not built because the published app is private (owners cannot sign in); see `docs/19` §0.
6. **Done.** `docs/18-contact-research.md`. It found two rules our letters broke, now fixed: the 815 ILCS 505/2PP not-a-bill box at the top and the Chicago license number (4-6-280).
7. **Designed.** `docs/19-conversion-experiments.md` (E1 holdout built as a setting; E2–E4 need the first mailing clients).
8. Founder actions unchanged (below).

## 5. Deep research agenda (for the next agent; write `docs/18-contact-research.md`)

Goal: the strongest compliant contact on as many leads as possible. Question everything; label each answer [V] verified live, [V3] third-party, [H]. For each candidate give: what it returns, coverage on OUR leads (test it, do not guess), cost, terms of use, legal exposure, and a verdict.

**A. Companies (investor LLCs, company-owned violations, contractors, buyers)**
1. Illinois SOS LLC/corporation records: manager, member, registered agent, status. Is there a bulk or API route (paid bulk file, open data mirror, OpenCorporates, Cook County Clerk assumed names)? What can the founder do by hand in ten minutes for the top 100 leads, and what would an assistant-assisted workflow look like without scraping a site that forbids it?
2. Company websites: extend `engine/enrich/web.py` beyond homepage + 2 pages (footer, `/about`, `mailto:`, JSON-LD `ContactPoint`, JavaScript-rendered sites, contact-form-only sites). Measure how many matched sites expose an email today (112 of 222 readable) and what a deeper crawl adds.
3. Email verification without guessing: is "known pattern + SMTP/MX verification" acceptable under our rule "never pattern-guess"? What do verification services cost, and does verifying someone's mailbox create privacy or deliverability risk? The rule stands until the founder decides otherwise; recommend, do not change.
4. Free tiers and terms of Hunter, Apollo, Snov, Google Places API, Yelp Fusion (storage terms), BBB, Facebook/Instagram business pages, LinkedIn company pages, Angi/Thumbtack/Nextdoor business profiles, chicago.gov contractor and home-repair license lookups, IDFPR lookups (roofing, electrical). Which return a phone/email for a small Chicago contractor, and which allow storing it?
5. Overture and other open place data: `socials`, `websites`, `emails` fields; additional releases; whether Overture matches improve with alias/DBA from permit records and with address instead of name (61 of 487 did).
6. Address-based routes for LLC owners: the same mailing address across parcels (tax agents, property managers: 915 company mailing addresses hold 10+ parcels, docs/16), registered-agent addresses, and law firms that file Board of Review appeals (`7pny-nedm` has `Attorney_FirmName`, `Appellant_Address`): reach the owner through a business that is expected to be contacted, or learn it is a dead end.

**B. Social media (business pages only unless the founder decides otherwise)**
7. What is legally and contractually usable: platform terms (Meta, LinkedIn, X, TikTok, Nextdoor), the scraping case law, and the difference between reading a business's own public page for its listed contact details and harvesting profiles. Can the founder message a contractor's Facebook business page by hand? Is a business page link from Overture or the company's own website enough to give the founder a manual channel? Record what the recommended, allowed workflow is.
8. Social as a **conversion** channel rather than a data source: a Brickline business page and Google Business Profile that homeowners can verify after a letter (trust), local Facebook groups and neighborhood associations where contractors earn referrals, ads targeted by ZIP to people who received a letter (platform matching of mailing lists: terms, minimum audience sizes, cost). Test what is allowed; do not build anything that scrapes personal profiles.

**C. Individual owners**
9. Is there any lawful, scalable way to contact an individual owner beyond mail? List paid skip-trace providers, what data they use (credit-header and marketing data), the permissible-purpose rules (FCRA/GLBA/DPPA), Do-Not-Call and TCPA exposure for calls and texts, CAN-SPAM for email, Illinois privacy law (check for a data-broker registry and any biometric or consumer-privacy statute that applies), and the consequences if a contractor, not Brickline, makes the contact. Verdict expected: mail plus opt-in reply, unless a provider is clearly compliant and affordable.
10. Mail effectiveness: which creative, offer, timing and address-hygiene choices raise reply rates for owner-targeted trade mail (published studies, vendor benchmarks labelled [V3]); address correction and NCOA costs; whether Chicago ordinances restrict solicitations to people with a code violation (read the actual text).

**D. Compliance spine.** Re-read `docs/14` §8 and write the exact rules for each channel we will use (letter, email, manual call to a business line, social message by hand), plus what the vendor agreement must say about contacting owners, honoring opt-outs and the Home Repair and Remodeling Act. Flag every place where the rules disagree with what is technically possible, and what is out of bounds (§6).

## 6. Rules (revised 2026-11-18 by the founder, D-027: full pursuit, down to the legal floor)

The founder removed every self-imposed limit on whom we contact and how. What remains is the law and data security; each item says why, because breaking it costs more than it earns.

**Allowed now (were self-imposed limits):**
- Individual owners and private event hosts (block-party hosts included) are leads like any other: letters, door hangers, and hand-dialed calls or one-to-one texts.
- Paid data: skip tracing and contact providers may be bought, from providers whose terms allow marketing use (e.g. BatchData, PropStream; not TLOxp or IDI, whose terms bar marketing; `docs/18` §5).
- Block-party applicants' names and mailing addresses are collected (`block_party_hosts`, private lists in `data/private/`).
- Social media: a human may message individuals who posted publicly about their event, one at a time. Collection may use the team's own logged-in sessions (D-029); sending stays manual.
- Business emails built from a company's pattern may be used once a hosted verifier confirms them, sent by hand.

**The legal floor (kept):**
- No autodialed, prerecorded or AI-voice calls and no automated or bulk texts to cell phones without prior express written consent (TCPA: $500–$1,500 per call or text, class actions).
- Every number is scrubbed against the National Do Not Call Registry (within 31 days) and our opt-out list before a sales call or text; calls 9:00–20:00 (law: 8–21); the caller gives name, company and purpose and asks to continue (Illinois Telephone Solicitations Act); stop on request.
- Every opt-out on any channel is honored within 10 business days (same day in practice) and kept forever.
- Letters: the 815 ILCS 505/2PP not-a-bill box, the contractor's license number, no City look. Emails: CAN-SPAM.
- No scraping against a site's terms or robots.txt and no working around a block (CFAA; Illinois computer tampering, 720 ILCS 5/16D).
- Private persons' phones and emails (skip-trace results, replies) never go into git or the app's shipped data files: `data/private/`, the skip-trace provider, or the app's database only. Names and mailing addresses from public records may ship in app data, as the snapshot's owner names already do (`web/data/event-board.json` carries block-party hosts); the app stays private until HANDOFF task 5 moves this data out of shipped files. Probe outputs hold counts only.
- Numbers come from data; confirmed vs inferred stays explicit; humans approve every send; lead rates stay labelled historical proxies.

## 7. Conversion levers to test (design first, then run) [H]

1. **Speed to lead:** PTAX puts a buyer in front of a contractor within days instead of 63+ days; the first permit comes at a median 93-96 days after a sale (25th percentile 38-42). Measure reply and win rate by lead age at first touch.
2. **Contractor-first routing:** 585 investor leads (34%) name a contractor the buyer used before; offer the lead first to the panel contractor with that relationship (they already have the phone). Compare to routing without it.
3. **Reply line per lead:** unique code, short URL/QR and one phone line on every letter; owners opt in with their own number. Measure reply rate by channel.
4. **Holdouts:** keep a random 10-20% of eligible leads unmailed within each segment to measure incremental lift (permit or win rate), otherwise historical rates cannot tell us what the letter did.
5. **Letter tests:** offer framing ("two prices, no charge to you" vs "free assessment"), hand-addressed look vs printed, sender identity (contractor name vs Brickline), plain vs bilingual (Spanish, Polish and others by community area), one vs two follow-ups; weeks 1, 6, 12, 24 cadence already in the app.
6. **Targeting:** send only leads above an expected-value threshold; combine signals (scofflaw, repeat citations, vacant plus violation: 21 complaint+vacant and 31 complaint+violation addresses overlap) after a backtest.
7. **Contractor side:** response SLA (two business days), exclusivity window, one-page case study after the first three wins (`/results`), seasonality (permits peak Aug-Oct, conversion flat by month).
8. **Funnel metrics to record weekly:** leads, contactable, contacted, replied, quote sent, signed, paid, and fee collected, per segment and lead age. Add a "contactable" column to `/results`.

## 8. Handoff prompt

The text below is the self-contained prompt for the next agent. The copy given in chat adds one first step: check out branch `cursor/contact-research-handoff-c826` (this file lives there until it is merged) and branch from it.

> You are continuing the Brickline project in `/agent/repos/brickline` (Chicago lead intelligence for trades built on public records; founder khaled; bottleneck is selling, not data). Read, in order: `docs/HANDOFF.md`, `docs/17-contact-and-conversion-plan.md` (this plan: findings, work list, research agenda, rules), `docs/16-vision-and-plan.md`, `docs/14-sales-playbook.md` §8 (compliance), then `research/findings/contact-sources-2026-11-18.md`. Work on branch `cursor/<name>-c826`, commit each logical change, open a PR with the PR tool (the repo's older "don't create PRs" note is superseded). Goals: (1) execute the work list in `docs/17` §4 in order, starting with PTAX-203 fresh investor leads and the tax-roll mailing fill, verifying every number against live data before writing it; (2) run the deep research in §5 and write `docs/18-contact-research.md` (each candidate tested on OUR leads, with terms, legal exposure and a verdict) before building any social or email extraction; (3) design the conversion experiments in §7. Keep the rules in §6: free contact data only, no pattern-guessed emails, no personal social profiles, no scraping against terms, humans approve all outreach, no personal contact data in shipped files. Re-create the weekly refresh timer (HANDOFF task 1). Run `uv run ruff check engine research` and the web checks before committing. Report plainly what was measured vs assumed.
