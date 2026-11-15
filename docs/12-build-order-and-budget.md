# Build Order, Platform Versions, and First-Six-Months Budget

*v1, 2026-11-14. Labels: [V] verified price, [E] estimate.*

## 1. Two versions of one platform

| | **Client version (Brickline)** — what we sell | **Admin version** — what we run the company on |
| --- | --- | --- |
| Who uses it | Contractors (and later suppliers/subs) | Founders and agency staff |
| Core screens | Dashboard with suggested moves · ranked leads with evidence, chance of work, expected value, outreach draft, status · neighborhoods · market & competitors · commercial preview · settings | All client workspaces · our own sales pipeline · agency work (ads, Google Business Profile, social) and its analytics · data-pipeline health · billing |
| Agency side | A read-only "what the agency did and what it produced" view per client (later) | Where ads and content are actually managed |
| Assistant | Suggested moves now; chat later, once real outcome data exists | Same engine, aimed at our pipeline and client health |
| Data | Same engine and snapshot, filtered to the client's workspace | Everything, across workspaces |

**Decision: build the client version first; the admin version later.** Reasons:

1. The client version is what pilots touch, so it's where we learn what matters (and capture close rates, which the formulas need).
2. It's also our best sales demo. Showing a contractor *their* neighborhood's real leads beats any pitch deck.
3. The admin version mostly wraps tools that already exist (CRM, ads managers, HighLevel). It's worth building once there are enough clients that spreadsheets and HubSpot get painful (roughly 10+).

## 2. Our own lead generation starts now (without the admin app)

We're our own first customer. The engine already knows every active contractor in Chicago:

```bash
uv run python -m engine.leads.prospects --trades porch masonry roofing
# -> data/prospects-<date>.csv (691 contractors doing 3–60 permitted jobs a year)
```

Each row has jobs in the last 12 months vs the prior 12, typical job size, last job date, neighborhoods, and **how many violation-driven jobs they already win**, which signals they'd value faster leads. Columns for website, phone, email, contact and status are left blank for research; nothing is guessed.

Until the admin app exists: import the CSV into HubSpot's free CRM (or a sheet), research contacts, and track outreach there. The admin version later replaces this with the same lead/pipeline screens contractors use, pointed at our own market.

## 3. First six months: costs [E unless marked]

Assumes founder-led building with AI tools, Chicago only, a handful of pilots.

| Item | Monthly | 6 months | Notes |
| --- | --- | --- | --- |
| App hosting + database | ~$0–$50 | ~$0–$300 | Depends on the host's pricing for the published app and its Postgres |
| Domain + business email (Google Workspace or similar) | ~$10–$20 | ~$60–$120 | Plus a separate domain for cold email so the main domain's reputation stays clean |
| Cold-email sending/warm-up tool | ~$30–$50 | ~$180–$300 | Needed before emailing hundreds of contractors |
| Contact data (Apollo Basic) | $49/seat [V, annual] | ~$300 | ~2,500 credits/month; email ≈ 1 credit |
| CRM | $0 | $0 | HubSpot free [V] |
| Phone line (VoIP number) | ~$15–$20 | ~$100 | Business line for calls and callbacks |
| AI APIs (drafting, later the assistant) | ~$10–$50 | ~$60–$300 | Cheap at one-city scale (see `04-feasibility-assessment.md` §4.1) |
| Our own direct-mail test (to prove the letters work) | — | ~$300–$600 | ~300–500 letters with tracking; clients pay their own postage after that |
| LLC formation + basic legal review of outreach templates/terms | — | ~$500–$1,500 | One-time; worth it before agency outreach scales |
| Optional: general liability / E&O insurance | ~$50–$100 | ~$300–$600 | Recommended once clients pay |
| **Total** | | **≈ $1,800–$4,100** | Fits "a few thousand"; the high end includes legal and insurance |

Not included: your time, a Cursor subscription, and paid ads for the agency side (which clients fund).

**Reinvestment order once revenue starts:** (1) more contact data and mail capacity for clients, (2) a part-time researcher/VA to prepare leads and contacts (~$15–$25/hour), (3) suburban data (Shovels $599+/month [V]) only when a paying client needs it, (4) the admin version.

## 4. What gets built next (in order)

1. Deliver to pilots: weekly snapshot refresh, outreach drafts, statuses → measure close rate per signal.
2. Client accounts: client sign-in that isn't tied to Cursor, workspace per client, and an invite link.
3. Scheduled data refresh (daily collector instead of manual sync).
4. Assistant chat over the client's own leads and pipeline (tool-calling over the same data; numbers from the database, never invented).
5. Agency view in the client app (read-only campaign results), then the admin version.
