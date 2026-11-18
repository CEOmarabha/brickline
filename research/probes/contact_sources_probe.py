"""Which free public records add a phone, email or mailing address to our leads and prospects?

Reproduces the 2026-11-18 contact-source research (docs/17): state transfer forms (PTAX-203), contractor and
foreclosure registries, the Cook County tax roll matched by buyer name, and Overture places matched by mailing
address. Writes research/findings/contact-sources-<date>.md and .json with aggregate counts only (no names,
phones, emails or addresses are stored).

Needs network access and the tracked app data (web/data/*.json). The Overture step needs `duckdb` (optional).
Run from the repo root:  python3 research/probes/contact_sources_probe.py [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine.enrich.names import normalize  # noqa: E402

UA = {"User-Agent": "BricklineResearchBot/0.1 (+contact: founder)"}
IL = "illinois-edp.data.socrata.com"
CHI = "data.cityofchicago.org"
COOK = "datacatalog.cookcountyil.gov"
SUFFIX = {"STREET": "ST", "AVENUE": "AVE", "AV": "AVE", "BOULEVARD": "BLVD", "BV": "BLVD", "ROAD": "RD", "DRIVE": "DR",
          "PLACE": "PL", "COURT": "CT", "PARKWAY": "PKWY", "PK": "PKWY", "TERRACE": "TER", "TR": "TER", "LANE": "LN",
          "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}  # fmt: skip


def get(url: str, tries: int = 3):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return json.load(r)
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(4 * 2**attempt)


def soql(dom: str, ds: str, **params):
    return get(f"https://{dom}/resource/{ds}.json?" + urllib.parse.urlencode(params))


def pull_all(dom: str, ds: str) -> list[dict]:
    rows, off = [], 0
    while True:
        page = get(f"https://{dom}/resource/{ds}.json?$limit=5000&$offset={off}&$order=:id")
        rows += page
        if len(page) < 5000:
            return rows
        off += 5000


def akey(address: str | None) -> str:
    """Normalized 'NUMBER DIR STREET SUFFIX' key; units and anything after a comma are dropped."""
    if not address:
        return ""
    out: list[str] = []
    for tok in re.sub(r"[^A-Z0-9 ]", " ", address.upper().split(",")[0]).split():
        tok = SUFFIX.get(tok, tok)
        if tok in ("APT", "UNIT", "STE", "FL", "SUITE"):
            break
        out.append(tok)
    return " ".join(out)


def load(name: str):
    return json.loads((ROOT / "web" / "data" / name).read_text())


def ptax(snap: dict) -> dict:
    """PTAX-203 freshness and what the form says about the buyer (no phone or email columns exist)."""
    base = "upper(line_1_county)='COOK' AND upper(line_1_city)='CHICAGO'"
    newest = soql(IL, "it54-y4c6", **{"$select": "max(date_recorded) as d"})[0]["d"][:10]
    since = snap["meta"]["dataAsOf"]["sales"]
    where = f"{base} AND date_recorded > '{since}T00:00:00'"

    def count(extra: str = "") -> int:
        return int(soql(IL, "it54-y4c6", **{"$select": "count(*) as n", "$where": where + extra})[0]["n"])

    total = count()

    def present(field: str) -> str:
        return f" AND {field} IS NOT NULL AND {field} != ''"

    top = soql(IL, "it54-y4c6", **{"$select": "count(*) as n", "$where": where, "$group": "step_4_preparer_name",
                                   "$order": "n desc", "$limit": "12"})  # fmt: skip
    return {
        "newestRecorded": newest,
        "assessorSalesAsOf": since,
        "chicagoTransfersSince": total,
        "buyerOrganization": count(present("step_4_buyer_organization")),
        "buyerAgentAddress": count(present("step_4_buyer_s_agent_s_address")),
        "investorCheckbox10l": count(" AND line_10l_buyer_is_a_real = true"),
        "bankReo10h": count(" AND line_10h_bank_reo = true"),
        "top12PreparerShare": round(sum(int(x["n"]) for x in top) / total, 3) if total else None,
    }


def registries(snap: dict, prospects: list[dict], contacts: dict) -> dict:
    """Contractor registries vs prospects (name) and foreclosure/scofflaw/vacant-violation registries vs leads (address)."""

    def has_pe(pid: str) -> bool:
        entry = contacts["prospects"].get(pid) or {}
        return bool(entry.get("phones") or entry.get("emails"))

    by_name = collections.defaultdict(list)
    for p in prospects:
        by_name[normalize(p["company"])].append(p["id"])
    out: dict = {
        "prospectsTotal": len(prospects),
        "prospectsWithPhoneOrEmailBefore": sum(has_pe(p["id"]) for p in prospects),
    }
    new_ids: set[str] = set()
    for label, (dom, ds, name_f, phone_f) in {
        "cdbVendors": (IL, "3dh9-yktq", "vendor_name", "phone_number"),
        "leadContractors": (IL, "vpwp-h7xr", "contractorname", "phone"),
        "asbestosContractors": (IL, "kt5u-9dcu", "contractor_name", "phone"),
    }.items():
        rows = pull_all(dom, ds)
        matched = {
            pid
            for r in rows
            if (k := normalize(r.get(name_f))) in by_name
            for pid in by_name[k]
            if (r.get(phone_f) or "").strip()
        }
        out[label] = {
            "rows": len(rows),
            "prospectsMatchedWithPhone": len(matched),
            "newlyReachable": len([m for m in matched if not has_pe(m)]),
        }
        new_ids |= {m for m in matched if not has_pe(m)}
    out["prospectsNewlyReachableAllRegistries"] = len(new_ids)

    leads_by_addr = collections.defaultdict(list)
    for lead in snap["leads"]:
        leads_by_addr[akey(lead["address"])].append(lead)
    already = set(contacts["leadOwners"])
    foreclosed = pull_all(CHI, "yhcw-iu53")
    ids = {lead["id"] for r in foreclosed for lead in leads_by_addr.get(akey(r.get("property_address")), [])}
    out["foreclosedRentalRegistry"] = {
        "rows": len(foreclosed),
        "leadsMatched": len(ids),
        "newlyReachableWithPhoneAndEmail": len(ids - already),
    }
    scofflaw = pull_all(CHI, "crg5-4zyp")
    sc_ids = {
        lead["id"]
        for r in scofflaw
        for f in ("address", "secondary_address", "tertiary_address")
        for lead in leads_by_addr.get(akey(r.get(f)), [])
    }
    out["scofflawList"] = {"rows": len(scofflaw), "leadsOnList": len(sc_ids),
                           "byKind": dict(collections.Counter(lead["kind"] for v in leads_by_addr.values() for lead in v if lead["id"] in sc_ids))}  # fmt: skip
    return out


def tax_roll_by_name(snap: dict) -> tuple[dict, dict[str, str]]:
    """Investor buyers with no mailing address that already pay tax on a Cook County parcel under the same name."""
    year = soql(COOK, "3723-97qp", **{"$select": "max(year) as y"})[0]["y"]
    inv = [lead for lead in snap["leads"] if lead["kind"] == "investor_purchase"]
    nomail = [lead for lead in inv if not lead["owner"].get("mailing")]
    names = sorted(
        {(lead["buyer"]["name"] or "").upper().strip() for lead in nomail if lead["buyer"].get("name")}
    )
    found: dict[str, list[dict]] = {}
    for i in range(0, len(names), 40):
        batch = names[i : i + 40]
        quoted = ",".join("'" + n.replace("'", "''") + "'" for n in batch)
        rows = soql(COOK, "3723-97qp", **{
            "$where": f"year='{year}' AND (upper(mail_address_name) in ({quoted}) OR upper(owner_address_name) in ({quoted}))",
            "$select": "pin,mail_address_name,mail_address_full,owner_address_name,owner_address_full", "$limit": "5000"})  # fmt: skip
        for r in rows:
            for nm in (r.get("mail_address_name"), r.get("owner_address_name")):
                if (k := (nm or "").upper().strip()) in batch:
                    found.setdefault(k, []).append(r)
    best: dict[str, str] = {}
    prop_key = {(lead["buyer"]["name"] or "").upper().strip(): akey(lead["address"]) for lead in nomail}
    for nm, rows in found.items():
        mails = collections.Counter(
            (r.get("mail_address_full") or r.get("owner_address_full") or "").strip() for r in rows
        )
        mails.pop("", None)
        if mails:
            best[nm] = mails.most_common(1)[0][0]
    covered = [lead for lead in nomail if (lead["buyer"].get("name") or "").upper().strip() in best]
    return {
        "rollYear": year, "investorLeads": len(inv), "investorLeadsWithoutMailing": len(nomail), "distinctBuyerNames": len(names),
        "leadsWhereBuyerIsOnRoll": len(covered), "namesWithMailing": len(best),
        "mailingIsPurchasedProperty": sum(1 for nm, a in best.items() if akey(a) == prop_key.get(nm)),
        "buyersWith3PlusParcels": sum(1 for rows in found.values() if len({r["pin"] for r in rows}) >= 3),
    }, best  # fmt: skip


def overture_by_address(best: dict[str, str]) -> dict:
    """Overture places listed at those mailing addresses (a suggestion only: the business may not be the buyer)."""
    try:
        import duckdb
    except ImportError:
        return {"skipped": "duckdb not installed"}
    listing = urllib.request.urlopen(urllib.request.Request(
        "https://overturemaps-us-west-2.s3.amazonaws.com/?list-type=2&prefix=release/&delimiter=/", headers=UA), timeout=60).read().decode()  # fmt: skip
    release = sorted(re.findall(r"release/([0-9\-\.a-z]+)/", listing))[-1]
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
    rows = con.execute(f"""
        SELECT phones, emails, addresses[1].freeform
        FROM read_parquet('s3://overturemaps-us-west-2/release/{release}/theme=places/type=place/*', hive_partitioning=1)
        WHERE bbox.xmin BETWEEN -87.95 AND -87.52 AND bbox.ymin BETWEEN 41.64 AND 42.03""").fetchall()  # noqa: S608
    by_addr: dict[str, list] = collections.defaultdict(list)
    for phones, emails, addr in rows:
        by_addr[akey(addr)].append((phones, emails))
    hit = [a for a in best.values() if akey(a) in by_addr]
    return {"release": release, "mailingAddressesTested": len(best), "withListingAtAddress": len(hit),
            "withPhone": sum(1 for a in hit if any(p for p, _ in by_addr[akey(a)])),
            "withEmail": sum(1 for a in hit if any(e for _, e in by_addr[akey(a)]))}  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now(UTC).date().isoformat())
    args = ap.parse_args()
    snap, prospects, contacts = (
        load("snapshot.json"),
        load("prospects.json")["prospects"],
        load("contacts.json"),
    )
    result: dict = {"date": args.date, "snapshotAsOf": snap["meta"]["generatedAt"][:10]}
    result["ptax203"] = ptax(snap)
    result["registries"] = registries(snap, prospects, contacts)
    result["taxRollByBuyerName"], best = tax_roll_by_name(snap)
    result["overtureByMailingAddress"] = overture_by_address(best)
    out = ROOT / "research" / "findings"
    (out / f"contact-sources-{args.date}.json").write_text(json.dumps(result, indent=1) + "\n")
    lines = [
        f"# Contact-source probe ({args.date})",
        "",
        "Aggregate counts only. Reproduce with `python3 research/probes/contact_sources_probe.py`.",
        "",
    ]
    for section, data in result.items():
        if isinstance(data, dict):
            lines += [f"## {section}", ""] + [f"- {k}: {json.dumps(v)}" for k, v in data.items()] + [""]
    (out / f"contact-sources-{args.date}.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
