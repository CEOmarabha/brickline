"""Open a headed browser so the team can log in once with a real account and save storage_state.

Does not type passwords, create accounts, or solve captchas. If a checkpoint appears, close the
window and retry later by hand.

    python -m engine.collect.social.save_session facebook
    python -m engine.collect.social.save_session instagram
    python -m engine.collect.social.save_session tiktok
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from engine.collect.social.config import secrets_dir
from engine.collect.social.session import Platform

START_URL: dict[Platform, str] = {
    "facebook": "https://www.facebook.com/login",
    "instagram": "https://www.instagram.com/accounts/login/",
    "tiktok": "https://www.tiktok.com/login",
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("platform", choices=("facebook", "instagram", "tiktok"))
    ap.add_argument(
        "--out",
        help="Write storage_state here (default secrets/<platform>.storage.json)",
    )
    args = ap.parse_args(argv)
    platform: Platform = args.platform
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("install Playwright: pip install playwright && playwright install chromium", file=sys.stderr)
        return 2
    dest = Path(args.out).expanduser() if args.out else secrets_dir() / f"{platform}.storage.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"A browser will open. Log in as the team's {platform} account, then return here and press Enter.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(locale="en-US")
        page = context.new_page()
        page.goto(START_URL[platform], wait_until="domcontentloaded")
        try:
            input("Press Enter after you see the logged-in home page (Ctrl-C to abort)... ")
        except KeyboardInterrupt:
            context.close()
            browser.close()
            print("aborted; nothing saved")
            return 1
        context.storage_state(path=str(dest))
        context.close()
        browser.close()
    print(f"saved {dest} (gitignored). Point {platform.upper()}_STORAGE_STATE at this file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
