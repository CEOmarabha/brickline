"""Rules-based trade tagging for permits and violations (v0).

Patterns are RE2 regular expressions (no lookarounds) applied to upper-cased text. Permit rules look at
permit type, work type and description together; violation rules look at the violation description.
They favour precision: a record with no match is "untagged", not guessed.
"""

from __future__ import annotations

PERMIT_TRADES: dict[str, str] = {
    "roofing": r"\bRE-?ROOF|\bROOF(ING)?\b|\bTEAR[- ]?OFF\b|\bSHINGLE|MODIFIED BITUMEN|\bTPO\b|\bEPDM\b",
    "masonry": r"MASONRY|TUCK ?POINT|\bBRICK|PARAPET|CHIMNEY|COPING|LINTEL|LIMESTONE",
    "porch": r"\bPORCH|\bDECK\b|BALCON|FIRE ESCAPE|EXTERIOR STAIR|REAR STAIR",
    "windows_doors": r"\bWINDOWS?\b|EXTERIOR WINDOWS/DOORS|\bDOORS? REPLACE|STOREFRONT",
    "electrical": r"ELECTRICAL WORK|\bELECTRIC(AL)? SERVICE|\bWIRING\b|\bAMP SERVICE|\bPANEL\b|LINE VOLTAGE",
    "plumbing": r"PLUMBING|\bSEWER\b|WATER (SERVICE|HEATER)|\bDRAIN|BACKFLOW",
    "hvac": r"MECHANICAL WORK|\bHVAC\b|\bFURNACE|\bBOILER|AIR CONDITION|\bA/?C UNIT|ROOFTOP UNIT|\bRTU\b"
    r"|DUCTWORK|VENTILATION|CONDENS(ER|ING) UNIT",
    "solar": r"SOLAR|PHOTOVOLTAIC|\bPV\b",
    "fence": r"\bFENCE|TRASH ENCLOSURE",
    "garage": r"\bGARAGE\b",
    "fire_alarm": r"FIRE ALARM|SPRINKLER|FIRE SUPPRESSION",
    "elevator": r"ELEVATOR|ESCALATOR|WHEELCHAIR LIFT",
    "concrete_flatwork": r"\bCONCRETE\b|\bSLAB\b|DRIVEWAY|\bSIDEWALK|\bPATIO\b|FOUNDATION",
    "interior_buildout": r"INTERIOR (ALTERATION|RENOVATION|REMODEL|BUILD)|TENANT (BUILD|IMPROVEMENT)"
    r"|BUILD[- ]?OUT|NONSTRUCTURAL INTERIOR|GUT REHAB|REMODEL",
    "demolition": r"WRECKING|DEMOLITION|\bWRECK\b|\bRAZE",
    "new_construction": r"PERMIT - NEW CONSTRUCTION|ERECT (A |AN )?(NEW )?\d*[- ]?(STORY|STY)",
    "signs": r"PERMIT - SIGNS|\bSIGNS?\b",
}

VIOLATION_TRADES: dict[str, str] = {
    "roofing": r"REPAIR ROOF|ROOF STRUCTURE|ROOF DRAIN|DRAIN ROOF|ROOF LIVE|RE-?ROOF|GUTTER|DOWNSPOUT",
    "masonry": r"EXTERIOR WALL|MASONRY|TUCK ?POINT|PARAPET|CHIMNEY|CORNICE|COPING|LINTEL",
    "porch": r"PORCH|EXTERIOR STAIR|BALCON|\bDECK\b|FIRE ESCAPE",
    "windows_doors": r"WINDOW|\bDOOR|GLAZ|PANES",
    "electrical": r"ELECTRIC|WIRING|OUTLET|\bLIGHTING|FIXTURE.*ELEC|\bPANEL",
    "plumbing": r"PLUMB|WATER HEATER|\bDRAIN|SEWER|\bTOILET|\bSINK|FAUCET|WATER SUPPLY",
    "hvac": r"\bHEAT|FURNACE|BOILER|VENTILAT|CHIMNEY FLUE|RADIATOR",
    "elevator": r"ELEVA",
    "pest": r"RODENT|INSECT|ROACH|BED ?BUG|\bPEST|VERMIN|EXTERMINAT",
    "fire_safety": r"SMOKE DETECTOR|CARBON MONOXIDE|FIRE ALARM|EXTINGUISHER|SPRINKLER",
    "fence": r"\bFENCE",
    "garage": r"\bGARAGE",
}


def sql_flags(text_expr: str, rules: dict[str, str], prefix: str = "t_") -> str:
    """Return a SQL select-list fragment with one boolean column per trade."""
    cols = []
    for trade, pattern in rules.items():
        escaped = pattern.replace("'", "''")
        cols.append(f"regexp_matches({text_expr}, '{escaped}') AS {prefix}{trade}")
    return ",\n    ".join(cols)
