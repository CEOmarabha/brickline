"""Free contact enrichment: public business contact details for prospects and company property owners.

    uv run python -m engine.enrich.contacts                # match, crawl company websites (cached 30 days), write
    uv run python -m engine.enrich.contacts --no-web       # skip website crawling (use cached results only)

Inputs: web/data/prospects.json, web/data/snapshot.json, and the warehouse tables `places` (Overture Maps),
`biz_licenses` and `biz_owners` (City of Chicago), `contractor_registry` (Illinois CDB vendors, IDPH lead and
asbestos contractors) and `foreclosed_rentals` (City of Chicago registry). Outputs: web/data/contacts.json (the app's suggestions),
data/contacts-<date>.csv (inspection) and research/findings/contact-enrichment-<date>.md (match rates).

Everything is a suggestion with its source, a match confidence and a retrieval date. Nothing is guessed: no
email patterns, no personal social profiles. A match is kept only at medium or high confidence. Social links are
the business pages Overture lists for a matched business, never a person's profile. Lead-level suggestions
(by property or mailing address) are kept only for company owners and company agents: contacts.json ships with
the app, so it must not carry a private person's phone or email.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path

from engine import db
from engine.db import RAW
from engine.enrich import web
from engine.enrich.names import distinctive, normalize, token_set_ratio
from engine.score.signals import INVESTOR_RE
from engine.text import title
from engine.warehouse import address_key_sql

PROSPECTS = Path("web/data/prospects.json")
SNAPSHOT = Path("web/data/snapshot.json")
JSON_OUT = Path("web/data/contacts.json")
WEB_CACHE = RAW / "web_contacts"
FINDINGS = Path("research/findings")

OVERTURE = "overture"
LICENSES = "chicago_business_licenses"
WEBSITE = "company_website"
CDB = "cdb_vendors"
IDPH_LEAD = "idph_lead_contractors"
IDPH_ASBESTOS = "idph_asbestos_contractors"
FORECLOSED = "foreclosed_rental_registry"
AT_MAILING = "overture_at_mailing_address"
REGISTRIES = (CDB, IDPH_LEAD, IDPH_ASBESTOS)
SOURCE_LABELS = {
    OVERTURE: "Overture Maps",
    LICENSES: "Chicago business licenses",
    WEBSITE: "Company website",
    CDB: "Illinois Capital Development Board vendors",
    IDPH_LEAD: "IDPH lead contractor registry",
    IDPH_ASBESTOS: "IDPH asbestos contractor registry",
    FORECLOSED: "Chicago foreclosed rental registry",
    AT_MAILING: "Overture Maps listing at this mailing address",
}
SOURCE_URLS = {
    CDB: "https://illinois-edp.data.socrata.com/d/3dh9-yktq",
    IDPH_LEAD: "https://illinois-edp.data.socrata.com/d/vpwp-h7xr",
    IDPH_ASBESTOS: "https://illinois-edp.data.socrata.com/d/kt5u-9dcu",
    FORECLOSED: "https://data.cityofchicago.org/d/yhcw-iu53",
}
SOURCE_ORDER = [OVERTURE, LICENSES, CDB, IDPH_LEAD, IDPH_ASBESTOS, FORECLOSED, AT_MAILING, WEBSITE]
COMPANY_RE = re.compile(INVESTOR_RE)
# Business pages only: personal-profile URL shapes are dropped even when a business listing carries them.
PERSONAL_SOCIAL = re.compile(r"linkedin\.com/in/|facebook\.com/(people|profile\.php)|/groups/", re.I)
SOCIAL_HOSTS = (
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "tiktok.com",
)
FORECLOSED_MAX_AGE_DAYS = 3 * 365
RANK = {"high": 2, "medium": 1, "low": 0}
FUZZY_MIN = 0.9
TRUNCATED_LEN = 29  # permit party names are cut at 30 characters
PAIR_MIN = 0.85
MIN_FUZZY_TOKEN = 5  # differing words must be long enough that one typo cannot turn one word into another

TRADE_GROUPS = {
    "porch": {"porch", "masonry", "generic"},
    "masonry": {"masonry", "generic"},
    "roofing": {"roofing", "generic"},
    "plumbing": {"plumbing", "hvac", "generic"},
    "electrical": {"electrical", "hvac", "generic"},
}
NOT_CONTRACTOR = re.compile(
    r"supply|store|supplier|wholesale|utility|equipment|rental|dealer|manufactur|school|training"
)
CATEGORY_KINDS = (
    ("roofing", re.compile(r"roof")),
    ("plumbing", re.compile(r"plumb|sewer|drain")),
    ("electrical", re.compile(r"electric")),
    ("masonry", re.compile(r"mason|concrete|brick|stone|tuckpoint|waterproof|foundation|chimney")),
    ("hvac", re.compile(r"hvac|heating|air_cond")),
    ("porch", re.compile(r"carpent|deck|fenc|porch|woodwork|siding")),
    (
        "generic",
        re.compile(
            r"contractor|construction|building|remodel|handyman|home_improvement|general|restoration|renovat"
        ),
    ),
)
OWNER_TITLE_ORDER = [
    "OWNER", "SOLE PROPRIETOR", "PRESIDENT", "CEO", "MANAGING MEMBER", "MANAGER", "MEMBER", "PARTNER",
    "GENERAL PARTNER", "VICE PRESIDENT", "INDIVIDUAL",
]  # fmt: skip
CONTRACTOR_ACTIVITY = re.compile(r"CONTRACT|CONSTRUCT|ROOF|PLUMB|ELECTR|MASON|BUILD|REMODEL|TUCKPOINT")


def category_kind(cat: str | None) -> str | None:
    c = (cat or "").lower()
    if not c or NOT_CONTRACTOR.search(c):
        return None
    for kind, rx in CATEGORY_KINDS:
        if rx.search(c):
            return kind
    return None


@dataclass
class Entity:
    kind: str  # prospect | owner
    id: str
    name: str
    key: str
    trade: str | None = None
    areas: list[int] = field(default_factory=list)
    zips: set[str] = field(default_factory=set)
    leads: list[str] = field(default_factory=list)
    best_fit: bool = False
    truncated: bool = False


@dataclass
class PlaceMatch:
    method: str
    confidence: str
    places: list[dict]
    in_chicago: bool
    category_ok: bool


@dataclass
class LicenseMatch:
    method: str
    confidence: str
    account: str
    rows: list[dict]
    owners: list[dict]


def zip_of(text: str | None) -> str | None:
    m = re.search(r"\b(\d{5})(?:-\d{4})?\s*$", text or "")
    return m.group(1) if m else None


def retrieved(path: Path, fallback: str) -> str:
    """Date a raw file was downloaded; `fallback` when the raw pages are not on this machine."""
    if not path.exists():
        return fallback
    return datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()


# ----------------------------------------------------------------------------------------------------------
# Entities
# ----------------------------------------------------------------------------------------------------------
def load_entities(prospects_path: Path, snapshot_path: Path) -> tuple[list[Entity], list[Entity], str]:
    file = json.loads(prospects_path.read_text())
    prospects = []
    for p in file["prospects"]:
        best = p["violationDrivenJobs"] > 0 and 5 <= p["jobs12m"] <= 40
        prospects.append(
            Entity(
                "prospect",
                p["id"],
                p["company"],
                normalize(p["company"]),
                p["trade"],
                p["areaIds"],
                best_fit=best,
                truncated=len(p["company"]) >= TRUNCATED_LEN,
            )
        )
    snap = json.loads(snapshot_path.read_text())
    owners: dict[str, Entity] = {}
    for lead in snap["leads"]:
        names = []
        if lead["owner"]["type"] == "company" and lead["owner"].get("name"):
            names.append(lead["owner"]["name"])
        if lead["kind"] == "investor_purchase" and lead["buyer"].get("name"):
            names.append(lead["buyer"]["name"])
        for name in names:
            key = normalize(name)
            if not key:
                continue
            e = owners.setdefault(key, Entity("owner", key, name, key))
            if lead["id"] not in e.leads:
                e.leads.append(lead["id"])
            z = zip_of((lead["owner"] or {}).get("mailing"))
            if z and name == lead["owner"].get("name"):
                e.zips.add(z)
    return prospects, sorted(owners.values(), key=lambda e: e.key), file["generatedFor"]


# ----------------------------------------------------------------------------------------------------------
# Overture places
# ----------------------------------------------------------------------------------------------------------
def words_pair_up(a: set[str], b: set[str]) -> bool:
    """Every differing word on one side has a clearly similar, long-enough partner on the other (typos, plurals)."""
    if len(a) != len(b):
        return False
    left = sorted(a)
    right = sorted(b)
    for t in left:
        best = max(right, key=lambda u: SequenceMatcher(None, t, u).ratio(), default=None)
        if best is None or min(len(t), len(best)) < MIN_FUZZY_TOKEN or t.isdigit() or best.isdigit():
            return False
        if SequenceMatcher(None, t, best).ratio() < PAIR_MIN:
            return False
        right.remove(best)
    return True


class PlaceIndex:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.exact: dict[str, list[int]] = defaultdict(list)
        self.tokens: dict[str, list[int]] = defaultdict(list)
        for i, r in enumerate(rows):
            r["key"] = key = normalize(r["name"])
            if not key:
                continue
            self.exact[key].append(i)
            for t in set(distinctive(key)):
                self.tokens[t].append(i)

    def fuzzy(self, key: str) -> list[int]:
        toks = set(distinctive(key))
        counts: Counter[int] = Counter()
        for t in toks:
            posting = self.tokens.get(t, ())
            if len(posting) <= 5000:
                counts.update(posting)
        need = max(1, (len(toks) + 1) // 2)
        out = []
        for i, n in sorted(counts.items()):
            if n < need:
                continue
            other = self.rows[i]["key"]
            if token_set_ratio(key, other) < FUZZY_MIN:
                continue
            if words_pair_up(set(key.split()) - set(other.split()), set(other.split()) - set(key.split())):
                out.append(i)
        return out

    def truncated(self, key: str) -> list[int]:
        """Places whose name starts with `key`: permit contractor names are cut at 30 characters."""
        toks = distinctive(key)
        if len(key.split()) < 3 or not toks:
            return []
        rare = min(toks[:-1] or toks, key=lambda t: len(self.tokens.get(t, ())))
        return [
            i
            for i in self.tokens.get(rare, ())
            if len(self.rows[i]["key"]) > len(key) and self.rows[i]["key"].startswith(key)
        ]


def load_places(con) -> list[dict]:
    cur = con.execute(f"""
        SELECT id, name, category, categories, phones, websites, emails, socials, address, locality, postcode,
            region, confidence, status, lat, lon, in_chicago, release, {address_key_sql("address")} AS address_key
        FROM places WHERE status IS DISTINCT FROM 'permanently_closed' ORDER BY id
    """)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def place_identity(p: dict) -> str:
    """Two listings with the same website host or phone are the same business."""
    for w in p["websites"] or []:
        site = web.clean_website(w)
        if site:
            return web.base_host(web.host_of(site))
    for ph in p["phones"] or []:
        n = web.normalize_us_phone(ph)
        if n:
            return n
    return p["id"]


def match_place(e: Entity, idx: PlaceIndex, drops: Counter) -> PlaceMatch | None:
    if len(e.key.split()) < 2 and e.kind == "owner":
        drops["overture: one-word owner name"] += 1
        return None
    method, hits = "exact_name", idx.exact.get(e.key, [])
    if not hits and len(e.key.split()) >= 2:
        method, hits = "token_set", idx.fuzzy(e.key)
    if not hits and e.truncated:
        method, hits = "truncated_name", idx.truncated(e.key)
    if not hits:
        drops["overture: no candidate"] += 1
        return None
    cands = []
    for i in hits:
        p = idx.rows[i]
        cats = [p["category"], *(p["categories"] or [])]
        kinds = {category_kind(c) for c in cats if c}
        if e.trade and p["category"] is not None:
            if not (kinds & TRADE_GROUPS[e.trade]):
                continue
            explicit = True
        else:
            explicit = False
        cands.append((p, explicit))
    if not cands:
        drops["overture: category not trade-compatible"] += 1
        return None
    in_city = [c for c in cands if c[0]["in_chicago"]]
    pool = in_city or cands
    if len({place_identity(p) for p, _ in pool}) > 1:
        drops["overture: ambiguous (several businesses share the name)"] += 1
        return None
    pool.sort(
        key=lambda c: (
            not c[1],
            not c[0]["websites"],
            not c[0]["phones"],
            -(c[0]["confidence"] or 0),
            c[0]["id"],
        )
    )
    best, explicit = pool[0]
    chicago = bool(in_city)
    zip_ok = bool(e.zips and (best["postcode"] or "")[:5] in e.zips)
    if e.kind == "prospect":
        if method == "exact_name":
            conf = "high" if explicit and chicago else "medium"
        elif method == "truncated_name":
            conf = "medium" if explicit else "low"
        else:
            conf = "medium" if explicit and chicago else "low"
    elif method == "exact_name":
        conf = "high" if chicago and zip_ok else "medium" if chicago or zip_ok else "low"
    else:
        conf = "medium" if chicago and zip_ok else "low"
    if conf == "low":
        drops["overture: low confidence"] += 1
        return None
    return PlaceMatch(method, conf, [p for p, _ in pool], chicago, explicit)


# ----------------------------------------------------------------------------------------------------------
# Chicago business licenses and owners
# ----------------------------------------------------------------------------------------------------------
class LicenseIndex:
    def __init__(self, con) -> None:
        cur = con.execute("""
            SELECT account_number, site_number, legal_name, dba, address, zip, community_area,
                license_description, business_activity, license_id
            FROM biz_licenses ORDER BY account_number, site_number, license_id
        """)
        cols = [c[0] for c in cur.description]
        self.by_key: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        for row in cur.fetchall():
            r = dict(zip(cols, row, strict=True))
            for name in (r["legal_name"], r["dba"]):
                k = normalize(name)
                if k and r not in self.by_key[k][r["account_number"]]:
                    self.by_key[k][r["account_number"]].append(r)
        cur = con.execute("""
            SELECT account_number, first_name, middle, last_name, suffix, title
            FROM biz_owners WHERE last_name IS NOT NULL
            ORDER BY account_number, last_name, first_name, middle, title
        """)
        cols = [c[0] for c in cur.description]
        self.owners: dict[str, list[dict]] = defaultdict(list)
        for row in cur.fetchall():
            r = dict(zip(cols, row, strict=True))
            self.owners[r["account_number"]].append(r)

    def match(self, e: Entity, drops: Counter) -> LicenseMatch | None:
        if len(e.key.split()) < 2:
            drops["licenses: one-word name"] += 1
            return None
        accounts = self.by_key.get(e.key)
        if not accounts:
            drops["licenses: no candidate"] += 1
            return None

        def corroborated(rows: list[dict]) -> bool:
            if e.kind == "prospect" and any(
                r["community_area"] and int(r["community_area"]) in e.areas for r in rows
            ):
                return True
            if e.zips and any((r["zip"] or "")[:5] in e.zips for r in rows):
                return True
            return e.kind == "prospect" and any(
                CONTRACTOR_ACTIVITY.search(f"{r['license_description']} {r['business_activity']}".upper())
                for r in rows
            )

        good = {a: rows for a, rows in accounts.items() if corroborated(rows)}
        if len(accounts) == 1:
            account, rows = next(iter(accounts.items()))
            conf = "high" if good else "medium"
        elif len(good) == 1:
            account, rows = next(iter(good.items()))
            conf = "high"
        else:
            drops["licenses: ambiguous (several accounts share the name)"] += 1
            return None
        return LicenseMatch("exact_name", conf, account, rows, self.owners.get(account, []))


def pick_owner(owners: list[dict]) -> dict | None:
    ranked = []
    for o in owners:
        t = (o["title"] or "").upper()
        if t in OWNER_TITLE_ORDER:
            ranked.append((OWNER_TITLE_ORDER.index(t), o))
    return min(ranked, key=lambda x: x[0], default=(0, None))[1]


def person_name(o: dict) -> str:
    parts = [o["first_name"], o["middle"], o["last_name"], o["suffix"]]
    name = " ".join(p.strip() for p in parts if p and p.strip())
    return title(name) if name.isupper() else name


# ----------------------------------------------------------------------------------------------------------
# Assembling suggestions
# ----------------------------------------------------------------------------------------------------------
def field_value(
    value: str, source: str, confidence: str, retrieved_at: str, url: str | None = None, **extra
) -> dict:
    return {
        "value": value, "source": source, "sourceUrl": url, "confidence": confidence, "retrievedAt": retrieved_at,
        **extra,
    }  # fmt: skip


def plain_email_ok(email: str) -> bool:
    local, _, domain = email.partition("@")
    if not local or "." not in domain or web.IMAGE_EXT.search(email) or web.BAD_LOCAL.match(local):
        return False
    return not any(domain == d or domain.endswith("." + d) for d in web.BAD_EMAIL_DOMAINS)


def order_values(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda f: (-RANK[f["confidence"]], SOURCE_ORDER.index(f["source"]), f["value"]))


def business_social(url: str | None) -> str | None:
    """A social-media link that is a business page (as listed by Overture for a business), else None."""
    if not url:
        return None
    url = url.strip()
    host = web.base_host(web.host_of(url))
    if not any(host == h or host.endswith("." + h) for h in SOCIAL_HOSTS) or PERSONAL_SOCIAL.search(url):
        return None
    return url


# ----------------------------------------------------------------------------------------------------------
# Contractor registries (prospects) and address-based suggestions (leads)
# ----------------------------------------------------------------------------------------------------------
class RegistryIndex:
    """State contractor registries by exact normalized name. A name listed with different phones is dropped."""

    def __init__(self, con) -> None:
        cur = con.execute("""
            SELECT registry, registry_id, name, city, state, phone, email, expires FROM contractor_registry
            WHERE phone IS NOT NULL OR email IS NOT NULL ORDER BY registry, name, registry_id
        """)
        cols = [c[0] for c in cur.description]
        self.by_key: dict[str, list[dict]] = defaultdict(list)
        self.rows = 0
        for row in cur.fetchall():
            r = dict(zip(cols, row, strict=True))
            self.rows += 1
            k = normalize(r["name"])
            if k:
                self.by_key[k].append(r)

    def match(self, e: Entity, drops: Counter) -> list[dict]:
        if len(e.key.split()) < 2:
            return []
        rows = self.by_key.get(e.key, [])
        phones = {web.normalize_us_phone(r["phone"] or "") for r in rows} - {None}
        if len(phones) > 1:
            drops["registries: ambiguous (one name, several phones)"] += 1
            return []
        return rows


def lead_suggestions(con, snap: dict, places: list[dict], stamps: dict[str, str], drops: Counter) -> dict:
    """Per-lead suggestions found by address, for company owners only.

    - Foreclosed rental registry: the notices agent of a registration at the lead's property, when the agent is
      a company (registered within FORECLOSED_MAX_AGE_DAYS of the newest registration).
    - Overture at the mailing address: the one business Overture lists at a company owner's mailing address
      (dropped when several businesses share the building). The business there may not be the owner.
    """
    rows = [
        (lead["id"], lead["address"], (lead["owner"] or {}).get("mailing"))
        for lead in snap["leads"]
        if (lead["owner"] or {}).get("type") == "company"
    ]
    con.execute("CREATE OR REPLACE TEMP TABLE lead_addr (id VARCHAR, address VARCHAR, mailing VARCHAR)")
    con.executemany("INSERT INTO lead_addr VALUES (?, ?, ?)", rows)
    keyed = con.execute(f"""
        SELECT id, {address_key_sql("address")} AS prop_key,
            CASE WHEN mailing IS NOT NULL THEN {address_key_sql("mailing")} END AS mail_key
        FROM lead_addr ORDER BY id
    """).fetchall()
    cur = con.execute("""
        SELECT registration_id, address_key, submitted_date, agent_name, manager_name, agent_phone, agent_email
        FROM foreclosed_rentals
        WHERE submitted_date >= (SELECT max(submitted_date) FROM foreclosed_rentals) - INTERVAL 1095 DAY
        ORDER BY address_key, submitted_date DESC, registration_id
    """)
    cols = [c[0] for c in cur.description]
    foreclosed: dict[str, dict] = {}
    for row in cur.fetchall():
        r = dict(zip(cols, row, strict=True))
        foreclosed.setdefault(r["address_key"], r)
    at_addr: dict[str, list[dict]] = defaultdict(list)
    for p in places:
        if p["address_key"] and p["in_chicago"] is not None:
            at_addr[p["address_key"]].append(p)

    out: dict[str, dict] = {}
    for lead_id, prop_key, mail_key in keyed:
        phones: list[dict] = []
        emails: list[dict] = []
        name = None
        matches = []
        website = None
        socials: list[dict] = []
        reg = foreclosed.get(prop_key)
        if reg:
            agent = reg["agent_name"] or ""
            if not COMPANY_RE.search(agent.upper()):
                drops["foreclosed registry: agent is not a company (not shipped)"] += 1
            else:
                when = reg["submitted_date"].isoformat()
                url = (
                    f"{SOURCE_URLS[FORECLOSED].replace('/d/', '/resource/')}.json?id={reg['registration_id']}"
                )
                n = web.normalize_us_phone(reg["agent_phone"] or "")
                if n:
                    phones.append(field_value(n, FORECLOSED, "high", when, url=url))
                if reg["agent_email"] and plain_email_ok(reg["agent_email"]):
                    emails.append(field_value(reg["agent_email"], FORECLOSED, "high", when, url=url))
                if phones or emails:
                    name = title(agent)
                    matches.append({"source": FORECLOSED, "method": "property_address", "confidence": "high"})
        listed = at_addr.get(mail_key) if mail_key and mail_key != prop_key else None
        if listed:
            if len({place_identity(p) for p in listed}) > 1:
                drops["mailing address: several businesses listed there"] += 1
            else:
                when = stamps[OVERTURE]
                p = listed[0]
                for ph in p["phones"] or []:
                    if n := web.normalize_us_phone(ph):
                        phones.append(field_value(n, AT_MAILING, "medium", when, listing=p["name"]))
                for em in p["emails"] or []:
                    if plain_email_ok(em := em.strip().lower()):
                        emails.append(field_value(em, AT_MAILING, "medium", when, listing=p["name"]))
                for w in p["websites"] or []:
                    if (site := web.clean_website(w)) and website is None:
                        website = field_value(site, AT_MAILING, "medium", when, url=site, listing=p["name"])
                for u in p["socials"] or []:
                    if link := business_social(u):
                        socials.append(
                            field_value(link, AT_MAILING, "medium", when, url=link, listing=p["name"])
                        )
                if phones or emails or website:
                    name = name or p["name"]
                    matches.append(
                        {"source": AT_MAILING, "method": "mailing_address", "confidence": "medium"}
                    )
        if matches:
            out[lead_id] = {
                "name": name,
                "website": website,
                "phones": merge_values(phones),
                "emails": merge_values(emails),
                "socials": merge_values(socials),
                "contactName": None,
                "address": None,
                "matches": matches,
            }
    return out


def merge_values(items: list[dict]) -> list[dict]:
    """One entry per value; a value seen in two sources gets `alsoFoundIn` and, for phones and emails, high."""
    by_value: dict[str, dict] = {}
    for f in items:
        key = f["value"].lower()
        have = by_value.get(key)
        if have is None:
            by_value[key] = dict(f)
        elif f["source"] != have["source"]:
            have.setdefault("alsoFoundIn", []).append(f["source"])
            have["confidence"] = (
                "high" if RANK[have["confidence"]] and RANK[f["confidence"]] else have["confidence"]
            )
    return order_values(list(by_value.values()))


def assemble(
    e: Entity,
    pm: PlaceMatch | None,
    lm: LicenseMatch | None,
    crawl: dict | None,
    stamps: dict[str, str],
    registry_rows: list[dict] | None = None,
) -> dict | None:
    website = None
    phones: list[dict] = []
    emails: list[dict] = []
    socials: list[dict] = []
    contact = None
    address = None
    matches = []
    if pm:
        matches.append({"source": OVERTURE, "method": pm.method, "confidence": pm.confidence})
        when = stamps[OVERTURE]
        for p in pm.places:
            for w in p["websites"] or []:
                site = web.clean_website(w)
                if site and website is None:
                    website = field_value(site, OVERTURE, pm.confidence, when, url=site)
            for ph in p["phones"] or []:
                n = web.normalize_us_phone(ph)
                if n:
                    phones.append(field_value(n, OVERTURE, pm.confidence, when))
            for em in p["emails"] or []:
                em = em.strip().lower()
                if plain_email_ok(em):
                    emails.append(field_value(em, OVERTURE, pm.confidence, when))
            for u in p["socials"] or []:
                if link := business_social(u):
                    socials.append(field_value(link, OVERTURE, pm.confidence, when, url=link))
        best = pm.places[0]
        if best["address"]:
            parts = [
                best["address"],
                best["locality"],
                f"{best['region'] or ''} {best['postcode'] or ''}".strip(),
            ]
            address = field_value(", ".join(p for p in parts if p), OVERTURE, pm.confidence, when)
    if lm:
        matches.append({"source": LICENSES, "method": lm.method, "confidence": lm.confidence})
        when = stamps[LICENSES]
        row = lm.rows[0]
        if row["address"]:
            lic_addr = f"{title(row['address'])}, Chicago IL {row['zip'] or ''}".strip()
            url = f"https://data.cityofchicago.org/resource/uupf-x98q.json?account_number={lm.account}"
            address = field_value(lic_addr, LICENSES, lm.confidence, when, url=url)
        owner = pick_owner(lm.owners)
        if owner:
            url = f"https://data.cityofchicago.org/resource/ezma-pppn.json?account_number={lm.account}"
            contact = field_value(
                person_name(owner), LICENSES, lm.confidence, when, url=url, title=title(owner["title"] or "")
            )
    for r in registry_rows or []:
        src = r["registry"]
        url = SOURCE_URLS[src]
        when = stamps[src]
        if n := web.normalize_us_phone(r["phone"] or ""):
            phones.append(field_value(n, src, "medium", when, url=url))
        if r["email"] and plain_email_ok(r["email"]):
            emails.append(field_value(r["email"], src, "medium", when, url=url))
    if registry_rows:
        matches.append(
            {"source": registry_rows[0]["registry"], "method": "exact_name", "confidence": "medium"}
        )
    if crawl and website and crawl["status"] == "ok":
        site_conf = website["confidence"]
        for em in crawl["emails"]:
            own = web.base_host(crawl["host"]) in em["value"].partition("@")[2]
            conf = site_conf if own or site_conf == "medium" else "medium"
            emails.append(field_value(em["value"], WEBSITE, conf, crawl["fetchedAt"], url=em["url"]))
        for ph in crawl["phones"]:
            phones.append(field_value(ph["value"], WEBSITE, site_conf, crawl["fetchedAt"], url=ph["url"]))
    out = {
        "name": e.name,
        "website": website,
        "phones": merge_values(phones),
        "emails": merge_values(emails),
        "socials": merge_values(socials),
        "contactName": contact,
        "address": address,
        "matches": matches,
    }
    has_contact = website or out["phones"] or out["emails"] or contact or out["socials"]
    return out if has_contact else None


# ----------------------------------------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------------------------------------
def rates(entities: list[Entity], results: dict[str, dict | None]) -> dict:
    n = len(entities)

    def share(pred) -> tuple[int, float]:
        k = sum(1 for e in entities if (r := results.get(e.id)) and pred(r))
        return k, (k / n if n else 0.0)

    def high(items):
        return any(i["confidence"] == "high" for i in items)

    return {
        "n": n,
        "any": share(lambda r: True),
        "phone": share(lambda r: r["phones"]),
        "website": share(lambda r: r["website"]),
        "email": share(lambda r: r["emails"]),
        "name": share(lambda r: r["contactName"]),
        "phone_or_email": share(lambda r: r["phones"] or r["emails"]),
        "address": share(lambda r: r["address"]),
        "high_phone": share(lambda r: high(r["phones"])),
        "high_email": share(lambda r: high(r["emails"])),
        "overture_email": share(lambda r: any(f["source"] == OVERTURE for f in r["emails"])),
        "web_email": share(lambda r: any(f["source"] == WEBSITE for f in r["emails"])),
        "social": share(lambda r: r.get("socials")),
        "registry_phone": share(lambda r: any(f["source"] in REGISTRIES for f in r["phones"])),
        "registry_only_phone_or_email": share(
            lambda r: (
                (r["phones"] or r["emails"])
                and all(f["source"] in REGISTRIES for f in r["phones"] + r["emails"])
            )
        ),
    }


def pct(share: tuple[int, float]) -> str:
    return f"{share[1] * 100:.1f}% ({share[0]:,})"


def render_report(
    day: str,
    stats: dict,
    web_stats: dict,
    meta: dict,
    drops: Counter,
    examples: list[tuple[Entity, dict]],
    lead_stats: dict,
) -> str:
    def row(label: str, r: dict) -> str:
        return (
            f"| {label} | {r['n']:,} | {pct(r['phone'])} | {pct(r['website'])} | {pct(r['email'])} | "
            f"{pct(r['name'])} | {pct(r['any'])} |"
        )

    lines = [
        f"# Free contact enrichment: match rates ({day})",
        "",
        "Generated by `uv run python -m engine.enrich.contacts` (deterministic given the web cache). All values are "
        "public business contact details with a source; none are guessed. Match confidence is `high` or `medium` "
        "(low matches are dropped).",
        "",
        "## Share of entities with at least one suggestion",
        "",
        "| Group | Entities | Phone | Website | Email | Contact name | Any field |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        row("All prospects", stats["all"]),
        row("Best-fit prospects (violation-driven jobs > 0, 5-40 jobs/yr)", stats["best"]),
        row("Company owners and buyers on leads", stats["owners"]),
        "",
        "Prospects by trade:",
        "",
        "| Trade | Entities | Phone | Website | Email | Contact name | Any field |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        *[row(t, s) for t, s in sorted(stats["trades"].items())],
        "",
        "## Where the emails and phones come from",
        "",
        "| Group | Phone, high confidence | Email, high confidence | Email from Overture | Email from website | "
        "Phone or email |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        *[
            f"| {label} | {pct(r['high_phone'])} | {pct(r['high_email'])} | {pct(r['overture_email'])} | "
            f"{pct(r['web_email'])} | {pct(r['phone_or_email'])} |"
            for label, r in (
                ("All prospects", stats["all"]),
                ("Best-fit prospects", stats["best"]),
                ("Company owners", stats["owners"]),
            )
        ],
        "",
        "## New sources (2026-11-18 plan, docs/17 §4.3)",
        "",
        "| Group | Business social page | Phone from a state registry | Phone or email only from a registry |",
        "| --- | ---: | ---: | ---: |",
        *[
            f"| {label} | {pct(r['social'])} | {pct(r['registry_phone'])} | {pct(r['registry_only_phone_or_email'])} |"
            for label, r in (
                ("All prospects", stats["all"]),
                ("Best-fit prospects", stats["best"]),
                ("Company owners", stats["owners"]),
            )
        ],
        "",
        f"Leads with an address-based suggestion (company owners only): {lead_stats['leads']:,} of "
        f"{lead_stats['company_leads']:,} company-owned leads; foreclosed rental registry agent "
        f"{lead_stats[FORECLOSED]:,}, Overture listing at the mailing address {lead_stats[AT_MAILING]:,}. Leads with a "
        f"phone or email from any source (owner name or address): {lead_stats['phone_or_email_any']:,} of "
        f"{lead_stats['all_leads']:,} leads.",
        "",
        "## Website crawl",
        "",
        f"- Sites with a matched website: {web_stats['sites']:,}.",
        f"- Outcome: {web_stats['ok']:,} readable, {web_stats['robots_blocked']:,} blocked by robots.txt, "
        f"{web_stats['error']:,} unreachable or erroring.",
        f"- Readable sites showing an email: {web_stats['with_email']:,}; showing a phone: {web_stats['with_phone']:,}.",
        "",
        "## Matching outcomes (entities without a suggestion, by reason)",
        "",
        *[f"- {k}: {v:,}" for k, v in sorted(drops.items())],
        "",
        "## Sources",
        "",
        f"- Overture Maps Places release {meta['release']} ({meta['places']:,} places in the Chicago metro subset; "
        f"{meta['open_places']:,} not permanently closed). CDLA-Permissive-2.0. Attribution: "
        "(c) Overture Maps Foundation; place data sourced from Meta and others.",
        f"- City of Chicago Business Licenses, current active (uupf-x98q): {meta['licenses']:,} licenses.",
        *[
            f"- {SOURCE_LABELS[k]} ({SOURCE_URLS[k]}): {meta['registries'].get(k, 0):,} rows; matched to prospects by "
            "exact normalized name (medium confidence; a name listed with different phones is dropped)."
            for k in REGISTRIES
        ],
        f"- {SOURCE_LABELS[FORECLOSED]} ({SOURCE_URLS[FORECLOSED]}): {meta['foreclosed']:,} registrations; the "
        "notices agent of a registration at the lead's property in the last three years, only when the agent is a "
        "company (individual agents' phones and emails are never shipped).",
        "- Overture listing at a company owner's mailing address: only when exactly one business is listed at that "
        "address (medium confidence; the business there may be a manager or agent, not the owner).",
        f"- City of Chicago Business Owners (ezma-pppn): {meta['owners']:,} owner rows. Used only as a contact-name "
        "suggestion for the matched business (titles preferred: owner, sole proprietor, president, CEO, managing "
        "member, manager, member, partner).",
        "- Company websites: homepage and at most two contact pages, robots.txt honored, 1 request/second/host, "
        "30-day cache.",
        "",
        "## Examples",
        "",
        *[
            f"- **{e.name}** ({e.kind}): website {r['website']['value'] if r['website'] else '-'}; "
            f"phones {', '.join(p['value'] for p in r['phones'][:2]) or '-'}; "
            f"emails {', '.join(m['value'] for m in r['emails'][:2]) or '-'}; "
            f"contact {r['contactName']['value'] + ' (' + r['contactName']['title'] + ')' if r['contactName'] else '-'}"
            for e, r in examples
        ],
        "",
        "## Caveats",
        "",
        "- A match is a name match, not proof. Exact normalized name plus a trade-compatible Overture category inside "
        "Chicago is `high`; same name outside the city, a missing category, or a close-but-not-exact name is "
        "`medium`; names shared by several different businesses are dropped as ambiguous.",
        "- Verify every contact before outreach (open the website, check the name and trade). Owner names from the "
        "business-owner records are public filings and are a name suggestion only.",
        "- Overture phone numbers can be a company's main line or a mobile number; call business lines manually only "
        "and never autodial or text (docs/14, section 8).",
        "- Chicago business licenses cover only businesses that need a city license, so many contractors and most "
        "single-property LLCs have no record there.",
        "",
    ]
    return "\n".join(lines)


# ----------------------------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--no-web", action="store_true", help="do not fetch websites (cached results are still used)"
    )
    ap.add_argument("--refresh-web", action="store_true", help="ignore the 30-day cache")
    ap.add_argument("--web-limit", type=int, default=None, help="fetch at most this many uncached sites")
    ap.add_argument(
        "--workers", type=int, default=16, help="parallel hosts (each host stays at 1 request/second)"
    )
    ap.add_argument("--out", type=Path, default=JSON_OUT)
    ap.add_argument("--no-report", action="store_true", help="do not write the findings markdown")
    args = ap.parse_args()
    started = time.monotonic()
    for path in (PROSPECTS, SNAPSHOT):
        if not path.exists():
            raise SystemExit(
                f"{path} missing: run `engine.leads.snapshot` and `engine.leads.prospects` first"
            )

    prospects, owners, day = load_entities(PROSPECTS, SNAPSHOT)
    con = db.connect()
    rows = load_places(con)
    release = rows[0]["release"] if rows else "unknown"
    stamps = {
        OVERTURE: re.match(r"\d{4}-\d{2}-\d{2}", release).group(0) if re.match(r"\d{4}-", release) else day,
        LICENSES: retrieved(RAW / "biz_licenses" / "page-0000.csv", day),
        CDB: retrieved(RAW / "cdb_vendors" / "page-0000.csv", day),
        IDPH_LEAD: retrieved(RAW / "idph_lead_contractors" / "page-0000.csv", day),
        IDPH_ASBESTOS: retrieved(RAW / "idph_asbestos_contractors" / "page-0000.csv", day),
    }
    print(f"{len(prospects)} prospects, {len(owners)} company owners/buyers, {len(rows):,} open places")
    idx = PlaceIndex(rows)
    lic = LicenseIndex(con)
    reg = RegistryIndex(con)
    drops: Counter = Counter()
    by_lead = lead_suggestions(con, json.loads(SNAPSHOT.read_text()), rows, stamps, drops)
    meta = {
        "release": release,
        "places": con.execute("SELECT count(*) FROM places").fetchone()[0],
        "open_places": len(rows),
        "licenses": con.execute("SELECT count(*) FROM biz_licenses").fetchone()[0],
        "owners": con.execute("SELECT count(*) FROM biz_owners").fetchone()[0],
        "registries": dict(
            con.execute("SELECT registry, count(*) FROM contractor_registry GROUP BY 1 ORDER BY 1").fetchall()
        ),
        "foreclosed": con.execute("SELECT count(*) FROM foreclosed_rentals").fetchone()[0],
    }
    con.close()

    entities = [*prospects, *owners]
    pmatch = {f"{e.kind}:{e.id}": match_place(e, idx, drops) for e in entities}
    lmatch = {f"{e.kind}:{e.id}": lic.match(e, drops) for e in entities}
    rmatch = {e.id: reg.match(e, drops) for e in prospects}
    print(
        f"matched: places {sum(1 for v in pmatch.values() if v):,}, licenses {sum(1 for v in lmatch.values() if v):,}"
    )

    # A license at the same ZIP as the place is independent evidence that both describe one business.
    for e in entities:
        pm, lm = pmatch[f"{e.kind}:{e.id}"], lmatch[f"{e.kind}:{e.id}"]
        if pm and lm and pm.confidence == "medium" and pm.method == "exact_name":
            lic_zips = {(r["zip"] or "")[:5] for r in lm.rows}
            if any((p["postcode"] or "")[:5] in lic_zips for p in pm.places):
                pm.confidence = "high"

    sites = sorted(
        {
            site
            for pm in pmatch.values()
            if pm
            for p in pm.places[:1]
            for w in p["websites"] or []
            if (site := web.clean_website(w))
        }
    )
    if args.no_web:
        crawls = {}
        for site in sites:
            rec = web.load_cached(WEB_CACHE, site, date.today())
            if rec:
                crawls[rec["host"]] = rec
        fetched = 0
    else:
        crawls, fetched = web.crawl_sites(
            sites,
            WEB_CACHE,
            date.today(),
            workers=args.workers,
            refresh=args.refresh_web,
            limit=args.web_limit,
        )

    results: dict[str, dict | None] = {}
    for e in entities:
        pm, lm = pmatch[f"{e.kind}:{e.id}"], lmatch[f"{e.kind}:{e.id}"]
        crawl = None
        if pm and pm.places:
            for w in pm.places[0]["websites"] or []:
                site = web.clean_website(w)
                if site:
                    crawl = crawls.get(web.host_of(site))
                    break
        results[f"{e.kind}:{e.id}"] = assemble(
            e, pm, lm, crawl, stamps, rmatch.get(e.id) if e.kind == "prospect" else None
        )
    for e in entities:
        if results[f"{e.kind}:{e.id}"] is None:
            drops["no usable contact field"] += 1

    by_prospect = {e.id: results[f"prospect:{e.id}"] for e in prospects}
    by_owner = {e.id: results[f"owner:{e.id}"] for e in owners}
    lead_owner: dict[str, str] = {}
    for e in owners:
        if by_owner[e.id]:
            for lead_id in e.leads:
                lead_owner.setdefault(lead_id, e.id)

    payload = {
        "generatedFor": day,
        "sources": {
            OVERTURE: {
                "label": SOURCE_LABELS[OVERTURE],
                "release": release,
                "license": "CDLA-Permissive-2.0",
                "attribution": "Places data (c) Overture Maps Foundation",
                "url": "https://overturemaps.org",
            },
            LICENSES: {
                "label": SOURCE_LABELS[LICENSES],
                "url": "https://data.cityofchicago.org/Community-Economic-Development/Business-Licenses-Current-Active/uupf-x98q",
            },
            WEBSITE: {"label": SOURCE_LABELS[WEBSITE]},
            **{k: {"label": SOURCE_LABELS[k], "url": SOURCE_URLS[k]} for k in (*REGISTRIES, FORECLOSED)},
            AT_MAILING: {
                "label": SOURCE_LABELS[AT_MAILING],
                "release": release,
                "license": "CDLA-Permissive-2.0",
                "attribution": "Places data (c) Overture Maps Foundation",
                "url": "https://overturemaps.org",
            },
        },
        "prospects": {k: v for k, v in sorted(by_prospect.items()) if v},
        "owners": {k: v for k, v in sorted(by_owner.items()) if v},
        "leadOwners": dict(sorted(lead_owner.items())),
        "leads": dict(sorted(by_lead.items())),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n")
    print(
        f"wrote {args.out}: {len(payload['prospects'])} prospects, {len(payload['owners'])} owners, "
        f"{len(payload['leadOwners'])} leads by owner name, {len(by_lead)} leads by address "
        f"({args.out.stat().st_size / 1024:.0f} KB)"
    )

    csv_path = Path(f"data/contacts-{day}.csv")
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["kind", "id", "name", "trade", "website", "phones", "emails", "contact_name", "contact_title",
             "address", "matches", "sources"]
        )  # fmt: skip
        for e in entities:
            r = results[f"{e.kind}:{e.id}"]
            if not r:
                continue
            c = r["contactName"]
            srcs = sorted(
                {f["source"] for k in ("phones", "emails") for f in r[k]}
                | {f["source"] for k in ("website", "contactName", "address") if (f := r[k])}
            )
            w.writerow(
                [
                    e.kind, e.id, e.name, e.trade or "", r["website"]["value"] if r["website"] else "",
                    "; ".join(f"{f['value']} [{f['source']},{f['confidence']}]" for f in r["phones"]),
                    "; ".join(f"{f['value']} [{f['source']},{f['confidence']}]" for f in r["emails"]),
                    c["value"] if c else "", c["title"] if c else "", r["address"]["value"] if r["address"] else "",
                    "; ".join(f"{m['source']}:{m['method']}:{m['confidence']}" for m in r["matches"]),
                    "; ".join(srcs),
                ]
            )  # fmt: skip
    print(f"wrote {csv_path}")

    stats = {
        "all": rates(prospects, by_prospect),
        "best": rates([e for e in prospects if e.best_fit], by_prospect),
        "owners": rates(owners, by_owner),
        "trades": {
            t: rates([e for e in prospects if e.trade == t], by_prospect)
            for t in sorted({e.trade for e in prospects})
        },
    }
    hosts = [crawls[h] for h in sorted(crawls)]
    web_stats = {
        "sites": len(sites),
        "ok": sum(1 for r in hosts if r["status"] == "ok"),
        "robots_blocked": sum(1 for r in hosts if r["status"] == "robots_blocked"),
        "error": sum(1 for r in hosts if r["status"] == "error"),
        "with_email": sum(1 for r in hosts if r["emails"]),
        "with_phone": sum(1 for r in hosts if r["phones"]),
    }
    snap_leads = json.loads(SNAPSHOT.read_text())["leads"]
    lead_stats = {
        "all_leads": len(snap_leads),
        "company_leads": sum(1 for x in snap_leads if (x["owner"] or {}).get("type") == "company"),
        "leads": len(by_lead),
        FORECLOSED: sum(1 for v in by_lead.values() if any(m["source"] == FORECLOSED for m in v["matches"])),
        AT_MAILING: sum(1 for v in by_lead.values() if any(m["source"] == AT_MAILING for m in v["matches"])),
        "phone_or_email_any": sum(
            1
            for x in snap_leads
            if any(
                (c := src.get(key)) and (c["phones"] or c["emails"])
                for src, key in ((by_lead, x["id"]), (by_owner, lead_owner.get(x["id"])))
            )
        ),
    }
    print(f"leads: {lead_stats}")
    examples = [
        (e, r)
        for e in prospects
        if e.best_fit and (r := by_prospect[e.id]) and r["emails"] and r["phones"] and r["website"]
    ][:3]
    examples += [(e, r) for e in owners if (r := by_owner[e.id]) and r["phones"]][:2]
    for label in ("all", "best", "owners"):
        r = stats[label]
        print(
            f"{label:7s} n={r['n']:5d} phone {pct(r['phone'])} website {pct(r['website'])} "
            f"email {pct(r['email'])} name {pct(r['name'])} any {pct(r['any'])}"
        )
    if not args.no_report:
        FINDINGS.mkdir(parents=True, exist_ok=True)
        path = FINDINGS / f"contact-enrichment-{day}.md"
        path.write_text(render_report(day, stats, web_stats, meta, drops, examples, lead_stats))
        print(f"wrote {path}")
    print(f"web sites: {len(sites)} ({fetched} fetched this run)")
    print(f"done in {time.monotonic() - started:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
