"""Playwright session runner for the team's own logged-in browsers.

Requires the optional `playwright` package and a stored storage_state file. No password
typing, no account creation, no captcha solver: if the site shows a login wall the run
stops and records SessionExpired.
"""

from __future__ import annotations

from collections.abc import Callable

from engine.collect.social.session import SessionExpired, looks_logged_out, playwright_storage_path
from engine.collect.social.throttle import Throttle


def playwright_available() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return True


def crawl_pages(
    platform: str,
    urls: list[str],
    extract: Callable[[str, str], list[dict]],
    throttle: Throttle,
) -> tuple[list[dict], str | None]:
    """Visit urls with the stored session. Returns (extracted dicts, skip reason)."""
    state = playwright_storage_path(platform)
    if state is None:
        return [], f"no {platform} storage_state or cookies file"
    if not playwright_available():
        return [], "playwright not installed (pip install playwright && playwright install chromium)"
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    found: list[dict] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(state), locale="en-US")
            page = context.new_page()
            for url in urls:
                if not throttle.allow():
                    break
                throttle.wait()
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                    page.wait_for_timeout(1500)
                except PlaywrightTimeout:
                    continue
                html = page.content()
                if looks_logged_out(html):
                    context.close()
                    browser.close()
                    raise SessionExpired(f"{platform} session expired or hit a login wall")
                found.extend(extract(url, html))
            context.close()
            browser.close()
    except SessionExpired:
        raise
    except Exception as exc:  # browser missing, sandbox, etc.
        return found, f"{platform} playwright failed: {type(exc).__name__}"
    return found, None


def fetch_public_html(url: str, *, timeout_ms: int = 45_000) -> str:
    """Logged-out Playwright fetch of a public page. Empty string if Playwright is missing."""
    if not playwright_available():
        return ""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(locale="en-US")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(1200)
                return page.content()
            except PlaywrightTimeout:
                return ""
            finally:
                browser.close()
    except Exception:
        return ""
