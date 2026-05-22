"""
Enriches a raw lead with:
  1. Instagram stats (Instaloader, rate-limited)
  2. Brand colors + logo (Playwright + ColorThief)
  3. Top 3 competitor IG stats (re-query Apify for same suburb)
"""
import io
import os
import time
import datetime
import requests
import instaloader
from colorthief import ColorThief
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

_loader = None


def _get_loader() -> instaloader.Instaloader:
    global _loader
    if _loader is None:
        proxy = os.environ.get("BRIGHTDATA_PROXY_URL")
        _loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            save_metadata=False,
            quiet=True,
            requests_delay=2,
        )
        if proxy:
            import socks
            _loader.context._session.proxies = {
                "http": proxy,
                "https": proxy,
            }
    return _loader


def check_instagram(handle: str) -> dict:
    """
    Returns follower count, post count, days since last post, avg likes.
    Falls back to empty dict on any error.
    """
    if not handle:
        return {}
    try:
        loader = _get_loader()
        profile = instaloader.Profile.from_username(loader.context, handle)
        posts = list(profile.get_posts())

        if posts:
            last_post_dt = posts[0].date_utc
            days_inactive = (datetime.datetime.utcnow() - last_post_dt).days
            recent = posts[:10]
            avg_likes = sum(p.likes for p in recent) / len(recent) if recent else 0
        else:
            days_inactive = 999
            avg_likes = 0

        return {
            "ig_followers": profile.followers,
            "ig_following": profile.followees,
            "ig_post_count": profile.mediacount,
            "ig_days_inactive": days_inactive,
            "ig_avg_likes": round(avg_likes, 1),
        }
    except Exception:
        return {}


def _hex_from_rgb(rgb: tuple) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def scrape_brand(website_url: str) -> dict:
    """
    Returns primary_hex, secondary_hex, logo_url, font_vibe using
    Playwright (screenshot) + ColorThief for color extraction.
    """
    if not website_url:
        return {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(website_url, timeout=15000, wait_until="networkidle")

            # find logo
            logo_url = None
            for sel in ['img[src*="logo"]', 'header img', '.logo img', 'a.logo img']:
                el = page.query_selector(sel)
                if el:
                    src = el.get_attribute("src") or ""
                    if src:
                        logo_url = src if src.startswith("http") else website_url.rstrip("/") + "/" + src.lstrip("/")
                        break

            screenshot = page.screenshot(full_page=False)
            browser.close()

        img_io = io.BytesIO(screenshot)
        ct = ColorThief(img_io)
        dominant = ct.get_color(quality=1)
        palette = ct.get_palette(color_count=3, quality=1)
        secondary = palette[1] if len(palette) > 1 else dominant

        return {
            "brand_primary_hex": _hex_from_rgb(dominant),
            "brand_secondary_hex": _hex_from_rgb(secondary),
            "brand_logo_url": logo_url,
        }
    except Exception:
        return {}


def get_competitors(suburb: str, category: str) -> list[dict]:
    """
    Re-queries Apify for top 3 businesses in the same suburb/category,
    returning name, IG handle, posts_per_week estimate, and rating.
    """
    from scraper import scrape_google_maps

    try:
        results = scrape_google_maps(category, suburb, max_items=10)
        competitors = []
        for biz in results[:3]:
            ig = biz.get("instagram_handle")
            ig_stats = check_instagram(ig) if ig else {}
            # rough posts/week: total posts / account age in weeks (estimate 52 weeks/yr for new accounts)
            post_count = ig_stats.get("ig_post_count", 0)
            posts_per_week = round(post_count / 52, 1) if post_count else 0
            competitors.append({
                "name": biz["name"],
                "ig": ig or "",
                "posts_per_week": posts_per_week,
                "rating": biz.get("google_rating") or 0,
            })
            time.sleep(3)  # respect rate limits between competitor IG checks
        return competitors
    except Exception:
        return []
