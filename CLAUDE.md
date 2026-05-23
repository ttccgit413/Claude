# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An automated lead generation pipeline for a social media agency targeting local hair salons. It scrapes Google Maps daily, enriches leads with Instagram/brand data, scores them, generates AI-branded sample posts, runs a personalized email sequence, and delivers a live client report page — end to end.

## Repo layout

```
/
├── pipeline/          # Python — all data processing, external API calls
│   └── api/server.py  # FastAPI app deployed to Railway
├── apps/web/          # Next.js 16 — all user-facing pages and webhooks
│   ├── app/           # App Router pages and API routes
│   ├── components/    # LandingPage, ReportPage, ReviewDashboard
│   └── lib/           # airtable.ts, instagram.ts, google-business.ts, twilio.ts
├── tests/             # Python unit tests (pytest)
├── requirements.txt   # Python deps (pipeline + Railway server)
├── railway.json       # Railway deploy config
└── .env.example       # All required env vars documented here
```

## Two separate services

**Railway** runs the Python pipeline (long-running: Playwright, Instaloader, image gen). Vercel cron jobs call Railway's HTTP endpoints — they never execute Python directly.

**Vercel** runs the Next.js app (landing pages, report pages, review dashboard, webhooks). All Next.js API routes that need to trigger the pipeline do so via `PIPELINE_SERVICE_URL` (server-side only — never exposed to the browser).

## Commands

### Python pipeline
```bash
# Run tests
python -m pytest tests/test_pipeline.py -v

# Run a single test
python -m pytest tests/test_pipeline.py::test_posting_schedule_count -v

# Run the full pipeline manually (needs real API keys in .env)
python pipeline/run_pipeline.py --query "hair salons" --location "Melbourne" --limit 10

# Generate content package for a client
python pipeline/content_generator.py --client-slug bellas-hair-salon

# Generate case study
python pipeline/case_study.py --client-slug bellas-hair-salon

# Dry-run referral email check
python pipeline/referral_email.py --dry-run

# Start the Railway FastAPI server locally
uvicorn pipeline.api.server:app --reload --port 8000
```

### Next.js app (`apps/web/`)
```bash
npm run dev      # start dev server
npm run build    # typecheck + production build (run before committing)
npm run lint     # ESLint
```

Always run `npm run build` from `apps/web/` before committing — it catches TypeScript errors and the Airtable lazy-init pattern (initialising the client at module scope crashes the build).

## Data flow

```
Vercel cron (daily 06:00 AEST = 20:00 UTC)
  → POST /api/cron/pipeline → Railway POST /run
      → scraper.py (Apify) → enricher.py (Instaloader + Playwright) → scorer.py
      → HOT leads (score ≥ 90): image_gen.py (GPT image-1 → S3) → ai_reviewer.py (Claude Haiku)
      → pipeline_status = "ready_for_review" → Twilio SMS to owner

Owner visits /review → approves image variant
  → POST /api/leads/approve → Airtable update + Railway POST /email/trigger
      → email_trigger.py (Instantly.ai) — injects {{case_study_blurb}} if one exists

Lead replies to email
  → SendGrid inbound parse → POST /api/webhook/sendgrid
      → marks reply_received in Airtable → Twilio SMS

Monthly crons:
  1st  → /api/cron/snapshots  → Railway /snapshots/update  (IG + GMB data)
  2nd  → /api/cron/case-studies → Railway /case-studies/generate
  25th → /api/cron/content    → Railway /content/generate  (12 captions/month)
  daily → /api/cron/referral  → Railway /referral/trigger  (day 28-35 post-onboard)
```

## Key architectural decisions

**Airtable as the database.** All state lives in Airtable. The Python client (`pipeline/airtable_client.py`) and TypeScript client (`apps/web/lib/airtable.ts`) both wrap the Airtable API directly — there is no intermediate database. The TS client must use lazy initialisation (call `base(table)` inside functions, not at module scope) or `next build` will crash without env vars.

**`pipeline_status` field drives the pipeline.** A lead moves through: `scored → images_generated → ai_reviewed → ready_for_review → approved → email_sent → replied`. The review dashboard filters on `ready_for_review`; the cron skips anything already past that stage.

**Scoring thresholds are in `pipeline/scorer.py`.** Hot ≥ 90, Warm 60–89, Cold < 60. Only Hot leads enter the image generation step. The max score is 100 (inactive IG +40, followers >200 +15, reviews >20 +15, has website +15, rating <4.2 +15).

**Claude Haiku is used for two things:** image QA review (`ai_reviewer.py`, scores 1–10 per image, PASS if avg ≥ 7.0) and caption generation (`content_generator.py`, 12 themed captions/month). Both use `claude-haiku-4-5-20251001`.

**GPT image-1** generates 3 image variants per lead. On AI review failure, it regenerates once with `refined=True` (adds anti-artefact instruction). If still failing, `pipeline_status = "ai_review_failed"` and the lead is skipped.

**Auth pattern:** `/review` uses `REVIEW_PASSWORD` env var + httpOnly cookie (`review_auth=1`, 7-day, path `/review`). `/report/[slug]` uses per-client password stored in Airtable + httpOnly cookie (`report_auth_{slug}`, 30-day). Both gated by server-side cookie check before data fetch.

**Cron security:** All cron endpoints check `Authorization: Bearer {CRON_SECRET}`. All Railway endpoints do the same. `PIPELINE_SERVICE_URL` is server-side only — never in `NEXT_PUBLIC_*`.

## Airtable tables

`Leads` · `ImageVariants` · `Clients` · `MonthlySnapshots` · `ContentPackages` · `CaseStudies`

The `CaseStudies` table also needs a `referral_email_sent` boolean field on the `Clients` table (checked by `referral_email.py`).
