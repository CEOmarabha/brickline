"""Reddit search via the official OAuth API. robots.txt disallows anonymous crawl."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from engine.collect.http import FetchError, default_headers
from engine.collect.social.config import INTENT_QUERIES, REDDIT_SUBS, env
from engine.leads.event_models import RawEvent, strip_personal_contacts


def collect_reddit() -> tuple[list[RawEvent], list[dict]]:
    token = _token()
    if not token:
        return [], [
            {
                "source": "reddit",
                "status": "skipped",
                "detail": (
                    "reddit.com/robots.txt disallows anonymous crawl. Set REDDIT_CLIENT_ID and "
                    "REDDIT_CLIENT_SECRET for the official API (https://www.reddit.com/prefs/apps)."
                ),
            }
        ]
    items: list[RawEvent] = []
    for sub in REDDIT_SUBS:
        for query in INTENT_QUERIES[:8]:
            items.extend(_search(token, sub, query))
    return items, [{"source": "reddit", "status": "ok", "count": len(items)}]


def _token() -> str | None:
    ready = env("REDDIT_ACCESS_TOKEN")
    if ready:
        return ready
    client_id, secret = env("REDDIT_CLIENT_ID"), env("REDDIT_CLIENT_SECRET")
    if not client_id or not secret:
        return None
    auth = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token",
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers=default_headers({"Authorization": _basic(client_id, secret)}),
        method="POST",
    )
    try:
        with urllib.request.urlopen(auth, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception as exc:
        raise FetchError("reddit token failed") from exc
    return data.get("access_token")


def _basic(client_id: str, secret: str) -> str:
    import base64

    raw = base64.b64encode(f"{client_id}:{secret}".encode()).decode("ascii")
    return f"Basic {raw}"


def _search(token: str, sub: str, query: str) -> list[RawEvent]:
    url = (
        f"https://oauth.reddit.com/r/{urllib.parse.quote(sub)}/search"
        f"?{urllib.parse.urlencode({'q': query, 'restrict_sr': '1', 'sort': 'new', 'limit': '15', 't': 'month'})}"
    )
    req = urllib.request.Request(
        url, headers=default_headers({"Authorization": f"Bearer {token}", "Accept": "application/json"})
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return []
    children = (data.get("data") or {}).get("children") or []
    out = []
    for child in children:
        post = child.get("data") or {}
        permalink = post.get("permalink") or ""
        title = post.get("title")
        body = post.get("selftext") or ""
        out.append(
            RawEvent(
                source="reddit",
                source_url=f"https://www.reddit.com{permalink}" if permalink else "https://www.reddit.com/",
                title=title,
                text=strip_personal_contacts(f"{title or ''} {body}".strip()),
                extra={"subreddit": post.get("subreddit"), "query": query},
            )
        )
    return out
