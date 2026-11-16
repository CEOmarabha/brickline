# Weekly source archive

Some public sources publish only their **current state**: no history, so no backtest is possible on them today.
Starting weekly snapshots now makes the "something changed" signals testable in 6-12 months. Equation numbers
below refer to the strategy matrix in `docs/15-intelligence-engine.md`.

Collector: `engine/collect/archive.py`. It runs after the warehouse sync in `scripts/refresh-data.sh` (a failure
prints a warning and does not abort the refresh) and by hand:

```bash
uv run python -m engine.collect.archive                       # all sources, today's date (UTC)
uv run python -m engine.collect.archive --only fmcsa_chicago_carriers idph_astc
uv run python -m engine.collect.archive --force               # overwrite today's files
uv run python -m engine.collect.archive --diff idph_hospitals 2026-11-16 2026-11-23
```

Run it weekly (the refresh does this Mondays); several runs on one date are harmless, because an existing
`<date>.csv.gz` is never overwritten without `--force`.

## What is archived and which test it enables

| Source (`name`) | What | Future test |
| --- | --- | --- |
| `fmcsa_chicago_carriers` | FMCSA Company Census (data.transportation.gov `az4n-8mr2`), carriers with a Chicago, IL physical address (about 20.7k): DOT number, legal/DBA name, address, status, operation, power units, drivers, MCS-150 date and mileage, new-carrier `add_date`. Phone, email and officer names are deliberately not kept. | **E23**: "carrier added power units" (week-over-week increase in `power_units`/`total_drivers`, a fresh `mcs150_date`, a new `dot_number`) -> fleet-service demand. Measure against follow-on events (new permits or licences at the carrier's address, further growth) once about 6 months of weeks exist. |
| `hfsrb_projects` | Illinois HFSRB project search listing (1,692 CON and exemption projects since 2011): project number, facility, year, Exempted / Non-Exempted, deemed-complete flag. One request, no PDFs. | **E20**: new projects appearing, deemed-complete flips; lead time from "project listed" to a building permit at the facility address. |
| `hfsrb_project_pages` | Fresh copy of each project page for last year's and this year's projects (about 180 requests, about 3 minutes): received date, hearing and comment deadlines, Board meeting date and which documents exist (application, completeness letter, staff report, approval letter). | **E20**: Board-action progress (meeting date set, staff report posted, approval letter posted) -> permit/equipment activity at the facility. Pages are the only place stage dates exist, and the site keeps no change log. |
| `cook_buying_plan` | Cook County Procurement Buying Plan, fiscal year 2026 (`datacatalog.cookcountyil.gov` `cbhc-xvrm`, 164 items): category, department, value band, anticipated advertise quarter, procurement method. | **E24**: plan item -> posted bid (`32au-zaqn` bid tabulations) -> award (`qh8j-6k63`): lead time, how often planned items are bid, repeat winners. A new fiscal year gets a new dataset id: add it as another spec in `archive.py`. |
| `chicago_adu_preapprovals` | Chicago ADU preapproval applications (`data.cityofchicago.org` `j4h8-ug9m`, 616 since 2026-03-31): status, submission and action dates, address, zoning, units allowed and applied for. Applicant and owner names are not kept. | **E22**: status path (Submitted -> Pre-Certified, Canceled, Denied) and time to preapproval; preapproval -> building permit at the address. |
| `idph_hospitals`, `idph_astc` | Illinois IDPH Hospital Directory (207) and Ambulatory Surgical Treatment Center Directory (156), all of Illinois (`illinois-edp.data.socrata.com` `53nt-jwqq`, `79iq-26tb`): licence number, facility, address, licence expiry (and ASTC administrative contact). | **E20**: new or closed facilities, address changes, licence renewals; the facility master list that joins HFSRB projects to permits. |

Filters: FMCSA is limited to `phy_city='CHICAGO' AND phy_state='IL'` (Cook County would be about 58k rows
instead of 20.7k; change the `where` in `archive.py` if the market widens). The IDPH directories are statewide
because the HFSRB projects are. Each source's exact URL, kept fields, key and filter are in `manifest.json`.

## Where the files live

- **Local checkout** (gitignored): `data/archive/<name>/<YYYY-MM-DD>.csv.gz`.
- **Persistent agent store** (survives VM resets): `/cursor/stores/self/brickline-archive/<name>/<YYYY-MM-DD>.csv.gz`.
  The same files can be reached by a future agent at the absolute store id path
  `/cursor/stores/bc-894506b3-f4b4-4377-8cff-355c1fd644e4/brickline-archive` (mounted on first access when the
  agent is authorized; the store id belongs to the agent that started the archive). The collector mirrors each
  new file there when `/cursor/stores/self` exists and is writable, and silently skips it otherwise; override
  the location with `BRICKLINE_ARCHIVE_STORE`. On a fresh VM the next run first copies any store snapshots that
  the checkout lacks back into `data/archive/`.
- **Git** (committed): `research/archive/manifest.json` and this README. Commit the manifest after each run.
  The data files are not committed (`data/` is gitignored), so the store is the only backup: if the store id
  changes, copy `data/archive/` somewhere durable.

## File format and manifest

Files are CSV (header, `\n` line endings, rows sorted by the primary key, numeric keys sorted numerically) in
gzip with `mtime=0` and level 9, so the same response always gives the same bytes. Values are stored exactly as
the source returns them (FMCSA dates are `YYYYMMDD` text, Socrata timestamps are ISO). `manifest.json` lists, per
source, `name`, `description`, `url`, `filter`, `fields`, `key` and `runs`: one entry per run date with `rows`,
`sha256` (of the uncompressed CSV, not the gzip file) and `status` (`ok` or `error: ...`). A failed source adds an
error entry and the run continues (exit code 2 at the end); a failure never replaces an earlier `ok` entry for
the same date. `duplicate_keys` appears on a run when the source itself repeats a key (the diff keeps the last
row for those).

To verify a file: `zcat data/archive/<name>/<date>.csv.gz | sha256sum` equals the manifest's `sha256`.

## Diffing two snapshots

```bash
uv run python -m engine.collect.archive --diff fmcsa_chicago_carriers 2026-11-16 2026-11-23
```

prints counts of added, removed and changed keys, how many keys changed per field, and the first 10 examples. In
code:

```python
from engine.collect.archive import diff_snapshots

d = diff_snapshots("fmcsa_chicago_carriers", "2026-11-16", "2026-11-23")
d["added"]  # keys only in the later snapshot (primary-key values joined with "|")
d["removed"]  # keys only in the earlier snapshot
d["changed"]  # {key: {field: (earlier, later)}}
d["changed_fields"]  # {field: number of keys where it changed}
```

For the "added power units" test: keep `d["changed"]` entries whose `power_units` increased
(`int(later) > int(earlier)`), and treat `added` keys with a recent `add_date` as new carriers.

## Politeness

Descriptive User-Agent (`BricklineResearchBot/0.1 (public-records research; +contact: founder)`), at most one
request per second per host, up to five attempts with exponential backoff on timeouts, 429 and 5xx. The Socrata
endpoints are the portals' documented open APIs (no key); HFSRB requests go through `engine.collect.hfsrb.Fetcher`,
which reads robots.txt first. No authentication, robots.txt rule or CAPTCHA is bypassed.
