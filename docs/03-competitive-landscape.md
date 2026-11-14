# Deliverable 3 — Competitive Landscape

*v1, 2026-11-14. Prices are from vendor pages or third-party comparison pages read on or near this date; third-party figures are marked as such and should be re-checked on the vendor page before any decision. Labels: [V] verified on vendor page, [V3] reported by a third party, [E]/[H] as elsewhere.*

## Summary

1. **Raw permit data and permit alerts are cheap and crowded.** Self-serve products range from $19 to ~$1,250 per market per month; several are under $130.
2. **"AI over permits" is already shipping.** Shovels has an in-app agent ("Charlie"), Dodge has plain-language search ("AI Search Assist"), Building Radar's agent "Jeane" claims discovery → scoring → contacts → outreach drafts → CRM updates, with a fully managed option.
3. **Closest concept competitor: FieldClients** — permits + code violations + new business licenses, verified decision-maker email and a dated "reason to call", $99–$499/mo, aimed at field-service companies [V3].
4. **Gaps that remain:** resolved GC↔sub relationship intelligence for subcontractors; local pre-permit signals at owner-operator prices; done-for-you execution tied to measured outcomes; one view joining outbound intelligence with inbound marketing results (the agency link).

## Construction project and permit intelligence

| Company | What it is | Price | Buyers | Data | Notes / weaknesses |
| --- | --- | --- | --- | --- | --- |
| **Dodge Construction Network (Dodge One)** | National commercial project database, planning → bid stage, researcher-verified; plans/specs; Blue Book, Sweets, Bid Board in family | Quote only [V3] | GCs, subs, building-product manufacturers | Proprietary research + plan rooms | Annual contracts, expensive for small subs [H]; AI Search Assist availability described inconsistently [V3] |
| **ConstructConnect (Project Intelligence)** | National project leads + takeoff + bid management | Starter $129/mo per market; Professional from $199/mo per market per seat (annual); Premium from $10k/yr [V3] | GCs, subs, manufacturers | In-house research + AI | No refunds mid-term [V3]; built for estimators |
| **BuildCentral / ConstructionWire** | Vertical project lists (retail, restaurant, hotel, medical, multifamily) | Quote only; $500k project floor [V3] | Suppliers, vendors | Research | High-end |
| **Building Radar** | AI sales platform for construction project sales; agent "Jeane" | Quote only; three tiers incl. Fully Managed [V]; third-party estimate $500–$2,000+/mo [V3, unverified] | Manufacturers, suppliers, enterprise sales teams | 300k+ sources incl. permits and tenders (vendor claim) | Enterprise focus; cancellation-terms complaints reported [V3] |
| **Shovels** | Nationwide permit + contractor data platform/API; contractor profiles, "Decisions" (zoning/planning before permit), properties, residents; agent "Charlie" | Free (500 credits); Basic $599/mo (25k records); Pro $999/mo (50k); Enterprise custom [V] | Platforms, insurers, suppliers, analysts | Permits normalized + AI-rewritten descriptions | Data layer, not a sales workflow; **potential supplier** for suburbs |
| **Construction Monitor** | Permit leads by market and category, weekly editions | $31–$1,281/mo per market/category; e.g. Dallas all permits $750, Florida South $1,250 [V3] | Subs, suppliers | Permits with builder/owner/contractor contacts | Sold one market at a time; mostly ~6 states [V3] |
| **PermitBoards** | Daily permit digest by county + trade | $79/mo per county+trade; $49 founding [V3] | Small trades | Permits | 31 live markets [V3] |
| **Groundbreak Pro** | Public-record project tracker (permits, deeds, loans, zoning/site-plan cases, sub-permits) | $27/mo all markets [V3] | Subs, suppliers | Public records in 14 cities, 16 states/provinces | Extremely low price anchor |
| **FieldClients** | Permits, violations, new business licenses, certificates of occupancy → accounts for field-service companies | $99 / $249 / $499 per month, monthly [V3] | Field-service sales teams | Public records + verified email | **Closest to this plan's Cluster 2** |
| **ConstructionBids.ai** | Public bid discovery with AI scoring | $59–$99/mo [V3] | Bidders on public work | Public solicitations | Public sector only |
| **BidNet Direct / DemandStar** | Government bid notices | Free to ~$2,699/yr [V3] | Public-sector bidders | Procurement notices | — |
| **Reonomy** | Commercial property ownership, debt, owner contacts | From $400/mo annual [V3] | CRE, vendors to owners | Property records | Owner-side intelligence |
| **PropertyRadar** | Residential lists with distress signals, skip tracing | From $119/mo [V3] | Investors, home-services marketers | Property records | Residential outreach compliance burden falls on the user |
| **MinakiLabs / tunnelapi (Joliet)** | Illinois parcel/permit data incl. FOIA'd monthly permit reports | Subscription [V3] | Local contractors | FOIA + public records | Evidence that suburban permit data often needs FOIA [V3] |

