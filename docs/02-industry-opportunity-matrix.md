# Deliverable 2 — Industry Opportunity Matrix

*v1, 2026-11-14. Chicago signal volumes are [V] from `research/findings/chicago-signal-probe-2026-11-14.md` (permits: last 90 days; violations, licenses, food inspections: last 30 days). Job values, difficulty and willingness to pay are [E]/[H] judgments to be replaced by interview and pilot data.*

## How to read this

The key question for every industry is **timing**: does the signal arrive *before* the buyer has chosen a vendor? Chicago data shows that for commercial MEP trades the answer is usually *no* (the sub is named on the permit at issue: electrical 92%, plumbing 84%, HVAC 74%; masonry 41%) — so for those trades the product must be relationship/market intelligence and pre-permit signals rather than permit alerts.

### Scoring (1–5 each; higher is better)

- **T** Timing edge — signal precedes vendor selection.
- **Vol** Signal volume in Chicago.
- **Val** Value of a won customer (job size × repeat).
- **D** Data accessibility (free, structured, current).
- **W** Willingness to pay for leads/intelligence (budget, sales culture).
- **Ez** Ease of building the module.

**Score = 2·T + Vol + Val + D + 2·W + Ez** (max 40). Timing and willingness to pay are double-weighted because a late or unpaid-for lead is worthless however good the data.

---

## Table A — Signals and data

