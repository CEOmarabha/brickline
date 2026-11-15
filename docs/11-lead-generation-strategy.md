# Lead Generation Strategy — What the Data Can Predict, Formulas, and Backtests

*v1, 2026-11-14. Evidence: `research/findings/backtests-2026-11-15.md` (reproducible with `research/backtests/run_backtests.py`). Labels: [V] measured on Chicago history, [E] estimate, [H] hypothesis to test with customers.*

## 1. Summary

We tested seven lead formulas against 20 years of Chicago permits, 1.5M building violations and 860k Cook County property sales. Five produce strong, usable signals; one hypothesis failed.

| Signal / formula | Result | Who it's for | Verdict |
| --- | --- | --- | --- |
| **Investor / company purchase** of a house or 2–6 flat | 30–38% pull a permit within 12 months (7–14x their own baseline); 8–13% start a ≥$100k renovation (16–28x); ~63 purchases/week | GCs/rehab, porch, masonry, roofing, plumbing, electrical, windows | **Strongest residential signal — and the buyer is a business (B2B outreach allowed)** |
| **Building violation** (porch, masonry, plumbing, electrical) | 10–29% followed by a permitted repair within a year (7.6–12x baseline); ~45 porch + ~53 masonry addresses/week | Porch, masonry, plumbing, electrical contractors | **Strong compelled-demand signal**; owner outreach by mail |
| **GC "open door" score** (past sub rotation) | Top-quintile GCs use a new sub on 30–34% of jobs vs 6% for bottom quintile (5–6x), out of sample | Commercial electrical, plumbing, HVAC subs | **Validated** — the core of the commercial product |
| **Composite parcel score** (signal combinations) | Top 100 parcels/half-year: 25% apply for a ≥$100k project within 180 days (56x base); top 500: 19% (41x) | Commercial subs, suppliers, GCs (pre-application leads) | **Validated** — genuinely *before* the permit application |
| **Restaurant build-out permit → food license** | 29% followed by a new food license; median 90 days before license application, 174 days before license issue | Food distributors, kitchen equipment, cleaning, pest, POS, insurance | **Useful early signal**, modest coverage (12% of new licenses) |
| Individual (owner-occupant) home purchase | 9–17% pull a permit within a year (2–2.5x baseline); ~214/week | Roofing, electrical, windows, solar | **Weak per lead**; profitable only for cheap channels |
| Demolition → new construction | Only 30% lead to new construction; when they do, the new-construction application is already filed (median 8 days *before* the demolition permit) and trades are named (89–98%) | — | **Failed** as an early signal in Chicago |

**Important limitation:** permits only capture *permitted* work. Window replacement, most HVAC replacement and many small repairs don't show up, so every conversion rate here is a **lower bound** on real jobs. Pilots must measure actual close rates.

---

## 2. What "homeowner trades" are, and my recommendation

**Homeowner (owner-facing / residential) trades** are businesses whose customer is the property owner: roofing, porches/decks, masonry and tuckpointing, windows/doors/siding, plumbing, electrical, HVAC, garages, concrete driveways/flatwork, fencing, solar, basement waterproofing, remodeling, painting, landscaping. In Chicago, a large share of "homeowners" are actually small landlords and investors who own 2–6 flats, often through LLCs.

### Is limited outreach a deal-breaker? No — for three reasons

1. **The best residential signal is B2B.** Companies buying houses and 2–6 flats (~63/week) pull permits at 7–14x their own baseline and start major renovations at 16–28x, and 20% of those purchases come from 233 repeat buyers. Contacting a company by email or a business line is allowed (CAN-SPAM for email; manual calls to business lines). Repeat investors are *repeat customers* for contractors.
2. **For owner-occupants, direct mail is legal and is the standard trigger channel.** What's off-limits is automated/AI calling and texting to cell phones without written consent, and cold calls to numbers on the Do-Not-Call list.
3. **Our customer — the contractor — is a business.** We can find and contact every one of them from the permit data itself (e.g., 817 roofing, 677 porch, 444 masonry, 521 plumbing, 848 electrical contractors active in the last 12 months [V]). With no existing relationships, this matters more than anything else.

### Recommendation: yes, start with homeowner trades for cash flow — but only the high-signal slice

| Track | What | Why | When |
| --- | --- | --- | --- |
| **1. Cash flow: "Chicago Property Triggers"** for owner-facing trades | Weekly trigger lists (investor purchases with company contact; porch/masonry/plumbing/electrical violations; individual purchases only where economics work) + done-for-you direct mail + optional local ads/GBP from the agency | Thousands of small contractors, short sales cycles, they already pay for leads/ads; we can reach them cold with our own data; proven signal lifts | Months 1–6, selling from week 3 |
| **2. Software asset: commercial intelligence** | GC open-door ranking, pre-application project predictions, competitor/relationship maps for commercial subs and suppliers | Validated formulas; higher value per customer; defensible entity graph | Build from month 1 on the same engine; sell from month 3–4 with Track 1 revenue and case studies |