Sources: [Shovels pricing](https://www.shovels.ai/pricing), [Shovels vs Construction Monitor](https://www.shovels.ai/compare/construction-monitor), [Construction Monitor shop](https://shop.constructionmonitor.com/product-category/permit-type/all-permits/), [PermitBoards comparison](https://permitboards.com/compare/construction-monitor/), [Groundbreak 2026 comparison](https://pro.groundbreak.city/guides/construction-lead-services-compared-2026), [FieldClients vs Dodge/ConstructConnect](https://fieldclients.com/vs/dodge-constructconnect/), [Means & Methods Lab: Dodge vs ConstructConnect](https://meansandmethodslab.com/compare/dodge-one-vs-constructconnect), [ConstructionBids.ai alternatives](https://constructionbids.ai/resources/dodge-construction-network-alternatives), [Building Radar pricing](https://www.buildingradar.com/pricing), [Building Radar FAQ](https://buildingradar.com/faqs), [Prospeo on Building Radar](https://prospeo.io/s/building-radar-pricing-reviews-pros-and-cons), [tunnelapi Joliet](https://www.tunnelapi.com/illinois/will-county/joliet/building-permits/).

> Caution: several comparison pages above are published by competitors of the products they describe. Treat their claims about others as leads to verify, not facts.

## Contact data and sales prospecting

| Company | Relevance | Price | Notes |
| --- | --- | --- | --- |
| **Apollo.io** | Contact enrichment (email/phone) for GCs, suppliers, businesses | Free; Basic $49, Professional $79, Organization $119 per seat/mo (annual); 1 credit per verified email, +8 credits per phone [V] | Bounce refunds within 30 days for emails sent via Apollo [V]. Good default for B2B contacts; weak for small trades [H] |
| ZoomInfo, Seamless, Lusha | Same category | Quote / tiered [not verified] | Enterprise-priced [H] |
| Shovels contractor profiles | Contractor contact + work history | Included in credits [V] | Possibly better coverage of small trades than Apollo [H] |

## CRM and agency tooling (integrate, don't build)

| Product | Relevance | Price | Notes |
| --- | --- | --- | --- |
| **HubSpot** | Default CRM for pilots; API on every plan | Free (2 users, 1,000 contacts); Starter $20/seat/mo list (promo $7–$10) [V]; API 100 req/10s, 250k/day on Free/Starter [V] | Easy sync target for opportunities, contacts, tasks |
| **HighLevel (GoHighLevel)** | De-facto agency CRM: sub-account per client, white-label, funnels, reviews, social scheduling, SaaS mode | $97 (3 sub-accounts) / $297 (unlimited, white-label, API) / $497 Founder (SaaS mode, rebilling, advanced API) [V] | Strong candidate as the agency's operating system and the client-facing CRM; our engine pushes opportunities into it |
| ServiceTitan, Jobber, Housecall Pro | Home-services field-management CRMs many trades already use | Not verified | Integrate later where customers already live |

Sources: [Apollo credits](https://www.apollo.io/pricing/about-credits), [Apollo API pricing](https://docs.apollo.io/docs/api-pricing), [HubSpot Starter](https://www.hubspot.com/products/crm/starter), [HubSpot API limits](https://developers.hubspot.com/docs/developer-tooling/platform/usage-guidelines), [HighLevel Founder plan](https://founder.gohighlevel.com/), [CRM Verdict on HighLevel](https://crmverdict.com/gohighlevel-for-agencies/).

## What customers complain about (to verify in interviews)

From the comparison pages and vendor fine print, recurring themes [V3/H]: annual contracts and hard cancellations; per-market × per-seat pricing that punishes small firms; leads that are already awarded or stale; too many irrelevant records; contacts that bounce; tools built for estimators rather than owners. **Each of these is an interview question, not a fact**, until we hear it from at least five target customers.

## Where we can differentiate (and where not to bother)

| Don't rebuild | Why | Do instead |
| --- | --- | --- |
| National permit coverage | Shovels/Construction Monitor/Groundbreak sell it for $27–$999/mo | Own Chicago deeply; buy suburbs/other metros when needed |
| Generic NL search over permits | Shipping at Shovels, Dodge, Building Radar | Internal tool first; customer-facing later on top of *our* entity graph + outcomes |
| A CRM | HubSpot/HighLevel are cheap and good | Sync opportunities into the CRM the customer/agency uses |
| Bid management / takeoff | ConstructConnect, Procore | Out of scope |

| Differentiate on | Evidence it's possible |
| --- | --- |
| GC↔sub relationship graph from resolved entities | Computed from Chicago permit contacts today [V] |
| "Open door" signals: GCs that rotate subs, new GCs entering your size range, subs losing share | Computable from permit history since 2006 [V data exists; H on value] |
| Pre-permit local signals (zoning, plan commission, PDs, public bids) | Requires collection; Shovels "Decisions" may cover some [V that it's sold; H on Chicago coverage] |
| Done-for-you execution + measured meetings/wins | No self-serve feed measures outcomes; Building Radar's managed tier is enterprise-priced [H] |
| One attribution view across inbound ads + outbound intelligence | Requires agency + engine + CRM in one place [H] |

## Potential partners and data licenses

| Partner | Use | Why |
| --- | --- | --- |
| Shovels | Suburban/collar-county permits, contractor profiles, "Decisions" | Avoids building dozens of municipal collectors; $599–$999/mo [V] |
| Apollo (or similar) | Contacts | Pay per verified record; bounce refunds [V] |
| HighLevel | Agency CRM + client portal | Avoids building CRM, reviews, social scheduling, funnels [V features] |
| HubSpot | Pilot CRM sync | Free tier with API [V] |
| Local trade associations / supply houses | Distribution to subs | Trust and access to buyers [H] |
