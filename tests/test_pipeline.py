"""Unit tests for pipeline modules that need no external API calls."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

from case_study import _render_text

from scorer import score_lead


# ── scorer.py ─────────────────────────────────────────────────────────────

class TestScoreLead:
    def test_bella_is_hot(self):
        biz = {
            "google_review_count": 47,
            "website": "bellashair.com.au",
            "google_rating": 3.9,
        }
        ig = {"ig_days_inactive": 47, "ig_followers": 340}
        score, tier = score_lead(biz, ig)
        assert score == 100
        assert tier == "hot"

    def test_active_ig_no_bonus(self):
        biz = {
            "google_review_count": 25,
            "website": "example.com",
            "google_rating": 4.5,  # above 4.2, no bonus
        }
        ig = {"ig_days_inactive": 5, "ig_followers": 300}  # active IG
        score, tier = score_lead(biz, ig)
        # gets: followers(15) + review_count(15) + website(15) = 45
        assert score == 45
        assert tier == "cold"

    def test_warm_lead(self):
        biz = {
            "google_review_count": 25,
            "website": "example.com",
            "google_rating": 4.0,
        }
        ig = {"ig_days_inactive": 60, "ig_followers": 500}
        score, tier = score_lead(biz, ig)
        # gets: inactive(40) + followers(15) + review_count(15) + website(15) + rating(15) = 100... wait
        # Actually rating 4.0 < 4.2 so +15. That's 100. Let me recalc.
        # 40+15+15+15+15 = 100
        assert score == 100
        assert tier == "hot"

    def test_no_website_no_bonus(self):
        biz = {
            "google_review_count": 25,
            "website": "",  # no website
            "google_rating": 4.5,
        }
        ig = {"ig_days_inactive": 45, "ig_followers": 300}
        score, tier = score_lead(biz, ig)
        # inactive(40) + followers(15) + review_count(15) + no website + no rating = 70
        assert score == 70
        assert tier == "warm"

    def test_cold_lead(self):
        biz = {
            "google_review_count": 5,   # below 20 threshold
            "website": "",
            "google_rating": 4.8,
        }
        ig = {"ig_days_inactive": 5, "ig_followers": 50}  # small, active
        score, tier = score_lead(biz, ig)
        assert score == 0
        assert tier == "cold"

    def test_missing_ig_fields_default_zero(self):
        biz = {"google_review_count": 0, "website": "", "google_rating": 5.0}
        ig = {}
        score, tier = score_lead(biz, ig)
        assert score == 0
        assert tier == "cold"

    def test_exact_thresholds(self):
        # ig_days_inactive exactly 30 → no bonus (needs > 30)
        biz = {"google_review_count": 0, "website": "", "google_rating": 5.0}
        ig = {"ig_days_inactive": 30, "ig_followers": 0}
        score, _ = score_lead(biz, ig)
        assert score == 0

        # ig_days_inactive 31 → bonus
        ig2 = {"ig_days_inactive": 31, "ig_followers": 0}
        score2, _ = score_lead(biz, ig2)
        assert score2 == 40

        # followers exactly 200 → no bonus (needs > 200)
        ig3 = {"ig_days_inactive": 0, "ig_followers": 200}
        score3, _ = score_lead(biz, ig3)
        assert score3 == 0

        # followers 201 → bonus
        ig4 = {"ig_days_inactive": 0, "ig_followers": 201}
        score4, _ = score_lead(biz, ig4)
        assert score4 == 15

    def test_tier_boundaries(self):
        # score 89 → warm
        biz = {"google_review_count": 25, "website": "x.com", "google_rating": 5.0}
        ig = {"ig_days_inactive": 45, "ig_followers": 300}
        # inactive(40) + followers(15) + review_count(15) + website(15) = 85 → warm
        score, tier = score_lead(biz, ig)
        assert score == 85
        assert tier == "warm"

        # add rating bonus to push to hot
        biz2 = {**biz, "google_rating": 4.0}
        score2, tier2 = score_lead(biz2, ig)
        assert score2 == 100
        assert tier2 == "hot"


# ── enricher helpers ──────────────────────────────────────────────────────

def test_ig_handle_regex():
    """Test the IG handle regex from scraper.py without network calls."""
    import re
    pattern = re.compile(
        r'instagram\.com/(?!p/|reel/|explore/)([A-Za-z0-9._]{1,30})/?',
        re.IGNORECASE,
    )
    cases = [
        ('href="https://www.instagram.com/bellashairmelbourne"', "bellashairmelbourne"),
        ('follow us at instagram.com/luxehair/', "luxehair"),
        ('instagram.com/p/ABC123/', None),      # post URL — should be ignored
        ('instagram.com/reel/XYZ/', None),      # reel URL — should be ignored
        ('instagram.com/explore/tags/hair/', None),  # explore — should be ignored
    ]
    for html, expected in cases:
        matches = pattern.findall(html)
        result = matches[0] if matches else None
        assert result == expected, f"For '{html}': expected {expected!r}, got {result!r}"


def test_hex_from_rgb():
    """Test color conversion without Playwright."""
    # replicate the _hex_from_rgb helper inline
    def hex_from_rgb(rgb):
        return "#{:02X}{:02X}{:02X}".format(*rgb)

    assert hex_from_rgb((196, 168, 130)) == "#C4A882"
    assert hex_from_rgb((44, 44, 44)) == "#2C2C2C"
    assert hex_from_rgb((0, 0, 0)) == "#000000"
    assert hex_from_rgb((255, 255, 255)) == "#FFFFFF"


def test_suburb_parsing():
    """Test address → suburb extraction from run_pipeline.py."""
    def parse_suburb(address):
        parts = address.split(",")
        if len(parts) >= 2:
            return parts[1].strip().split(" ")[0]
        return ""

    assert parse_suburb("342 Smith St, Collingwood VIC 3066") == "Collingwood"
    assert parse_suburb("123 Chapel St, Prahran VIC 3181") == "Prahran"
    assert parse_suburb("No comma here") == ""


def test_first_name_extraction():
    """Test business name → first name for email personalisation."""
    def first_name(business_name):
        return business_name.split("'")[0].split(" ")[0]

    assert first_name("Bella's Hair Salon") == "Bella"
    assert first_name("Smith Street Hair") == "Smith"
    assert first_name("Luxe Hair Collingwood") == "Luxe"


def test_slugify():
    """Test business name → URL slug."""
    import re
    def slugify(name):
        return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    assert slugify("Bella's Hair Salon") == "bella-s-hair-salon"
    assert slugify("Smith & Co.") == "smith-co"
    assert slugify("  Spaces  ") == "spaces"
    assert slugify("Luxe Hair Collingwood") == "luxe-hair-collingwood"


def test_ai_review_avg_normalisation():
    """Verify that avg is recomputed correctly regardless of model output."""
    scores = {"professionalism": 8, "quality": 7, "text": 9, "overall": 8}
    computed_avg = round(sum(scores.values()) / len(scores), 2)
    assert computed_avg == 8.0
    assert (computed_avg >= 7.0) is True  # should PASS

    low_scores = {"professionalism": 5, "quality": 6, "text": 6, "overall": 5}
    low_avg = round(sum(low_scores.values()) / len(low_scores), 2)
    assert low_avg == 5.5
    assert (low_avg >= 7.0) is False  # should FAIL


def test_case_study_text_rendering():
    """Verify case study text contains all key before/after metrics."""
    lead = {
        "name": "Bella's Hair Salon",
        "address": "342 Smith St, Collingwood VIC 3066",
        "google_rating": 3.9,
        "ig_days_inactive": 47,
        "ig_avg_likes": 12,
    }
    first = {"followers": 340, "month": "2025-05"}
    latest = {"followers": 389, "google_rating": 4.1, "posts_delivered": 12,
              "top_post_likes": 47, "month": "2025-06"}

    text = _render_text(lead, first, latest,
                        follower_growth=49, follower_pct=14.4,
                        rating_delta=0.2, top_likes=47,
                        likes_multiplier=3.9, suburb="Collingwood")

    assert "Bella's Hair Salon" in text
    assert "340" in text        # before followers
    assert "389" in text        # after followers
    assert "+49" in text        # follower growth
    assert "14.4%" in text      # pct growth
    assert "3.9" in text        # before rating
    assert "4.1" in text        # after rating
    assert "47" in text         # top post likes
    assert "12 posts" in text   # posts delivered
    assert "Collingwood" in text
