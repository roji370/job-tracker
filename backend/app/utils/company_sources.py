"""
Company career-page registry.

To add a company:
  1. Find their careers page URL
  2. Identify the ATS:
     - Greenhouse URL looks like: boards.greenhouse.io/stripe
     - Lever URL looks like:      jobs.lever.co/netflix
  3. Add an entry to COMPANIES below using their slug.

To filter which job titles get imported, set JOB_TITLE_KEYWORDS.
Any job whose title does NOT contain at least one keyword is skipped.
Leave the list empty [] to import all jobs regardless of title.
"""

# ─── Companies to track ───────────────────────────────────────────────────────
COMPANIES: list[dict] = [
    # ── Greenhouse ATS ──────────────────────────────────────────────────────
    {"name": "Stripe",       "ats": "greenhouse", "slug": "stripe"},
    {"name": "Shopify",      "ats": "greenhouse", "slug": "shopify"},
    {"name": "Notion",       "ats": "greenhouse", "slug": "notion"},
    {"name": "Reddit",       "ats": "greenhouse", "slug": "reddit"},
    {"name": "Ramp",         "ats": "greenhouse", "slug": "ramp"},
    {"name": "Airbnb",       "ats": "greenhouse", "slug": "airbnb"},
    {"name": "Figma",        "ats": "greenhouse", "slug": "figma"},
    {"name": "Airtable",     "ats": "greenhouse", "slug": "airtable"},
    {"name": "Brex",         "ats": "greenhouse", "slug": "brex"},
    {"name": "Discord",      "ats": "greenhouse", "slug": "discord"},
    {"name": "Twilio",       "ats": "greenhouse", "slug": "twilio"},
    {"name": "Datadog",      "ats": "greenhouse", "slug": "datadog"},
    {"name": "Databricks",   "ats": "greenhouse", "slug": "databricks"},
    {"name": "Snowflake",    "ats": "greenhouse", "slug": "snowflake"},
    {"name": "Cloudflare",   "ats": "greenhouse", "slug": "cloudflare"},
    {"name": "Coinbase",     "ats": "greenhouse", "slug": "coinbase"},
    {"name": "Robinhood",    "ats": "greenhouse", "slug": "robinhood"},
    {"name": "Scale AI",     "ats": "greenhouse", "slug": "scaleai"},
    {"name": "Hugging Face", "ats": "greenhouse", "slug": "huggingface"},
    {"name": "Anthropic",    "ats": "greenhouse", "slug": "anthropic"},
    {"name": "OpenAI",       "ats": "greenhouse", "slug": "openai"},
    {"name": "Plaid",        "ats": "greenhouse", "slug": "plaid"},
    {"name": "Asana",        "ats": "greenhouse", "slug": "asana"},
    {"name": "Linear",       "ats": "greenhouse", "slug": "linear"},

    # ── Lever ATS ───────────────────────────────────────────────────────────
    {"name": "Netflix",      "ats": "lever", "slug": "netflix"},
    {"name": "GitHub",       "ats": "lever", "slug": "github"},
    {"name": "Dropbox",      "ats": "lever", "slug": "dropbox"},
    {"name": "Vercel",       "ats": "lever", "slug": "vercel"},
    {"name": "Palantir",     "ats": "lever", "slug": "palantir"},
    {"name": "Canva",        "ats": "lever", "slug": "canva"},
    {"name": "HubSpot",      "ats": "lever", "slug": "hubspot"},
    {"name": "Fastly",       "ats": "lever", "slug": "fastly"},
    {"name": "Retool",       "ats": "lever", "slug": "retool"},
]

# ─── Title keyword filter ─────────────────────────────────────────────────────
# Only jobs whose title contains at least one of these words (case-insensitive)
# will be imported. Remove all entries to import every role (marketing, HR, etc.)
JOB_TITLE_KEYWORDS: list[str] = [
    "engineer",
    "developer",
    "data",
    "scientist",
    "analyst",
    "architect",
    "backend",
    "frontend",
    "fullstack",
    "full-stack",
    "sre",
    "devops",
    "platform",
    "infrastructure",
    "machine learning",
    "ml",
    "ai",
    "software",
]