| # | Industry | Demand events | Best signals (Chicago availability) | Chicago volume [V] | Timing edge |
| --- | --- | --- | --- | --- | --- |
| 1 | Electrical (commercial) | New construction, renovation, tenant build-out | Permits (sub named at issue), pre-permit zoning/PD filings (not in open data), public bids | 1,458 electrical-work permits; sub named on 92% of major permits | Late for the job; strong for GC/market intel |
| 2 | HVAC (commercial) | New construction, renovation, equipment replacement | Permits (ventilation/refrigeration contractors named), mechanical permits | 119 mechanical-work permits; HVAC sub named on 74% of major permits | Late for the job; strong for GC/market intel |
| 3 | HVAC (residential replacement) | Equipment failure (~15–20 yr life) [E], home sale | Parcel permit history (Cook County Assessor, lagged), home sales (lagged months) | Weak/indirect | Weak; old building ≠ old equipment |
| 4 | Plumbing (commercial) | New construction, renovation, restaurant build-outs | Permits (plumber named), sewer/water work | 176 plumbing permits; plumber named on 84% of major permits | Late for the job; strong for GC/market intel |
| 5 | Concrete / foundations / flatwork | New construction, demolition → rebuild, parking lots | Wrecking/demolition permits (precede new builds), new-construction permits, zoning | 189 demolition, 452 new-construction permits; masonry/concrete named on only 41% of major permits | Medium — demolition and early sitework precede concrete |
| 6 | Roofing | Storm, roof age, sale, violation | Reroof permits (names competitors), roof violations, hail data (NOAA), parcel permit history | 473 reroof permits; roof violations at 46 addresses | Medium (violations/storms); permits = competitor intel |
| 7 | Masonry / tuckpointing (residential, Chicago-specific) | Exterior wall/parapet violations, age | Building violations, masonry permits | 627 masonry permits; "repair exterior wall" among top open violations; masonry violations at 81 addresses | Strong (compelled demand) |
| 8 | Porches / decks / stairs | Porch-system violations (Chicago 2-/3-flats) | Building violations | Porch/stair violations at 143 addresses; 251 porch permits | Strong (compelled demand) |
| 9 | Windows & doors | Window violations, energy upgrades | Building violations, replacement permits | Window/door violations at 209 addresses; 86 replacement permits | Strong (compelled demand) |
| 10 | Demolition / excavation / grading | Redevelopment, zoning change | Zoning/PD filings, land sales, demolition permits | Low volume in city | Needs pre-permit data |
| 11 | Fire protection / fire alarm | New construction, change of use, annual inspection | Fire alarm permits (named), new construction, new businesses | 272 fire-alarm permits | Medium; recurring inspection contracts are the prize |
| 12 | Security / low-voltage / AV | New business, build-out, relocation | Renovation permits, new business licenses, communication-equipment permits | 93 communication-equipment permits; 621 new licenses/30d | Strong (usually not named on building permits) |
| 13 | Telecom / ISP (business) | New building, new business | New construction, new business licenses | As above | Strong, but big carriers have their own data |
| 14 | Commercial cleaning (post-construction + janitorial) | Construction completion, new business, new tenant | Permit milestones (final inspection / certificate of occupancy), new business licenses | 621 new licenses/30d; 452 new-construction permits/90d | Strong (not named on permits) |
| 15 | Landscaping (commercial maintenance) | New building completion, property sale | Completions, property sales | Low–medium | Medium |
| 16 | Solar | Roof replacement, home sale, utility rates | Reroof permits (good moment for solar), solar permits (competitor intel) | 523 small solar permits; 473 reroofs | Medium |
| 17 | Equipment rental | Contractor starts a job | Permits naming the contractor, demolition/new construction | ~84 major projects/week, contractor named | Strong (buyer on the record) |
| 18 | Building-material suppliers / distributors (electrical, plumbing, HVAC, lumber, concrete) | Contractor starts a job | Permits naming the contractor + value + scope | Same as above; 627 distinct GCs, 300–400 distinct subs per trade/90d | Strong (buyer on the record) |
| 19 | Commercial kitchen equipment | Restaurant build-out | Renovation permits mentioning restaurant/kitchen; food license filings | 101 new retail-food licenses/30d | Medium (licenses come late; permits earlier) |
| 20 | Food & beverage distributors | Restaurant opening, ownership change | License inspections, new retail-food licenses | 221 license inspections/30d | Strong (pre-opening, recurring revenue) |
| 21 | Signage | New business, rebrand | New business licenses, renovation permits | 532 sign permits (sign contractor named) | Medium (licenses earlier than sign permits) |
| 22 | Property management | New multifamily, sale, distressed owner | Completions, sales (lagged), violations | Violations at 876 addresses/30d | Medium |
| 23 | Restoration (water/fire) | Emergencies | Not reliably public; insurer referral driven | Low | Weak |
| 24 | Commercial real estate brokerage | Vacancy, sale, expansion | Sales, permits, licenses (vs CoStar/Reonomy) | Medium | Weak vs incumbents |
| 25 | Home inspection | Home sale | Realtor referrals; sales lag | — | Weak |
| 26 | Commercial insurance brokers | New business, new construction, new fleet | New business licenses, new construction | 621 new licenses/30d | Strong for new businesses |
| 27 | Accountants / business services | New business formation | New business licenses, state registrations | 621 new licenses/30d | Strong but crowded, low value |
| 28 | Elevator maintenance | Elevator violations, new buildings | Building violations, elevator permits | "Maintain or repair elevator" is the #1 open violation (376 + 147 hydraulic); 283 elevator permits | Strong, but a concentrated industry |
| 29 | Pest control (commercial) | Failed food inspection, pest violations, new restaurant | Food inspection results/violations, building violations, new licenses | Pest violations at 39 addresses; 31 failed license inspections/30d | Strong (urgent, recurring) |
| 30 | Waste hauling / dumpster rental | Demolition, renovation | Demolition + renovation permits; CDOT public-way permits | 189 demolition + 1,423 renovation permits | Strong |
| 31 | Logistics / warehouse racking / forklifts | Warehouse build or expansion | New construction (suburbs dominate) | Low in city | Medium; needs suburban data |
| 32 | Healthcare practices | (Agency client, not a signal user) | — | — | n/a |
| 33 | Automotive services | (Agency client) | No useful public trigger | — | n/a |
| 34 | Manufacturing suppliers | Plant expansion | Environmental permits, expansions, hiring | Low | Weak |
| 35 | Commercial printing | New business | New business licenses | Medium | Strong but low value |

## Table B — Commercial fit and score

