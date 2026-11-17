"""Display formatting for public-record strings."""

from __future__ import annotations

import re

UPPER_WORDS = {"LLC", "LLP", "LP", "II", "III", "IV", "USA", "CTA", "HVAC", "JV", "PC"}


def title(s: str | None) -> str | None:
    """Title-case an all-caps record: '2031 W 23RD ST, CHICAGO IL' -> '2031 W 23rd St, Chicago IL'."""
    if not s:
        return s
    s = re.sub(r"\s+", " ", s.strip())
    s = re.sub(
        r"\b([A-Z])([A-Z']*)\b",
        lambda m: m.group(0) if m.group(0) in UPPER_WORDS else m.group(1) + m.group(2).lower(),
        s,
    )
    s = re.sub(r"(\d)(ST|ND|RD|TH)\b", lambda m: m.group(1) + m.group(2).lower(), s)
    return re.sub(r"\b([A-Z][a-z])(\s+\d{5}(?:-\d{4})?)$", lambda m: m.group(1).upper() + m.group(2), s)