Both tracks run on **one engine** (same warehouse, entity resolution, scoring, reports). Track 1 is mostly data + mail operations, so it doesn't fork the codebase.

Why this changes my earlier advice (which treated residential as an add-on): you have no existing contractor relationships and need cash flow within a year. Track 1 is the market we can reach and sell to fastest, and the investor-purchase result shows it isn't limited to mail-only consumer outreach.

What to avoid in residential: predicting replacements from building age (weak evidence, not tested); individual-buyer lists for expensive channels; any outreach that looks like a government notice when using violations.

---

## 3. The formulas

### F1 — Signal lift (is the signal real?)

```text
conversion(signal, W) = P(target event within window W | signal)
baseline(signal, W)   = same properties' event rate in an earlier, signal-free window
lift                  = conversion / baseline
```

Used in BT2/BT3. The within-property baseline avoids "busy neighborhood" bias.

### F2 — Expected value per lead (is it worth contacting?)

```text
EV(lead) = P(job | signal) × P(win | contacted) × job value × contractor margin − contact cost
```

- `P(job | signal)` from backtests [V] (lower bound).
- `P(win | contacted)` — unknown; **the most important number to measure in pilots**. Illustrative assumptions [H]: 5% for mailed owner-occupants, 10–15% for directly contacted investors.
- Job value: median permit reported cost for the trade [V]; margin 30% [E]; mail ≈ $1/piece × 3 touches [E].

| Lead type (illustrative) | P(job) | P(win) [H] | Job value | EV gross profit | Contact cost | Worth it? |
| --- | --- | --- | --- | --- | --- | --- |
| Porch violation → porch contractor | 13.4% | 5% | $20,000 | ~$40 | ~$3 | Yes |
| Masonry violation → mason | 10.4% | 5% | $20,000 | ~$31 | ~$3 | Yes |
| Investor purchase, 2–6 flat → GC/rehab | 38.4% (any permit) | 10% | $20,000 | ~$230 | ~$3 + call time | Yes, best |
| Investor purchase, single-family → porch | 8.2% | 10% | $20,000 | ~$49 | ~$3 | Yes |
| Individual purchase, single-family → roofer | 1.4% | 5% | $23,800 | ~$5 | ~$3 | Marginal |
| Window violation → window installer | 1.6% (permits undercount) | 5% | $9,000 | ~$2 | ~$3 | No (unless real rate is much higher) |

F2 decides which lists we sell to whom and which channel each one gets. Replace the assumptions with pilot data as soon as it exists.

### F3 — Combination score (ranking parcels by multiple signals)

```text
rate(combo) = (hits(combo) + m × base_rate) / (n(combo) + m)       m = 200 pseudo-observations
score(parcel, t) = rate(combination of signals present at t), trained on past years
```

An empirical, explainable alternative to naive Bayes — it doesn't double-count correlated signals (e.g. "any violation" and "3+ violations"). Out of sample (trained 2016–2019, tested 2022–2024), the top 100 parcels per half-year hit 25% vs 0.5% base [V]. Every score is explainable as "parcels with this exact combination converted X% of the time historically".

The strongest combinations [V]: active small permits + a major permit in the last 3 years + recent violations (24–25% in train and test); demolition + small permit (11–13%); investor purchase + permits (8–9%).

### F4 — GC open-door score (commercial subs)

```text
open_door(GC, trade) = share of the GC's past jobs (excluding its first) that used a sub new to that GC
```

Validated calibration [V], jobs from 2022 on, GCs with ≥5 prior jobs:

| Trade | Bottom quintile | Top quintile | Base rate |
| --- | --- | --- | --- |
| Electrical | 5.7% | 31.2% | 14.8% |
| Plumbing | 5.7% | 30.1% | 13.8% |
| HVAC | 5.7% | 34.1% | 16.1% |

Use: rank GCs by `open_door × activity in the sub's size band × proximity` to build a sub's target list. Next refinements: recency weighting, size-band matching, "lost sub" events (a GC's regular sub disappears).

### F5 — Timing windows (when to contact)

