# 20 — Opportunity lifecycles: every trigger, the jobs it sets off, and who sells them

*v1, 2026-11-18. Every count is measured on public records through 2026-11-17 (`research/findings/lifecycles-2026-11-17.md`, `research/findings/private-lists-2026-11-17.md`). Lines marked [H] are ideas or expectations not yet tested. The outreach rules are `docs/17` §6 (D-027).*

## 1. The idea in one picture

Every public record that says "something is about to happen at this address" starts a **lifecycle**: a chain of stages, each needing services that local companies sell.

```
trigger (public record) → stages (timing) → services needed → companies that sell them → who already has the job → our move
```

Our move depends on who already has the job:

- **Nobody visible yet:** sell the lead to the vendors, or broker it.
- **A named company already has it:** pitch the next stage's vendors, or offer to match or beat the incumbent.
- **The buyer is a private person:** mail or door hanger first, then a hand-dialed call or text after a skip trace and a Do Not Call scrub.

The catalog lives in code (`engine/leads/lifecycles.py`, 17 lifecycles, 132 service slots). The app shows it at **/opportunities** (sidebar: Opportunity map), filtered by family. The weekly refresh rebuilds it.

## 2. What we can see, measured

| Lifecycle | Triggers (last 12 months) | How early we see it |
| --- | ---: | --- |
| Block party | 4,786 | Median 32 days ahead; repeat blocks a year ahead |
| Street festival, parade or race | 2,265 | Festivals a median 59 days ahead; recurring series a season ahead |
| Wedding or party at a Park District venue | 388 | Late in open data; venues know months ahead |
| Organization event with a food or liquor license | 620 | Median 6 days; repeat holders a year ahead |
| Grand opening of a new business | 342 open spaces now | Median 157 days from build-out permit to license |
| New building, zoning to move-in | 1,559 new-construction permits | Zoning ~10 months before the permit |
| Investor buys, rehabs, resells or rents | 2,424 open leads | Days after recording |
| Owner ordered to make repairs | 2,257 open leads | Complaint ~33 days before the citation |
| Vacant building to sale and rehab | 5,088 complaints | Sale a median 167 days later (19.4%) |
| Household moves (home sold to a person) | 12,135 | Days after recording |
| Restaurant opening | 1,024 new food licenses | Pre-opening inspection ~14 days before the license |
| Restaurant closes, space re-tenants | 167 open leads | New license 32% within a year |
| Business moves to a new location | 430 | Around the move |
| Large commercial project ($1M+) | 1,015 permits | Follow-on trades within 540 days (62%) |
| Basement flood to restoration | 7,318 complaints | Same day to days |
| Demolition and construction cleanup | 691 wrecking permits | Before work starts |
| Rats and pests | 43,422 complaints | Same week |

## 3. Who already covers the job (incumbents)

Chicago permits name the companies on the job, so for permitted work the incumbent is often visible. These are the shares of permits from the last 730 days that name a company in each role:

| Permit group | GC | Electrical | Plumbing | HVAC | Masonry | Architect |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| New construction | 75% | 68% | 62% | 56% | 60% | 96% |
| Renovation/alteration | 100% | 80% | 67% | 58% | 23% | 95% |
| $1M+ projects | 89% | 82% | 74% | 67% | 46% | 85% |

- Wrecking permits name the wrecking contractor (100%). CDOT dumpster permits name the hauler (100%).
- Elevator, sign and fire-alarm work goes on its own later permit. On $1M+ sites the follow-on contractor is usually not one from the first permit (H29), so that job is open.
- **Invisible in public data:** who caters, rents tents, does the flowers, cleans, hauls event waste, or provides security for an event; who cleans or does pest control for a business; who a household hires. For these, the play is to ask, or to offer to match or beat the current provider (a promise we must honor).

## 4. Storylines

Each storyline is a lifecycle in the code. "Where we come in" is the entry point; "who pays" is who would buy the list or the introduction.

