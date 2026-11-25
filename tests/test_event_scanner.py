"""Unit tests for the daily event-lead scanner (no live social logins)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from engine.collect.event_feeds import park_row_wanted
from engine.collect.social import facebook, session, throttle
from engine.leads import event_extract, event_store
from engine.leads.event_models import RawEvent, strip_personal_contacts
from engine.leads.event_scan import run


class ParkSliceTests(unittest.TestCase):
    lo = date(2026, 11, 25)
    hi = date(2027, 3, 25)

    def test_tentative_festival_is_kept(self):
        row = {
            "permit_status": "Tentative",
            "reservation_start_date": "2026-12-12",
            "event_type": "Permit - Festival",
        }
        self.assertTrue(park_row_wanted(row, self.lo, self.hi))

    def test_waiting_decision_event_is_kept(self):
        row = {
            "permit_status": "Waiting Decision",
            "reservation_start_date": "2026-12-01",
            "event_type": "Permit - Event Athletic",
        }
        self.assertTrue(park_row_wanted(row, self.lo, self.hi))

    def test_wedding_without_held_status_is_kept(self):
        row = {
            "permit_status": "Tentative",
            "reservation_start_date": "2027-02-14",
            "event_type": "Venue Rental - Wedding",
        }
        self.assertTrue(park_row_wanted(row, self.lo, self.hi))

    def test_denied_is_dropped(self):
        row = {
            "permit_status": "Stage Denied",
            "reservation_start_date": "2026-12-12",
            "event_type": "Venue Rental - Wedding",
        }
        self.assertFalse(park_row_wanted(row, self.lo, self.hi))

    def test_past_is_dropped(self):
        row = {
            "permit_status": "Approved",
            "reservation_start_date": "2026-11-01",
            "event_type": "Permit - Festival",
        }
        self.assertFalse(park_row_wanted(row, self.lo, self.hi))


class ExtractTests(unittest.TestCase):
    def test_geo_fence(self):
        self.assertEqual(event_extract.geo_region("wedding in Hammond IN"), "nw_indiana")
        self.assertEqual(event_extract.geo_region("festival downtown Milwaukee"), "milwaukee")
        chicago = RawEvent(
            source="facebook",
            source_url="https://www.facebook.com/events/1",
            title="Looking for a DJ in Chicago",
            text="Need a DJ for a quinceanera in Chicago",
        )
        self.assertTrue(event_extract.in_fence(chicago))
        elsewhere = RawEvent(
            source="facebook",
            source_url="https://www.facebook.com/events/2",
            title="Austin TX wedding",
            text="looking for a DJ in Austin Texas",
        )
        self.assertFalse(event_extract.in_fence(elsewhere))

    def test_vendor_needs_and_score(self):
        item = RawEvent(
            source="chicago_park_district",
            source_url="https://data.cityofchicago.org/d/pk66-w54g",
            title="Need a caterer and a DJ",
            start="2026-12-20",
            venue="Grant Park",
            city="Chicago",
            region="chicagoland",
            text="Need a caterer and a DJ for 200 guests",
            host_org="Friends of Grant Park",
        )
        extracted = event_extract.enrich(item, use_llm=False)
        self.assertIn("dj", extracted["vendor_needs"])
        self.assertIn("caterer", extracted["vendor_needs"])
        self.assertEqual(extracted["est_size"], 200)
        row = {**item.to_dict(), **extracted, "start": extracted["date"]}
        row["score"] = event_extract.score(row, date(2026, 11, 25))
        self.assertGreater(row["score"], 40)

    def test_dedup_same_name_date_venue(self):
        a = {
            "item_hash": "a",
            "event_name": "Summer Fest",
            "start": "2026-07-04",
            "venue": "Grant Park",
            "score": 10,
        }
        b = {
            "item_hash": "b",
            "event_name": "Summer Fest",
            "start": "2026-07-04",
            "venue": "Grant Park",
            "score": 40,
        }
        kept = event_extract.dedup([a, b])
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["item_hash"], "b")

    def test_phones_stripped_from_text(self):
        text = strip_personal_contacts("Call Jane at (312) 555-0199 or jane@gmail.com")
        self.assertNotIn("555", text)
        self.assertNotIn("jane@gmail.com", text)
        self.assertIn("[phone withheld]", text)
        self.assertIn("[email withheld]", text)

    def test_item_hash_stable(self):
        a = RawEvent(source="rss", source_url="https://ex.test/e", title="Fest", start="2026-12-01")
        b = RawEvent(source="rss", source_url="https://ex.test/e", title="Fest", start="2026-12-01")
        self.assertEqual(a.item_hash(), b.item_hash())


class StoreTests(unittest.TestCase):
    def test_merge_keeps_review_status(self):
        previous = {
            "abc": {
                "item_hash": "abc",
                "content_hash": "old",
                "title": "Fest",
                "review_status": "contacted",
                "first_seen": "2026-11-01T00:00:00",
                "score": 1,
            }
        }
        incoming = [{"item_hash": "abc", "content_hash": "new", "title": "Fest renamed", "score": 9}]
        now = datetime(2026, 11, 25, 7, 0, tzinfo=ZoneInfo("America/Chicago"))
        merged = event_store.merge(previous, incoming, now)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["review_status"], "contacted")
        self.assertEqual(merged[0]["changed_at"][:10], "2026-11-25")
        self.assertFalse(merged[0]["is_new"])

    def test_sanitize_drops_cookies(self):
        row = {
            "title": "Fest",
            "extra": {"cookie": "secret", "page": "https://www.facebook.com/events/"},
            "cookies": "c_user=1",
        }
        out = event_store.sanitize_for_ship(row)
        self.assertNotIn("cookies", out)
        self.assertNotIn("cookie", out["extra"])
        self.assertEqual(out["extra"]["page"], "https://www.facebook.com/events/")


class SessionTests(unittest.TestCase):
    def test_looks_logged_out(self):
        self.assertTrue(session.looks_logged_out("<html>Log in to continue</html>"))
        self.assertFalse(session.looks_logged_out("<html>c_user=123 logout</html>"))

    def test_cookie_header_from_json_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facebook.cookies.json"
            path.write_text(
                json.dumps([{"name": "c_user", "value": "99", "domain": ".facebook.com"}]),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"EVENT_SCAN_SECRETS_DIR": tmp, "FB_COOKIE": ""}, clear=False):
                os.environ.pop("FB_COOKIE", None)
                os.environ.pop("FB_STORAGE_STATE", None)
                os.environ.pop("FB_COOKIES_FILE", None)
                header = session.load_cookie_header("facebook")
            self.assertIn("c_user=99", header or "")

    def test_playwright_storage_from_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"FB_COOKIE": "c_user=1; xs=abc", "EVENT_SCAN_SECRETS_DIR": tmp}):
                os.environ.pop("FB_STORAGE_STATE", None)
                path = session.playwright_storage_path("facebook")
                self.assertIsNotNone(path)
                data = json.loads(path.read_text(encoding="utf-8"))
                names = {c["name"] for c in data["cookies"]}
                self.assertIn("c_user", names)

    def test_facebook_extract_events_and_groups(self):
        html = """
        <html><title>Chicago events</title>
        <a href="https://www.facebook.com/events/12345">event</a>
        <a href="https://www.facebook.com/groups/nwiwedding/posts/99">group</a>
        <p>Looking for a DJ in Chicago for a wedding next month with 150 guests.</p>
        </html>
        """
        rows = facebook._extract("https://www.facebook.com/search/events?q=wedding", html)
        urls = {r["url"] for r in rows}
        self.assertTrue(any("events/12345" in u for u in urls))
        self.assertTrue(any("/groups/" in u for u in urls))

    def test_session_expired_is_graceful(self):
        with patch(
            "engine.collect.social.facebook._via_playwright", side_effect=session.SessionExpired("login wall")
        ):
            with patch("engine.collect.social.facebook._via_apify", return_value=[]):
                items, notes = facebook.collect_facebook(authenticated=True)
        self.assertEqual(items, [])
        self.assertTrue(any(n.get("status") == "session_expired" for n in notes))


class ThrottleTests(unittest.TestCase):
    def test_per_run_cap_and_jitter(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "social_throttle.json"
            slept = []
            with patch.object(throttle, "STATE", state):
                t = throttle.Throttle("facebook", min_delay=2, max_delay=3, max_per_run=2, max_per_hour=10)
                self.assertTrue(t.allow())
                t.wait(sleep=slept.append)
                self.assertTrue(t.allow())
                t.wait(sleep=slept.append)
                self.assertFalse(t.allow())
                self.assertEqual(t.remaining(), 0)
                self.assertGreaterEqual(slept[0], 2)
                self.assertLessEqual(slept[0], 3)

    def test_env_overrides(self):
        with patch.dict(os.environ, {"FB_MAX_PER_RUN": "4", "FB_MIN_DELAY": "1.5"}):
            t = throttle.Throttle("facebook", min_delay=10, max_delay=20, max_per_run=30)
            self.assertEqual(t.max_per_run, 4)
            self.assertEqual(t.min_delay, 1.5)


class ScanGateTests(unittest.TestCase):
    def test_require_chicago_hour_skips(self):
        fake = datetime(2026, 11, 25, 15, 0, tzinfo=ZoneInfo("America/Chicago"))
        with patch("engine.leads.event_scan.chicago_now", return_value=fake):
            with patch("engine.leads.event_scan.collect_all") as collect:
                code = run(public_only=True, use_llm=False, require_chicago_hour=True)
        self.assertEqual(code, 0)
        collect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
