"""Social and listing collectors for the event-lead scanner.

Public, logged-out collection goes through official APIs and licensed providers
(Apify, SerpApi, Firecrawl) configured by environment variables. Logged-in Facebook,
Instagram and TikTok collection uses the team's own session cookies (Playwright storage
state or cookie JSON) or Apify actors that accept those cookies. No fake-account
creation and no captcha-solving.
"""

from __future__ import annotations

from engine.collect.social.facebook import collect_facebook
from engine.collect.social.instagram import collect_instagram
from engine.collect.social.listings import collect_listings
from engine.collect.social.reddit import collect_reddit
from engine.collect.social.tiktok import collect_tiktok
from engine.collect.social.x import collect_x
from engine.leads.event_models import RawEvent


def collect_social(*, authenticated: bool = True) -> tuple[list[RawEvent], list[dict]]:
    """Run every social/listing collector. Returns (items, skip/status notes)."""
    items: list[RawEvent] = []
    notes: list[dict] = []
    for fn in (
        collect_listings,
        collect_reddit,
        collect_x,
        lambda: collect_facebook(authenticated=authenticated),
        lambda: collect_instagram(authenticated=authenticated),
        lambda: collect_tiktok(authenticated=authenticated),
    ):
        batch, note = fn()
        items.extend(batch)
        notes.extend(note)
    return items, notes