**Block party (small, private host, very repeatable).** A neighbor files about a month ahead. Before the day the host needs tables, chairs and a tent, a bounce house, a DJ, food, a cake, balloons and flyers; after it, cleanup and trash hauling.
- *Where we come in:* the host's name and mailing address are on the application. Last year's hosts are next year's leads: of blocks with a party in all three of 2023–2025, **77.8%** held one in 2026; two of three, 47.0%; one of three, 19.8%.
- **2,919 blocks** are already likely 2027 hosts, and 14 parties start in the next 90 days.
- *Who pays:* party-rental companies (205 in Chicago), event planners (856), caterers (536), DJs (273), balloon/decor shops (796). A "summer block-party package" from one partner, offered to hosts in May, is the simplest product [H].

**Street festival or race (organization, recurring).** A chamber, church or promoter files about two months ahead. Production (stage, sound, tents, fencing, printing), site services (portable toilets, security, food vendors), cleanup.
- *Where we come in:* the organizer is named on 43% of festivals, and recurring series are known a season ahead.
- *Who pays:* AV and stage companies (149), sanitation and portable toilets (161), security (132), tent and party rentals (205).

**Wedding or party at a park venue (private, high spend).** Florals, linens, decor, catering, cake, music, photo and video, transport, cleanup. The open data lists these late and never names the couple.
- *Where we come in:* partner with the venues (543 venues in Chicago); they know dates months ahead.
- *Who pays:* florists (646), linen and laundry services (177), photographers (679), bakeries (631).

**Organization fair or fundraiser with a one-day food or liquor license.** Churches, schools, chambers and clubs. The license appears days ahead, but **393 organizations** held one in at least two of the last three years, each with a usual month. Contact them a month or two before that month (list in `data/private/`).

**Grand opening.** A build-out permit predicts a new business about 5 months later (H33). Before opening: signs, post-construction cleaning, internet, furniture, insurance, alarm. At opening: balloons, flowers, catering, photos. After: janitorial and pest-control contracts.

**New building, zoning to move-in.** A zoning change (~10 months before the permit), then demolition, excavation, foundation, structure, systems, finishes, close-out cleaning, landscaping, then occupancy (movers, property management, internet).
- Dumpsters and portable toilets serve the whole job.
- The permit names most of the trades, so pitch the *next* stage's vendors before those trades are hired.

**Investor rehab.** A company buys (state transfer forms show it within about two weeks). Rekey, cleanout, insurance and inspection in the first month; GC and trades over months 1–6 (31% reuse a GC they used before); then cleaning, staging, photos, listing or property management.

**Owner ordered to make repairs, vacant building, household move.** Covered in the product already (letters); D-027 adds hand-dialed follow-up after a skip trace and a Do Not Call scrub. Household moves (12,135 a year) need movers, cleaning, locks, internet, paint and floors, and furniture.

**Restaurant opening, closure and re-tenant.**
- *Opening:* GC, kitchen equipment, grease trap and plumbing, hood and HVAC, signs, post-construction cleaning, insurance, POS; then recurring pest control, linen, janitorial and waste.
- *Closure:* cleanout, equipment removal, deep clean, broker; a new food license follows 32% of the time within a year, which starts a new opening.

**Business move.** 430 location changes a year: movers, IT and phones, signs, cleaning at both ends, furniture, alarm, opening event.

**Large commercial project.** Follow-on elevator, fire alarm, sign and electrical work (62% within 18 months, mostly new contractors), then post-construction and window cleaning, security and janitorial contracts.

## 5. Cleanup, dumpsters and waste: the full niche map

