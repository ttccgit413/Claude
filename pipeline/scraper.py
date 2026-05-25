"""
Scrapes Google Maps via Playwright and extracts email/Instagram from business websites.
"""
import datetime
import json
import logging
import os
import random
import re
import time
from urllib.parse import quote, unquote

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

_IG_HANDLE_RE = re.compile(
    r'instagram\.com/(?!p/|reel/|explore/)([A-Za-z0-9._]{1,30})/?',
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
_IGNORED_EMAIL_DOMAINS = {"example.com", "sentry.io", "wixpress.com", "amazonaws.com"}

_DAILY_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".scraper_daily.json")

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ── Daily rate-limit helpers ──────────────────────────────────────────────────

def _load_daily_state() -> dict:
    today = datetime.date.today().isoformat()
    try:
        with open(_DAILY_STATE_PATH) as f:
            state = json.load(f)
        if state.get("date") == today:
            return state
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    return {"date": today, "count": 0}


def _save_daily_state(count: int) -> None:
    today = datetime.date.today().isoformat()
    try:
        with open(_DAILY_STATE_PATH, "w") as f:
            json.dump({"date": today, "count": count}, f)
    except OSError as e:
        logging.warning(f"[scraper] could not write daily state: {e}")


# ── Website data extraction ───────────────────────────────────────────────────

_CONTACT_PATHS = ["/contact", "/contact-us", "/about", "/about-us", "/get-in-touch"]


def _clean_email(candidate: str) -> str | None:
    candidate = candidate.lower()
    domain = candidate.split("@")[1]
    if "noreply" in candidate or domain in _IGNORED_EMAIL_DOMAINS:
        return None
    return candidate


def _parse_html(html: str) -> tuple[str | None, str | None]:
    """Extract (email, ig_handle) from raw HTML."""
    email = None
    m = _EMAIL_RE.search(html)
    if m:
        email = _clean_email(m.group(0))

    ig_handle = None
    ig_matches = _IG_HANDLE_RE.findall(html)
    if ig_matches:
        handle = ig_matches[0].split("?")[0].strip("/")
        ig_handle = handle if len(handle) >= 2 else None

    return email, ig_handle


def _fetch_html(url: str) -> str | None:
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": _USER_AGENT})
        return resp.text
    except Exception:
        return None


def _extract_from_website(url: str) -> tuple[str | None, str | None]:
    """
    Fetch the business website and return (email, ig_handle).
    Checks the homepage first, then common contact pages if no email is found.
    """
    if not url:
        return None, None

    base = url.rstrip("/")

    # Always collect IG handle from homepage (most reliable location)
    homepage_html = _fetch_html(url)
    if homepage_html is None:
        return None, None

    email, ig_handle = _parse_html(homepage_html)
    if email:
        return email, ig_handle

    # No email on homepage — try contact pages
    for path in _CONTACT_PATHS:
        html = _fetch_html(base + path)
        if html is None:
            continue
        contact_email, contact_ig = _parse_html(html)
        if contact_email:
            # Keep homepage IG handle if we already found one
            return contact_email, ig_handle or contact_ig

    return None, ig_handle


# ── Playwright helpers ────────────────────────────────────────────────────────

def _dismiss_consent(page) -> None:
    try:
        btn = page.wait_for_selector(
            'button[aria-label*="Accept"], button:has-text("Accept all"), '
            'form[action*="consent"] button',
            timeout=3000,
        )
        if btn:
            btn.click()
            page.wait_for_timeout(800)
    except Exception:
        pass


def _collect_result_cards(page, session_max: int) -> list:
    cards = []
    last_count = 0
    no_change_cycles = 0

    while len(cards) < session_max:
        cards = page.query_selector_all('div[role="feed"] > div[jsaction]')

        # Check for end-of-results sentinel
        if page.query_selector('span:has-text("You\'ve reached the end of the list")'):
            break

        if len(cards) == last_count:
            no_change_cycles += 1
            if no_change_cycles >= 3:
                break
        else:
            no_change_cycles = 0

        last_count = len(cards)

        page.evaluate('(el => el && el.scrollBy(0, 800))(document.querySelector(\'div[role="feed"]\'))')
        page.wait_for_timeout(random.randint(1000, 2000))

    return list(cards[:session_max])


