# Daily event-lead scanner

Daily collection of upcoming event leads for Chicagoland, Milwaukee / SE Wisconsin, and NW Indiana. Output is a JSON snapshot (`web/data/event-leads.json`), a 7 AM America/Chicago digest (`web/data/event-digest.json`), the `/events?tab=scanner` list, and `/events/digest`. Outreach is still one message at a time from a real account; this job does not send DMs, emails, or texts.

## How to run

From the repository root:

```bash
# Public calendars only (no Facebook / Instagram / TikTok sessions)
python -m engine.leads.event_scan --public-only --no-llm

# Full run: public + listings + social (sessions/tokens if configured)
python -m engine.leads.event_scan

# Dual UTC cron helper: no-op unless the local Chicago clock is 07:00
python -m engine.leads.event_scan --require-chicago-hour
```

`scripts/daily-event-scan.sh` wraps the same command. GitHub Actions (`.github/workflows/event-scan.yml`) fires at 12:00 and 13:00 UTC with `--require-chicago-hour` so only the 7 AM America/Chicago slot writes a digest (CST = UTC−6, CDT = UTC−5).

Optional Postgres: set `DATABASE_URL` and apply `web/migrations/009_event_leads.sql`. The Python job upserts rows and leaves `review_status` alone; `web/scripts/upsert-event-leads.mjs` can load the JSON when Python has no `psycopg`. Review status in the Events UI writes to that table and is overlaid on the next scan.

## Public sources (no login)

| Source | How | Notes |
| --- | --- | --- |
| Chicago Park District `pk66-w54g` | Socrata. `$select` omits requestor names. Includes Tentative / Waiting Decision / On Hold plus every upcoming wedding and social venue rental. | Same privacy rule as the warehouse. |
| Chicago DCASE special events `xgse-8eg7` | Socrata map dataset (no applicant names). | `knv6-r5ad` is stale (ends 2017) and includes requestor; do not select it. |
| Choose Chicago, Visit Milwaukee, South Shore CVA | Public RSS. | robots.txt allowed on 2026-11-25. |
| CDOT street events | Local DuckDB warehouse when present. | Skipped if `data/warehouse.duckdb` is missing. |
| Milwaukee special-event *permits* | **Not scraped.** | No open dataset. `city.milwaukee.gov` calendar is Cloudflare 403. Wisconsin public-records request: DPW Special Events, (414) 286-3915. |
| McCormick Place calendar | **Not scraped.** | SiteGround captcha (HTTP 202) / Ungerboeck 500. Copy by hand or a licensed fetch that already passed the interstitial. No captcha solver. |
| Eventbrite / Meetup / Luma / AllEvents | Public feeds, official APIs, or licensed providers. | See env vars below. |
| Reddit | Official OAuth only (`REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`). | `reddit.com/robots.txt` disallows anonymous crawl. |
| X | Bearer token, SerpApi, or Apify. | No anonymous crawl. |

## Authenticated Facebook, Instagram, TikTok

Omar accepted the account risk: collectors log in as **the team's own real accounts**, never newly created fakes. There is no captcha-solving service and no account-creation automation.

Two runtimes, tried in order:

1. **Playwright** with stored `storage_state` (preferred) or exported cookies converted to `storage_state`.
2. **Apify** actors that accept a cookie header (`APIFY_TOKEN` plus optional `APIFY_*_ACTOR` overrides).

If the page looks like a login wall or checkpoint, the collector raises `SessionExpired`, records `status: session_expired` in the scan notes, and does not keep hammering that account.

### Export session cookies (do this on a trusted machine)

Never commit the files. `secrets/`, `*.storage.json`, `*.cookies.json`, and `event-scanner.env` are gitignored.

**Option A — Playwright (recommended)**

```bash
pip install playwright
playwright install chromium
python -m engine.collect.social.save_session facebook
python -m engine.collect.social.save_session instagram
python -m engine.collect.social.save_session tiktok
```

A headed browser opens. Log in yourself. When you see the logged-in home feed, return to the terminal and press Enter. That writes `secrets/<platform>.storage.json`.

