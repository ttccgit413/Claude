"""
Scores a lead 0-100. Returns (score, tier).
Tier: "hot" >= 90, "warm" 60-89, "cold" < 60.

Example — Bella's Hair Salon:
  days_inactive=47 (+40), followers=340 (+15),
  review_count=47 (+15), has_website (+15), rating=3.9 (+15) = 100 → HOT
"""


def score_lead(biz: dict, ig: dict) -> tuple[int, str]:
    score = 0

    if ig.get("ig_days_inactive", 0) > 30:
        score += 40

    if ig.get("ig_followers", 0) > 200:
        score += 15

    if biz.get("google_review_count", 0) > 20:
        score += 15

    if biz.get("website"):
        score += 15

    if (biz.get("google_rating") or 5.0) < 4.2:
        score += 15

    if score >= 90:
        tier = "hot"
    elif score >= 60:
        tier = "warm"
    else:
        tier = "cold"

    return score, tier