def _extract_website(page) -> str:
    el = page.query_selector('[data-item-id="authority"] a, a[data-item-id*="website"]')
    if not el:
        return ""
    href = el.get_attribute("href") or ""
    if "google.com/url" in href:
        m = re.search(r'[?&]q=([^&]+)', href)
        if m:
            return unquote(m.group(1))
    return href


def _extract_info_field(page, keywords: list[str]) -> str:
    for kw in keywords:
        el = page.query_selector(f'[data-item-id*="{kw.lower()}"], [aria-label*="{kw}"]')
        if el:
            text_el = el.query_selector("span span") or el
            val = text_el.inner_text().strip()
            if val:
                return val
    return ""


def _extract_detail_panel(page) -> dict | None:
    try:
        name_el = page.query_selector('div[role="main"] h1')
        name = name_el.inner_text().strip() if name_el else ""
        if not name:
            return None

        rating = None
        rating_el = page.query_selector('div[role="main"] span[aria-label*="stars"]')
        if rating_el:
            aria = rating_el.get_attribute("aria-label") or ""
            m = re.search(r'([\d.]+)\s+star', aria)
            if m:
                rating = float(m.group(1))

        review_count = 0
        review_el = page.query_selector('div[role="main"] span[aria-label*="review"]')
        if review_el:
            aria = review_el.get_attribute("aria-label") or ""
            m = re.search(r'([\d,]+)\s+review', aria)
            if m:
                review_count = int(m.group(1).replace(",", ""))

        category = ""
        cat_el = page.query_selector('div[role="main"] button[jsaction*="category"]')
        if cat_el:
            category = cat_el.inner_text().strip()

        address = _extract_info_field(page, ["address", "Address"])
        phone = _extract_info_field(page, ["phone", "Phone number"])
        website = _extract_website(page)

        return {
            "name": name,
            "address": address,
            "website": website,
            "phone": phone,
            "google_rating": rating,
            "google_review_count": review_count,
            "category": category,
        }
    except Exception:
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def scrape_google_maps(query: str, location: str, max_items: int = 100) -> list[dict]:
    """
    Scrape Google Maps with Playwright and return raw business records.
    Each record includes name, address, website, email, phone,
    google_rating, google_review_count, category, instagram_handle.
    Records without an email are filtered out.
    """
    max_daily = int(os.environ.get("SCRAPER_MAX_DAILY", "200"))
    state = _load_daily_state()
    daily_count = state["count"]

    if daily_count >= max_daily:
        logging.warning(f"[scraper] daily limit reached ({daily_count}/{max_daily}) — returning []")
        return []

    session_max = min(max_items, max_daily - daily_count)
    results = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": 1280, "height": 900},
                user_agent=_USER_AGENT,
            )

            search_url = (
                f"https://www.google.com/maps/search/"
                f"{quote(query + ' ' + location)}/?hl=en"
            )
            page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            _dismiss_consent(page)
            page.wait_for_selector('div[role="feed"]', timeout=15000)

            cards = _collect_result_cards(page, session_max)
            logging.info(f"[scraper] found {len(cards)} result cards for '{query} {location}'")

            for card in cards:
                try:
                    card.click()
                    page.wait_for_selector('div[role="main"] h1', timeout=8000)
                    page.wait_for_timeout(random.randint(600, 1500))

                    partial = _extract_detail_panel(page)
                    if not partial:
                        continue

                    email, ig_handle = _extract_from_website(partial.get("website", ""))
                    if not email:
                        continue

                    results.append({
                        **partial,
                        "email": email.strip().lower(),
                        "instagram_handle": ig_handle,
                    })
                    logging.info(f"[scraper] ✓ {partial['name']} ({email})")

                except Exception as e:
                    logging.debug(f"[scraper] skipped card: {e}")
                    continue

                time.sleep(random.uniform(1, 3))

            browser.close()

    except Exception as e:
        logging.warning(f"[scraper] Playwright session failed: {e}")

    finally:
        new_count = daily_count + len(results)
        _save_daily_state(new_count)
        if new_count >= max_daily:
            logging.warning(f"[scraper] daily limit hit — {len(results)} results this session")

    return results