**Option B — Cookie-Editor (or similar) browser extension**

1. Log into facebook.com / instagram.com / tiktok.com in the browser you already use.
2. Export cookies as JSON (Cookie-Editor → Export → JSON) or Netscape `cookies.txt`.
3. Save as `secrets/facebook.cookies.json` (or `.txt`). Repeat for `instagram` and `tiktok`.

**Option C — cookie header in env (least preferred; easy to leak in logs)**

Set `FB_COOKIE`, `IG_COOKIE`, `TIKTOK_COOKIE` to the `Cookie` request header string. Do not print these values.

Copy `event-scanner.env.example` to `secrets/event-scanner.env` (gitignored) and fill paths:

```
FB_STORAGE_STATE=secrets/facebook.storage.json
IG_STORAGE_STATE=secrets/instagram.storage.json
TIKTOK_STORAGE_STATE=secrets/tiktok.storage.json
FB_GROUP_URLS=https://www.facebook.com/groups/your-joined-group
```

Facebook visits Events, Events discovery, the joined-groups feed (`/groups/?category=membership` and `/groups/feed/`), keyword event/group/post search for the three regions, and any `FB_GROUP_URLS` the team adds (public *and* groups those accounts already joined). Instagram uses hashtags plus `IG_PROFILE_URLS`. TikTok uses tags plus search.

### Rate limits (so accounts are not banned)

Defaults (overridable per account):

| Account | Delay | Max / run | Max / hour |
| --- | --- | --- | --- |
| Facebook | 15–32 s jitter | 18 | 40 |
| Instagram | 12–28 s | 16 | 36 |
| TikTok | 12–30 s | 14 | 32 |

Env overrides: `FB_MIN_DELAY`, `FB_MAX_DELAY`, `FB_MAX_PER_RUN`, `FB_MAX_PER_HOUR` (and `IG_*`, `TIKTOK_*`). A request log lives in gitignored `data/raw/social_throttle.json`. First-run URL lists are capped (~20 Facebook pages).

When a session expires, re-export cookies with Option A or B. Do not loop the headed login from cron.

## Other env vars

| Variable | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` | Optional strict-JSON extract (never invents contacts). `--no-llm` skips it. |
| `ASSISTANT_MODEL` | Anthropic model id (default `claude-sonnet-5-5`). |
| `DATABASE_URL` | Postgres upsert of `event_lead`. |
| `APIFY_TOKEN` | Licensed Apify actors (events, IG, TikTok, Eventbrite, …). |
| `APIFY_FACEBOOK_ACTOR` / `APIFY_INSTAGRAM_ACTOR` / `APIFY_TIKTOK_ACTOR` | Override default actor ids. |
| `SERPAPI_API_KEY` | Google Events and related engines. |
| `FIRECRAWL_API_KEY` | Licensed page fetch (Luma/AllEvents fallback). |
| `EVENTBRITE_TOKEN` | Official Eventbrite API. |
| `MEETUP_TOKEN` | Official Meetup API. |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | Reddit OAuth. |
| `X_BEARER_TOKEN` | X API. |
| `EVENT_ICAL_URLS` | Comma-separated extra iCal URLs. |
| `EVENT_SCAN_SECRETS_DIR` | Override `secrets/`. |

## Pipeline

1. Collect raw items (public HTTPS, then social if not `--public-only`).
2. Geo-fence the three regions. Drop social posts with no place.
3. Rule extract (name, date, venue, size, vendor-need tags, evidence quote). Optional Anthropic JSON; phones/emails are stripped.
4. Fuzzy dedup on name + date + venue.
5. Score: recency, 2–8 week notice window, size, vendor-need, contactability.
6. Merge with the previous snapshot (`item_hash` stable; `first_seen` / `last_seen`; `content_hash` change detection; keep `review_status`).
7. Write JSON + digest. Upsert Postgres when configured.

## What this does not do

- Create fake accounts or farm sessions.
- Solve captchas.
- Send DMs, comments, follows, emails, or SMS.
- Store requestor names from Park District Socrata.
- Put personal phones/emails in `web/data/*.json`.
