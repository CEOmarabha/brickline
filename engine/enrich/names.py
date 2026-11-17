"""Company-name normalization and a conservative token-set similarity (no third-party dependencies)."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

# Legal-form words that say nothing about which company it is. Removed wherever they appear.
LEGAL_WORDS = frozenset(
    {
        "INC",
        "INCORPORATED",
        "LLC",
        "LLP",
        "LP",
        "LTD",
        "LIMITED",
        "CORP",
        "CORPORATION",
        "CO",
        "COMPANY",
        "THE",
        "PLLC",
    }
)
# Words that carry no identity when comparing (kept in the name, ignored for blocking and one-token checks).
GENERIC_WORDS = frozenset(
    {
        "AND", "OF", "CHICAGO", "ILLINOIS", "SERVICE", "SERVICES", "CONSTRUCTION", "CONTRACTORS", "CONTRACTOR",
        "CONTRACTING", "BUILDERS", "BUILDING", "GROUP", "ENTERPRISES", "ENTERPRISE", "PROPERTIES", "PROPERTY",
        "HOLDINGS", "INVESTMENTS", "INVESTMENT", "REALTY", "MANAGEMENT", "REAL", "ESTATE", "ROOFING", "PLUMBING",
        "ELECTRIC", "ELECTRICAL", "MASONRY", "HOME", "HOMES", "IMPROVEMENT", "REMODELING", "GENERAL", "INTERNATIONAL",
        "SOLUTIONS", "DEVELOPMENT", "DEVELOPERS", "CAPITAL", "PARTNERS", "VENTURES", "TRUST",
    }
)  # fmt: skip


def normalize(name: str | None) -> str:
    """Upper-case, '&' -> AND, punctuation dropped (apostrophes joined), legal words removed, spaces collapsed."""
    if not name:
        return ""
    s = name.upper().replace("&", " AND ")
    s = re.sub(r"[’'`]", "", s)
    s = re.sub(r"\bL\.?\s?L\.?\s?C\b\.?", " LLC ", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return " ".join(t for t in s.split() if t not in LEGAL_WORDS)


def distinctive(key: str) -> list[str]:
    """Tokens that help identify the company (generic industry words removed)."""
    return [t for t in key.split() if t not in GENERIC_WORDS]


def token_set_ratio(a: str, b: str) -> float:
    """Similarity in [0, 1] of two normalized names, ignoring word order.

    Follows the usual token-set recipe (shared tokens first, then each side's remaining tokens), but scores only
    the two full strings against each other, so a name that is merely a prefix or subset of another ("ACME" vs
    "ACME ROOFING") does not count as a perfect match. Typos inside a word still score high.
    """
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0.0
    common = sorted(ta & tb)
    left = " ".join([*common, *sorted(ta - tb)])
    right = " ".join([*common, *sorted(tb - ta)])
    return SequenceMatcher(None, left, right).ratio()
