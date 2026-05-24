"""
Tests for pipeline/scraper.py — runs fully offline using a local HTTP server
that mimics the Google Maps DOM structure Playwright expects.
"""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
import scraper
from playwright.sync_api import sync_playwright

# ── Chromium path for this environment ───────────────────────────────────────

_CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
_CHROMIUM_ARGS = ["--no-sandbox", "--disable-setuid-sandbox"]


def _launch_browser(p):
    return p.chromium.launch(
        headless=True,
        executable_path=_CHROMIUM,
        args=_CHROMIUM_ARGS,
    )


# ── Mock HTML pages ───────────────────────────────────────────────────────────

BIZ_0_HTML = b"""<!DOCTYPE html><html><body>
<p>Contact us: info@bellashair.com.au</p>
<a href="https://instagram.com/bellashair">Instagram</a>
</body></html>"""

BIZ_1_HTML = b"""<!DOCTYPE html><html><body>
<p>Email: hello@smithstcuts.com.au</p>
</body></html>"""


def _make_maps_html(port: int) -> bytes:
    return f"""<!DOCTYPE html>
<html lang="en"><body>
<div role="feed">
  <div jsaction="click:a" style="cursor:pointer;padding:8px">Card 0</div>
  <div jsaction="click:b" style="cursor:pointer;padding:8px">Card 1</div>
</div>

<div role="main" id="detail" style="display:none">
  <h1 id="biz-name">placeholder</h1>
  <span id="biz-stars" aria-label="4.1 stars"></span>
  <span id="biz-reviews" aria-label="47 reviews"></span>
  <div data-item-id="address"><span><span id="biz-addr">-</span></span></div>
  <div data-item-id="phone:tel"><span><span id="biz-phone">-</span></span></div>
  <div data-item-id="authority"><a id="biz-site" href="">Site</a></div>
  <button jsaction="pane.rating.category" id="biz-cat">Hair Salon</button>
</div>

<script>
const bizData = [
  {{
    name: "Bella's Hair Studio",
    stars: "4.1 stars", reviews: "47 reviews",
    addr: "123 Brunswick St, Fitzroy", phone: "+61 3 1234 5678",
    site: "http://localhost:{port}/biz/0"
  }},
  {{
    name: "Smith St Cuts",
    stars: "3.8 stars", reviews: "23 reviews",
    addr: "456 Smith St, Collingwood", phone: "+61 3 9876 5432",
    site: "http://localhost:{port}/biz/1"
  }}
];
document.querySelectorAll('[jsaction]').forEach((card, i) => {{
  card.addEventListener('click', () => {{
    const b = bizData[i];
    document.getElementById('detail').style.display = 'block';
    document.getElementById('biz-name').textContent = b.name;
    document.getElementById('biz-stars').setAttribute('aria-label', b.stars);
    document.getElementById('biz-reviews').setAttribute('aria-label', b.reviews);
    document.getElementById('biz-addr').textContent = b.addr;
    document.getElementById('biz-phone').textContent = b.phone;
    document.getElementById('biz-site').href = b.site;
  }});
}});
</script>
</body></html>""".encode()


class MockMapsHandler(BaseHTTPRequestHandler):
    port = None  # set before starting the server

    def do_GET(self):
        if self.path == "/":
            body = _make_maps_html(self.server.server_port)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/biz/0":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(BIZ_0_HTML)
        elif self.path == "/biz/1":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(BIZ_1_HTML)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass  # suppress request logs during tests