| Signal | Median days to first permit | p25 | p75 | Outreach schedule |
| --- | --- | --- | --- | --- |
| Property sale (single-family / 2–6 flat) | 93–96 | 38–42 | 187 | Contact in weeks 1–5 after sale; follow up at weeks 8 and 16 |
| Porch / masonry violation | ~180–190 | — | — | Mail in week 1, then weeks 6 and 12; most permits come after 3 months |
| Electrical / plumbing violation | 120–132 | — | — | Faster: weeks 1, 4, 8 |
| Restaurant build-out permit | 90 to license application | — | — | Distributors/equipment: contact within 30 days of permit |

### F6 — Freshness decay

```text
score_t = score_0 × S(t)      S(t) = share of eventual conversions not yet happened t days after the signal
```

`S(t)` is read directly from the backtest timing distributions, so leads automatically drop in priority as their window closes.

### F7 — Acceptance metrics (how we judge any formula)

- Time-split validation only (train on past years, test on later years). Never random splits.
- **Precision@K per week** (what a customer actually receives), lift vs base rate, recall.
- Calibration by score bucket (predicted vs observed rates).
- Re-fit quarterly; ship a new version only if it beats the current one on the latest held-out period.

---

## 4. What each signal looks like as a product line

| Product line | Weekly volume [V] | Delivered as | Primary buyers |
| --- | --- | --- | --- |
| Investor purchases (houses, 2–6 flats) with buyer entity, repeat-buyer flag, purchase history | ~63/week; 233 repeat buyers | List + company contact research + call/email script | GCs/rehab, porch, masonry, roofing, plumbing, electrical |
| Porch & masonry violations | ~45 porch + ~53 masonry addresses/week | Mail-ready list + 3-touch mail sequence | Porch builders, masons |
| Plumbing/electrical violations | ~12 each/week (episodes) | Mail-ready list | Plumbers, electricians |
| Pre-application major projects (composite score) | ~19/week at 19% precision | Ranked list with reasons | Commercial subs, suppliers, GCs |
| GC open-door ranking + relationship map | 627 active GCs | Monthly target list per sub | Commercial subs |
| Restaurant openings pipeline | ~7 permits/week [V: 5,191 over 13.5 years] | List + timing | Food distributors, equipment, cleaning, pest |

---

## 5. Next experiments (ranked)

| # | Experiment | Why | Effort |
| --- | --- | --- | --- |
| 1 | Refine "investor buyer": exclude banks/land trusts (~13% of matches), flag repeat buyers, link each investor to the contractors on its past permits | Sharper list; "this investor used these GCs before" is a strong sales angle | Low |
| 2 | Owner type for violations (LLC vs individual) via Cook County owner/mailing data | B2B-reachable violations; likely higher conversion | Medium |
| 3 | Violation severity: complaint vs periodic, repeat citations, court/hearing cases | Higher-conversion subsets | Low–medium |
| 4 | Composite score v2: add sale price vs neighborhood, building age, zoning changes, vacancy, permit revisions | Higher precision for pre-application leads | Medium |
| 5 | Open-door v2: size-band matching, recency weighting, "regular sub disappeared" events | More actionable sub target lists | Low |
| 6 | Pilot measurement: actual close rate per signal (P(win)) | Converts F2 from illustration to pricing | Needs customers |
| 7 | Restaurant pipeline coverage: liquor license filings, sidewalk café permits, sign permits | Raise 12% recall | Medium |

---

## 6. Revised first 90 days (given: Chicago-based, no contacts yet, full time, AI tools)

| Weeks | Engine | Go-to-market |
| --- | --- | --- |
| 1–2 | Investor-buyer refinement; weekly trigger-list generator (investor purchases + violations); contractor directory from permits (by trade, volume, recency) | Pick 2 trades (recommend **porch** and **masonry**: strongest violation signals, ~1,100 active contractors, Chicago-specific demand); build a sample report per neighborhood |
| 3–4 | Contact research workflow (company websites, state registry, licensed data) for contractors and investor buyers; mail-merge output | Cold email + calls to ~200 porch/masonry contractors and GCs (CAN-SPAM compliant) offering a free 2-week trigger list for their area; aim for 20 conversations and 5 free pilots |
| 5–8 | Feedback capture; F2 tracking per lead; composite score + open-door outputs for commercial | Pilots run; measure replies, appointments, jobs; convert to paid ($300–$750/month [H]) + mail at cost-plus; start commercial-sub conversations with open-door samples |
| 9–12 | Automate the weekly pipeline end to end; quarterly re-fit of formulas | Target: 5–10 paying Track 1 customers, 2–3 commercial pilots, written case notes |

Cash flow target for month 12 (illustrative): 25 Track 1 customers × ~$600 + 8 commercial × ~$1,000 ≈ **$23k MRR**, plus mail and agency margins [E].