| # | Industry | Valuable lead looks like | Decision-maker | Outreach | Won-customer value [E] | Build difficulty | WTP [H] | T | Vol | Val | D | W | Ez | **Score** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 18 | Material suppliers / distributors | Contractor X started $1.2M job 3 mi from branch | Contractor owner/PM/purchasing | Rep call/visit, email | $10k–$250k/yr per contractor account | Low–med | High | 4 | 5 | 4 | 5 | 4 | 4 | **34** |
| 17 | Equipment rental | Contractor X starting sitework next month | Contractor PM/superintendent | Rep call, email | $5k–$100k/yr per account | Low–med | High | 4 | 5 | 3 | 5 | 4 | 4 | **33** |
| 1,2,4,5 | Commercial subs — *reframed* (GC intel + pre-permit) | GC that builds your size range, rotates subs, has upcoming work | GC estimator/PM | Email + call, bid-list request | $50k–$1M+ per GC relationship/yr | Medium | Med–high | 4 | 5 | 4 | 5 | 3 | 4 | **32** |
| 14 | Commercial cleaning | Building nearing completion / new tenant opening | GC (post-construction), owner/tenant (janitorial) | Email, call, visit | $5k–$60k/yr recurring | Low–med | Medium | 5 | 4 | 3 | 4 | 3 | 4 | **31** |
| 26 | Commercial insurance brokers | New business opened last week | Business owner | Email, mail, call (business line) | $2k–$20k/yr commission | Low | Medium | 4 | 4 | 3 | 5 | 3 | 4 | **30** |
| 29 | Pest control (commercial) | Restaurant failed inspection for pests | Restaurant owner/manager | Visit, call, email | $1k–$10k/yr recurring | Low | Medium | 5 | 3 | 2 | 5 | 3 | 4 | **30** |
| 5 | Concrete (as lead feed, unreframed) | Demolition done, new construction pending, concrete not yet named | GC | Email + call | $20k–$500k per job | Medium | Medium | 3 | 4 | 4 | 5 | 3 | 4 | **29** |
| 20 | Food & beverage distributors | Restaurant passed license inspection, opening soon | Owner/chef | Visit, call | $10k–$100k/yr recurring | Low | Medium | 4 | 3 | 3 | 5 | 3 | 4 | **29** |
| 30 | Waste / dumpster | Renovation or demolition permit just issued | Contractor | Call, email | $500–$20k/yr per contractor | Low | Medium | 4 | 4 | 2 | 5 | 3 | 4 | **29** |
| 1 | Electrical (commercial, permit alerts) | — | GC | — | $20k–$500k per job | Low | Medium | 2 | 5 | 4 | 5 | 3 | 4 | **28** |
| 7 | Masonry / tuckpointing (residential) | Owner cited for exterior wall | Owner (often individual/landlord) | Direct mail | $3k–$40k | Low | Low–med | 4 | 4 | 3 | 5 | 2 | 4 | **28** |
| 8 | Porches | Owner cited for porch system | Owner | Direct mail | $5k–$40k | Low | Low–med | 5 | 3 | 2 | 5 | 2 | 4 | **28** |
| 16 | Solar | Owner just re-roofed | Homeowner | Direct mail, ads | $15k–$40k | Low | Medium | 3 | 4 | 3 | 5 | 3 | 4 | **28** |
| 28 | Elevator maintenance | Building cited for elevator maintenance | Owner/property manager | Email, call | $5k–$50k/yr recurring | Low | Low–med | 4 | 3 | 4 | 5 | 2 | 4 | **28** |
| 2 | HVAC (commercial, permit alerts) | — | GC | — | $20k–$500k | Low | Medium | 2 | 4 | 4 | 5 | 3 | 4 | **27** |
| 4 | Plumbing (commercial, permit alerts) | — | GC | — | $20k–$300k | Low | Medium | 2 | 4 | 4 | 5 | 3 | 4 | **27** |
| 12 | Security / low-voltage / AV | New business build-out underway | Tenant/owner, GC | Email, call | $5k–$100k + monitoring | Medium | Medium | 4 | 3 | 3 | 4 | 3 | 3 | **27** |
| 9 | Windows & doors | Window violation | Owner | Direct mail | $2k–$30k | Low | Low–med | 4 | 3 | 2 | 5 | 2 | 4 | **26** |
| 11 | Fire protection | New construction / change of use | GC, owner (inspections) | Email, call | $10k–$200k + recurring | Low–med | Medium | 3 | 3 | 3 | 4 | 3 | 4 | **26** |
| 27 | Accountants / business services | New business license | Owner | Email, mail | $1k–$10k/yr | Low | Low | 4 | 4 | 2 | 4 | 2 | 4 | **26** |
| 6 | Roofing | Violation, storm, old roof | Owner/PM | Mail, ads, call (business) | $8k–$200k | Medium | Medium | 3 | 3 | 3 | 4 | 3 | 3 | **25** |
| 19 | Kitchen equipment | Restaurant build-out permit | Owner, GC, kitchen designer | Email, call | $20k–$300k | Medium | Medium | 3 | 3 | 3 | 4 | 3 | 3 | **25** |
| 22 | Property management | Owner with recurring violations; new multifamily | Owner | Mail, email | $10k–$100k/yr | Medium | Medium | 3 | 3 | 4 | 3 | 3 | 3 | **25** |
| 13 | Telecom / ISP | New building | Owner, tenant | Email | Varies | Medium | Low–med | 4 | 3 | 2 | 4 | 2 | 3 | **24** |
| 15 | Landscaping (commercial) | Building completed | Owner/PM | Email, call | $5k–$50k/yr | Low | Low–med | 4 | 2 | 2 | 4 | 2 | 4 | **24** |
| 31 | Logistics / racking | Warehouse expansion | Ops/facilities | Email, call | $50k–$1M | Medium | Medium | 3 | 2 | 4 | 3 | 3 | 3 | **24** |
| 21 | Signage | New business | Owner | Visit, email | $2k–$30k | Low | Low–med | 3 | 3 | 2 | 4 | 2 | 4 | **23** |
| 3 | HVAC (residential replacement) | Old system + recent sale | Homeowner | Mail, ads | $6k–$20k | Medium | Low–med | 3 | 3 | 3 | 3 | 2 | 3 | **22** |
| 10 | Demolition / excavation | Zoning approved | Developer, GC | Email, call | $50k–$1M | High | Medium | 2 | 2 | 4 | 3 | 3 | 3 | **22** |
| 24 | CRE brokerage | — | Owner | — | High | Medium | Low | 2 | 3 | 4 | 3 | 2 | 3 | **21** |
| 34 | Manufacturing suppliers | — | — | — | High | High | Medium | 2 | 2 | 4 | 2 | 3 | 2 | **20** |
| 23 | Restoration | — | — | — | Medium | High | Medium | 2 | 2 | 3 | 2 | 3 | 2 | **19** |
| 35 | Commercial printing | — | — | — | Low | Low | Low | 2 | 3 | 1 | 4 | 1 | 4 | **18** |
| 32 | Healthcare practices | (agency client) | — | — | — | — | — | 1 | 1 | 3 | 1 | 3 | 2 | **15** |
| 25 | Home inspection | — | — | — | Low | — | Low | 1 | 3 | 1 | 2 | 1 | 3 | **13** |
| 33 | Automotive services | (agency client) | — | — | — | — | — | 1 | 1 | 2 | 1 | 2 | 2 | **12** |

