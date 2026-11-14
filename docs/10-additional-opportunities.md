# Deliverable 10 — Additional Opportunities

*v1, 2026-11-14. Ranked roughly by value ÷ effort. Labels: [V] verified, [H] hypothesis, [S] speculative.*

## High value, near-term (build on what the MVP already produces)

1. **GC Relationship Graph ("who builds with whom").** From resolved permit parties: GC ↔ sub ↔ architect ↔ owner edges with counts, recency and value. Lets a sub see which GCs use competitors, which rotate subs, which architects feed which GCs. Computable from Chicago data today [V]; this is the most defensible early asset.
2. **Competitor and market-share reports.** "Your top 5 competitors did X major jobs this quarter, for these GCs, in these neighborhoods; your share moved from a% to b%." Strong retention hook, cheap to produce [H on value].
3. **"Open door" alerts.** A GC that historically used one HVAC sub just used a different one; a new GC entered your size band; a frequent competitor disappeared (capacity issue?). Rare, high-signal events [H].
4. **Architect and owner targeting.** Architects specify products and recommend GCs; repeat owners/developers return to the same team. Useful for suppliers/manufacturer reps and for subs pursuing negotiated work [H].
5. **Daily briefing email.** The "good morning" briefing from the brief, delivered by email before any app exists. Cheap; habit-forming [H].
6. **Direct-mail engine for compelled demand.** Violation → letter within days (masonry, porch, windows, roof), with careful non-governmental messaging. Natural agency add-on with measurable response codes [H; compliance review needed].

## Medium-term

7. **Pre-permit project tracker for Chicago.** Zoning map amendments, planned developments, plan commission and ZBA agendas parsed into projects linked to later permits. Raises timing for every commercial trade; also lets us measure "how many days earlier than the permit" [H].
8. **Public procurement layer.** City, CPS, Park District, Public Building Commission, county, state, federal bids for the user's trade and size, joined to the GC graph ("who usually wins these") [H].
9. **Restaurant opening tracker.** Join renovation permits → license applications → license inspections → opening, to serve food distributors, equipment, cleaning, pest, POS, insurance [V signals exist; H on value].
10. **Outcome-trained scoring.** Once hundreds of feedback labels exist, learn per-trade weights; publish "items like this produced meetings X% of the time" — a claim feed competitors can't make [H].
11. **Unified attribution view (agency × engine).** One table of leads → appointments → customers by source (Google Ads, Meta, organic, intelligence). Helps clients allocate budget and makes the agency stickier [H].
12. **Subcontractor capacity marketplace (reverse direction).** GCs searching for qualified subs by trade, size, recent work and inspection history — the same graph sold to the other side [S].

## Longer-term / speculative

13. **Supplier and manufacturer enterprise tier.** Territory-level contractor activity feeds via API/warehouse share for distributors and building-product manufacturers — higher contract values, Dodge-like buyers [H].
14. **Inspection-performance signals.** Contractor inspection pass/fail history as a quality signal (Shovels markets similar metrics [V]) for GCs choosing subs and for insurers [S].
15. **Insurance and surety data products.** Contractor activity/volume trends as underwriting signals [S].
16. **Climate/storm overlays for roofing and restoration** (hail swaths from NOAA + roof permit history) — only where the residential cluster is pursued [S].
17. **Multifamily and ADU tracking** using Chicago's new `residential_unit_change` permit column (added Oct 27, 2026 [V]) — unit additions signal demand for flooring, appliances, cabinets, property management [H].

## Automation opportunities (internal efficiency)

- Auto-generated first drafts of every report section; humans edit rather than write.
- Review queue that only surfaces low-confidence matches and new entities.
- Schema-drift and freshness monitors on every source.
- Templated industry snapshots in HighLevel/HubSpot for fast client onboarding.
- Per-client "reason to call" library learned from which openings got replies.

## Competitive advantages worth compounding

| Advantage | Compounds because |
| --- | --- |
| Resolved entity graph | Every new source and correction improves every customer's view |
| Outcome data | Only a managed service sees meetings and wins; feeds don't |
| Local pre-permit collection | Labor-intensive per city → hard for national feeds to match deeply |
| Agency relationship | Sees inbound + outbound results; owns the client's CRM setup |