| Niche | Triggers we can see | Source | Status |
| --- | --- | --- | --- |
| Post-construction cleaning (rough, final, touch-up) | New-construction and renovation permits near completion; $1M+ projects | Permits | Lifecycles built; completion timing [H] |
| Commercial janitorial (recurring) | New business licenses, grand openings, business moves | Licenses | Built (lists); win rate untested |
| Residential deep and move-in/move-out cleaning | Home sales, investor resale or rental | PTAX, Assessor | Built (home sale, investor) |
| Junk removal and cleanouts (estate, eviction, foreclosure, hoarding) | Investor purchases, vacant buildings, foreclosed rentals, restaurant closures | PTAX, 311, registries | Built as stages |
| Dumpster rental (roll-off) | Renovation, wrecking and new-construction permits; CDOT dumpster permits name the hauler | Permits, CDOT | Built; 70% of GCs reuse a hauler (H40), so pitch first-time GCs |
| Portable toilets and event waste | Festivals, races, large block parties; construction sites | CDOT, permits | Built as services |
| Event cleanup (street, venue) | Every event lifecycle | CDOT, Park District | Built as the "after" stage |
| Water, fire and mold restoration | 311 water-in-basement complaints (7,318 a year) | 311 | Built (basement flood) |
| Pest control | 311 rodent complaints (43,422), restaurant pest findings | 311, inspections | Built; restaurant pilot exists |
| Hood, duct and grease-trap cleaning | New restaurant licenses; hood or ventilation violations | Licenses, inspections | Opening lifecycle; violations untested [H] |
| Window and pressure washing | New commercial buildings, storefront openings | Permits, licenses | Services listed; untested [H] |
| Graffiti removal | 311 graffiti requests (not yet ingested) | 311 | Idea [H] |
| Snow removal and lot sweeping | Commercial property and parking permits | Permits | Idea [H] |
| Biohazard and trauma cleaning | No ethical public trigger | — | Not pursued |

## 6. Wider list of jobs to map next [H]

- **Events:** quinceañeras, graduations, first communions, holiday parties, nonprofit galas (IRS Form 990 Schedule G), school and church festivals, sports banquets (Park District athletic permits), corporate events (new offices from build-out permits), funerals and repasts (sensitive: venue partners only).
- **Property:** solar installs (neighbors of past solar permits, H01), roof replacement cycles, porch and deck inspections (311), tuckpointing on pre-1910 masonry (H13), tree work after storms, fencing after sales, ADU builds (preapprovals, retest 2027), condo-association projects (big permits on condo parcels).
- **Business:** new-business insurance, POS and payments, uniforms, office furniture, signage (H33 buyers), fire-extinguisher and alarm inspections for new licenses, waste hauling contracts for new restaurants, commercial brokers for closures.

## 7. How to work the private lists (D-027)

`uv run python -m engine.leads.hosts` writes three files to `data/private/` (never committed or shipped):

- `block-party-upcoming-<date>.csv`: parties in the next 90 days, with host name, mailing address, block, ward, the services that event buys, and the channel.
- `block-party-likely-<season>-<date>.csv`: blocks likely to host next season. The `past_seasons` column (2 or 3) ranks them: 3 means about a 78% repeat rate, 2 about 47%.
- `repeat-event-organizations-<date>.csv`: organizations with one-day food or liquor licenses in 2+ of the last 3 years, with their usual month.

Sequence for a host [H]:
1. A letter or door hanger in April–May, with the not-a-bill box and a reference code, offering a block-party package from a named partner.
2. If there is no reply in 10 days, skip-trace the host with a provider whose terms allow marketing, scrub the number against Do Not Call and our opt-out list, then make one hand-dialed call or send one text.
3. Log the reply by code. The partner pays per booked party.

## 8. Next to build (ranked by value × ease) [H]

1. **Package offers by lifecycle in `/deals`:** one partner per service for block parties, and a grand-opening bundle.
2. **IRS Form 990 Schedule G gala list:** recurring fundraising events with organization contacts.
3. **Completion timing for post-construction cleaning:** time from the permit to the last trade permit or the certificate of occupancy.
4. **Load the private lists into the app's database** (owner-only page), so the founder works them in the app instead of a CSV. This needs HANDOFF task 5's private-data path.
5. **Ingest 311 graffiti and sanitation requests**, then test them as cleanup triggers.