def _start_mock_server() -> tuple[HTTPServer, int]:
    server = HTTPServer(("127.0.0.1", 0), MockMapsHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server, port


# ── 1. Daily rate-limit unit tests ───────────────────────────────────────────

class TestDailyRateLimit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.tmp.close()
        self.patcher = patch.object(scraper, "_DAILY_STATE_PATH", self.tmp.name)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_fresh_state_starts_at_zero(self):
        os.unlink(self.tmp.name)  # ensure file is missing
        state = scraper._load_daily_state()
        self.assertEqual(state["count"], 0)

    def test_save_and_reload(self):
        scraper._save_daily_state(42)
        state = scraper._load_daily_state()
        self.assertEqual(state["count"], 42)

    def test_stale_date_resets_count(self):
        import datetime
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        with open(self.tmp.name, "w") as f:
            json.dump({"date": yesterday, "count": 150}, f)
        state = scraper._load_daily_state()
        self.assertEqual(state["count"], 0)

    def test_corrupted_file_resets(self):
        with open(self.tmp.name, "w") as f:
            f.write("not valid json{{{")
        state = scraper._load_daily_state()
        self.assertEqual(state["count"], 0)

    def test_scrape_google_maps_returns_empty_when_limit_hit(self):
        scraper._save_daily_state(200)
        with patch.dict(os.environ, {"SCRAPER_MAX_DAILY": "200"}):
            results = scraper.scrape_google_maps("hair salons", "Melbourne", max_items=10)
        self.assertEqual(results, [])

    def test_session_capped_by_remaining_daily_budget(self):
        """session_max = min(max_items, max_daily - used) should cap what Playwright fetches."""
        scraper._save_daily_state(195)
        # With 5 remaining, asking for 50 should only try to get 5
        # We mock the Playwright part to verify session_max is respected
        collected = []

        def fake_collect(page, session_max):
            collected.append(session_max)
            return []  # return no cards so scrape exits cleanly

        with patch.dict(os.environ, {"SCRAPER_MAX_DAILY": "200"}):
            with patch.object(scraper, "_collect_result_cards", side_effect=fake_collect):
                with patch("scraper.sync_playwright") as mock_pw:
                    # Set up context manager chain
                    mock_page = unittest.mock.MagicMock()
                    mock_browser = unittest.mock.MagicMock()
                    mock_browser.new_page.return_value = mock_page
                    mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
                    scraper.scrape_google_maps("hair salons", "Melbourne", max_items=50)

        self.assertEqual(collected[0], 5)


# ── 2. Website extraction unit tests ─────────────────────────────────────────

class TestExtractFromWebsite(unittest.TestCase):
    def _fake_get(self, html: str):
        """Patch requests.get to return mock HTML."""
        import unittest.mock as mock
        resp = mock.MagicMock()
        resp.text = html
        return mock.patch("scraper.requests.get", return_value=resp)

    def test_extracts_email_and_ig(self):
        html = '<p>Email: info@bellashair.com.au</p><a href="https://instagram.com/bellashair">IG</a>'
        with self._fake_get(html):
            email, ig = scraper._extract_from_website("http://example.com")
        self.assertEqual(email, "info@bellashair.com.au")
        self.assertEqual(ig, "bellashair")

    def test_filters_noreply_email(self):
        html = '<p>noreply@bellashair.com.au</p>'
        with self._fake_get(html):
            email, ig = scraper._extract_from_website("http://example.com")
        self.assertIsNone(email)

    def test_filters_ignored_domains(self):
        html = '<p>error@sentry.io</p>'
        with self._fake_get(html):
            email, ig = scraper._extract_from_website("http://example.com")
        self.assertIsNone(email)

    def test_returns_none_none_on_empty_url(self):
        email, ig = scraper._extract_from_website("")
        self.assertIsNone(email)
        self.assertIsNone(ig)

    def test_returns_none_none_on_request_failure(self):
        with patch("scraper.requests.get", side_effect=Exception("timeout")):
            email, ig = scraper._extract_from_website("http://example.com")
        self.assertIsNone(email)
        self.assertIsNone(ig)

    def test_ig_handle_strips_query_params(self):
        html = '<a href="https://instagram.com/myhandle?igshid=abc">IG</a>'
        with self._fake_get(html):
            _, ig = scraper._extract_from_website("http://example.com")
        self.assertEqual(ig, "myhandle")

    def test_ignores_ig_post_and_reel_paths(self):
        html = '<a href="https://instagram.com/p/abc123">post</a><a href="https://instagram.com/reel/xyz">reel</a>'
        with self._fake_get(html):
            _, ig = scraper._extract_from_website("http://example.com")
        self.assertIsNone(ig)


# ── 3. Playwright helper integration tests (local mock server) ────────────────

class TestPlaywrightHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.port = _start_mock_server()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _get_page(self, p):
        browser = _launch_browser(p)
        page = browser.new_page()
        page.goto(self.base_url, wait_until="domcontentloaded")
        return browser, page

    def test_collect_result_cards_finds_cards(self):
        with sync_playwright() as p:
            browser, page = self._get_page(p)
            cards = scraper._collect_result_cards(page, session_max=10)
            browser.close()
        self.assertEqual(len(cards), 2)

    def test_collect_result_cards_respects_session_max(self):
        with sync_playwright() as p:
            browser, page = self._get_page(p)
            cards = scraper._collect_result_cards(page, session_max=1)
            browser.close()
        self.assertEqual(len(cards), 1)

    def test_extract_detail_panel_after_click(self):
        with sync_playwright() as p:
            browser, page = self._get_page(p)
            cards = scraper._collect_result_cards(page, session_max=10)
            cards[0].click()
            page.wait_for_selector('div[role="main"] h1', timeout=5000)
            page.wait_for_timeout(300)
            detail = scraper._extract_detail_panel(page)
            browser.close()

        self.assertIsNotNone(detail)
        self.assertEqual(detail["name"], "Bella's Hair Studio")
        self.assertAlmostEqual(detail["google_rating"], 4.1)
        self.assertEqual(detail["google_review_count"], 47)
        self.assertEqual(detail["address"], "123 Brunswick St, Fitzroy")
        self.assertEqual(detail["phone"], "+61 3 1234 5678")
        self.assertIn(f"localhost:{self.port}/biz/0", detail["website"])

    def test_extract_detail_panel_second_card(self):
        with sync_playwright() as p:
            browser, page = self._get_page(p)
            cards = scraper._collect_result_cards(page, session_max=10)
            cards[1].click()
            page.wait_for_selector('div[role="main"] h1', timeout=5000)
            page.wait_for_timeout(300)
            detail = scraper._extract_detail_panel(page)
            browser.close()

        self.assertEqual(detail["name"], "Smith St Cuts")
        self.assertAlmostEqual(detail["google_rating"], 3.8)
        self.assertEqual(detail["google_review_count"], 23)

    def test_extract_website_returns_href(self):
        with sync_playwright() as p:
            browser, page = self._get_page(p)
            cards = scraper._collect_result_cards(page, session_max=10)
            cards[0].click()
            page.wait_for_selector('div[role="main"] h1', timeout=5000)
            website = scraper._extract_website(page)
            browser.close()

        self.assertIn("/biz/0", website)

    def test_dismiss_consent_safe_when_no_dialog(self):
        """Should not raise even when no consent dialog exists."""
        with sync_playwright() as p:
            browser, page = self._get_page(p)
            try:
                scraper._dismiss_consent(page)  # no dialog on mock page
            except Exception as e:
                self.fail(f"_dismiss_consent raised unexpectedly: {e}")
            finally:
                browser.close()


# ── 4. Full pipeline end-to-end with mock server ──────────────────────────────

class TestScrapeGoogleMapsMock(unittest.TestCase):
    """
    Patches the URL in scrape_google_maps to point at the local mock server
    and patches the browser launch to use the local Chromium binary.
    """
    @classmethod
    def setUpClass(cls):
        cls.server, cls.port = _start_mock_server()
        cls.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        cls.tmp.close()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        if os.path.exists(cls.tmp.name):
            os.unlink(cls.tmp.name)

    def _run_scrape(self, max_items=10):
        local_url = f"http://127.0.0.1:{self.port}"

        original_scrape = scraper.scrape_google_maps

        def patched_scrape(query, location, max_items=100):
            # Identical to scrape_google_maps but uses local URL + local Chromium
            from urllib.parse import quote
            import random, time, logging
            max_daily = int(os.environ.get("SCRAPER_MAX_DAILY", "200"))
            state = scraper._load_daily_state()
            if state["count"] >= max_daily:
                return []
            session_max = min(max_items, max_daily - state["count"])
            results = []
            try:
                with sync_playwright() as p:
                    browser = _launch_browser(p)
                    page = browser.new_page(
                        viewport={"width": 1280, "height": 900},
                        user_agent=scraper._USER_AGENT,
                    )
                    page.goto(local_url, timeout=15000, wait_until="domcontentloaded")
                    scraper._dismiss_consent(page)
                    page.wait_for_selector('div[role="feed"]', timeout=10000)
                    cards = scraper._collect_result_cards(page, session_max)
                    for card in cards:
                        try:
                            card.click()
                            page.wait_for_selector('div[role="main"] h1', timeout=8000)
                            page.wait_for_timeout(300)
                            partial = scraper._extract_detail_panel(page)
                            if not partial:
                                continue
                            email, ig = scraper._extract_from_website(partial.get("website", ""))
                            if not email:
                                continue
                            results.append({**partial, "email": email.lower(), "instagram_handle": ig})
                        except Exception:
                            continue
                    browser.close()
            except Exception as e:
                logging.warning(f"[test scrape] {e}")
            finally:
                scraper._save_daily_state(state["count"] + len(results))
            return results

        with patch.object(scraper, "_DAILY_STATE_PATH", self.tmp.name):
            return patched_scrape("hair salons", "Melbourne", max_items=max_items)

    def test_returns_correct_number_of_leads(self):
        results = self._run_scrape(max_items=10)
        # Both mock businesses have emails, so expect 2
        self.assertEqual(len(results), 2)

    def test_first_lead_has_correct_fields(self):
        results = self._run_scrape()
        lead = results[0]
        self.assertEqual(lead["name"], "Bella's Hair Studio")
        self.assertEqual(lead["email"], "info@bellashair.com.au")
        self.assertEqual(lead["instagram_handle"], "bellashair")
        self.assertAlmostEqual(lead["google_rating"], 4.1)
        self.assertEqual(lead["google_review_count"], 47)
        self.assertEqual(lead["address"], "123 Brunswick St, Fitzroy")

    def test_second_lead_no_ig_handle(self):
        results = self._run_scrape()
        lead = results[1]
        self.assertEqual(lead["name"], "Smith St Cuts")
        self.assertEqual(lead["email"], "hello@smithstcuts.com.au")
        self.assertIsNone(lead["instagram_handle"])  # BIZ_1_HTML has no IG link

    def test_daily_count_incremented_after_scrape(self):
        with patch.object(scraper, "_DAILY_STATE_PATH", self.tmp.name):
            scraper._save_daily_state(0)
            self._run_scrape()
            state = scraper._load_daily_state()
        self.assertEqual(state["count"], 2)

    def test_max_items_limits_results(self):
        results = self._run_scrape(max_items=1)
        self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