## Ranking and launch clusters

The scores cluster around **two shared data pipelines**. Each cluster can be served from one pipeline, which matches the original "build once, serve several trades" logic.

### Cluster 1 — Construction supply chain (permit pipeline + contractor entity resolution) — *recommended first*

Material suppliers/distributors (34), equipment rental (33), commercial subs with the reframed product (32), concrete (29), waste/dumpster (29).

- **Why first:** all are served by *one* pipeline (Chicago building permits + contacts + entity resolution + project clustering), which is free, daily and has history since 2006 [V]. The buyer either appears on the record (suppliers/rental sell *to* the named contractor) or benefits from relationship maps (subs).
- **Verification:** the permit record itself (status, value, parties) plus the contractor's website/licensing; contacts from licensed data (Apollo or similar) with bounce-tested email.
- **Main risk:** suppliers/rental may already get this from reps' relationships or from Dodge/ConstructConnect [H]. Must be tested in interviews.

### Cluster 2 — New business and new building (licenses + inspections + permit milestones)

Commercial cleaning (31), insurance brokers (30), pest control (30), food distributors (29), security/low-voltage (27), signage, telecom.

- **Why second:** genuinely early signals (vendors are not named on these records), recurring-revenue buyers, simple sales cycles. Needs a second pipeline (business licenses + food inspections + permit milestones), which is cheap once Cluster 1's infrastructure exists.
- **Main risk:** lower deal values → lower willingness to pay per customer; FieldClients already targets this exact use-case at $99–$499/mo [V].

### Cluster 3 — Compelled-demand residential (violations)

Masonry/tuckpointing, porches, windows, roofing, elevators.

- **Strong signal, weaker business:** small contractors, lower budgets, owners are often individuals (→ direct mail only), and messaging must never look like a government notice. Good **agency** add-on (direct-mail campaigns built from violation lists) rather than a SaaS wedge.

### Not recommended for the intelligence product

Healthcare, automotive, home inspection, printing, restoration — no reliable public trigger. Serve them, if at all, through agency services only.

## What would change this ranking

- Interview evidence that commercial subs will pay ≥ $500/mo for GC-relationship intelligence → move them to #1.
- Discovering a reliable Chicago **pre-permit** source (zoning/PD/plan-review data) → raises T for all commercial trades by 1–2 points.
- Suburban data purchased cheaply (e.g. Shovels coverage verified for collar counties) → raises Vol for logistics/racking, concrete, landscaping.
