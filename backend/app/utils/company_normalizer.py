"""
Company normalizer — Part 1 & 2 of the company-boost feature.

Public API:
    normalize_company(name: str) -> str
        Clean, lowercase-free canonical company name.

    is_top_company(company: str) -> bool
        True if company appears in top_companies.json (static tier-1 list).
"""

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Static dataset path ────────────────────────────────────────────────────────
_DATA_FILE = Path(__file__).parent.parent / "data" / "top_companies.json"


@lru_cache(maxsize=1)
def _load_top_companies() -> set[str]:
    """
    Load the top_companies.json once and cache it for the lifetime of the process.
    Returns a set of LOWERCASE company names for O(1) lookup.
    """
    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        names = {c.lower().strip() for c in data.get("companies", [])}
        logger.info("Loaded %d top companies from static dataset.", len(names))
        return names
    except Exception as exc:
        logger.error("Failed to load top_companies.json: %s", exc)
        return set()


# ── Legal suffix patterns to strip ────────────────────────────────────────────
# Ordered longest-first so greedy stripping works correctly.
_SUFFIX_PATTERN = re.compile(
    r"""
    ,?\s*\b(?:
        pvt\.?\s*ltd\.?
        | private\s+limited
        | p\.?\s*l\.?
        | incorporated
        | inc\.?
        | limited
        | ltd\.?
        | llc\.?
        | llp\.?
        | l\.p\.?
        | l\.l\.c\.?
        | corp\.?
        | corporation
        | co\.?
        | group
        | holdings?
        | technologies?
        | solutions?
        | services?
        | systems?
        | global
        | international
        | enterprises?
    )\b\.?$
    """,
    re.VERBOSE | re.IGNORECASE,
)

# ── Canonical alias map (key = any variant, value = canonical display name) ───
# Keys are LOWERCASE normalized strings without legal suffixes.
_ALIAS_MAP: dict[str, str] = {
    # Google
    "google":                          "Google",
    "google llc":                      "Google",
    "alphabet":                        "Google",
    "google inc":                      "Google",
    "google cloud":                    "Google",
    # Amazon
    "amazon":                          "Amazon",
    "amazon web services":             "Amazon",
    "aws":                             "Amazon",
    "amazon.com":                      "Amazon",
    # Microsoft
    "microsoft":                       "Microsoft",
    "msft":                            "Microsoft",
    "microsoft azure":                 "Microsoft",
    # Meta / Facebook
    "meta":                            "Meta",
    "facebook":                        "Meta",
    "instagram":                       "Meta",
    "whatsapp":                        "Meta",
    # Apple
    "apple":                           "Apple",
    "apple computer":                  "Apple",
    # Netflix
    "netflix":                         "Netflix",
    # OpenAI / Anthropic
    "openai":                          "OpenAI",
    "anthropic":                       "Anthropic",
    # Square / Block
    "square":                          "Block",
    "block":                           "Block",
    # Twitter / X
    "twitter":                         "Twitter",
    "x":                               "Twitter",
    "x.com":                           "Twitter",
    # Salesforce & subs
    "salesforce":                      "Salesforce",
    "slack":                           "Slack",   # was acquired, but brand lives
    "tableau":                         "Salesforce",
    "mulesoft":                        "Salesforce",
    # LinkedIn
    "linkedin":                        "LinkedIn",
    # Other well-known ones
    "uber technologies":               "Uber",
    "uber":                            "Uber",
    "lyft":                            "Lyft",
    "airbnb":                          "Airbnb",
    "stripe":                          "Stripe",
    "shopify":                         "Shopify",
    "coinbase":                        "Coinbase",
    "robinhood":                       "Robinhood",
    "palantir":                        "Palantir",
    "palantir technologies":           "Palantir",
    "twilio":                          "Twilio",
    "datadog":                         "Datadog",
    "snowflake":                       "Snowflake",
    "databricks":                      "Databricks",
    "confluent":                       "Confluent",
    "cloudflare":                      "Cloudflare",
    "figma":                           "Figma",
    "notion":                          "Notion",
    "github":                          "GitHub",
    "gitlab":                          "GitLab",
    "atlassian":                       "Atlassian",
    "discord":                         "Discord",
    "canva":                           "Canva",
    "zoom":                            "Zoom",
    "zoom video communications":       "Zoom",
    "airtable":                        "Airtable",
    "ramp":                            "Ramp",
    "brex":                            "Brex",
    "okta":                            "Okta",
    "crowdstrike":                     "CrowdStrike",
    "palo alto networks":              "Palo Alto Networks",
    "zscaler":                         "Zscaler",
    "servicenow":                      "ServiceNow",
    "workday":                         "Workday",
    "adobe":                           "Adobe",
    "oracle":                          "Oracle",
    "sap":                             "SAP",
    "intel":                           "Intel",
    "nvidia":                          "Nvidia",
    "amd":                             "AMD",
    "qualcomm":                        "Qualcomm",
    "scale ai":                        "Scale AI",
    "hugging face":                    "Hugging Face",
    "deepmind":                        "DeepMind",
    "google deepmind":                 "DeepMind",
    "spotify":                         "Spotify",
    "twitch":                          "Twitch",
    "reddit":                          "Reddit",
    "dropbox":                         "Dropbox",
    "vercel":                          "Vercel",
    "netlify":                         "Netlify",
    "hasura":                          "Hasura",
    "monday":                          "Monday",
    "monday.com":                      "Monday",
    "hubspot":                         "HubSpot",
    "asana":                           "Asana",
    "zendesk":                         "Zendesk",
    "intercom":                        "Intercom",
    "linear":                          "Linear",
    "coda":                            "Coda",
    "splunk":                          "Splunk",
    "hashicorp":                       "HashiCorp",
    "fastly":                          "Fastly",
}


def normalize_company(name: str | None) -> str:
    """
    Normalize a raw company name into a clean canonical form.

    Steps:
      1. Guard against None / empty input.
      2. Lowercase + strip outer whitespace.
      3. Remove legal suffixes (Inc, LLC, Ltd, Corp, Pvt Ltd, ...).
      4. Collapse internal whitespace.
      5. Look up alias map → return canonical display name.
      6. If no alias, title-case the stripped name as best-effort.

    Returns a non-empty string (falls back to the original input on failure).
    """
    if not name:
        return "Unknown"

    raw = name.strip()
    key = raw.lower()

    # Fast-path: exact alias match before suffix stripping
    if key in _ALIAS_MAP:
        return _ALIAS_MAP[key]

    # Strip legal suffixes iteratively (handles stacked suffixes like "Acme Corp Ltd")
    for _ in range(4):
        stripped = _SUFFIX_PATTERN.sub("", key).strip(" ,.")
        if stripped == key:
            break
        key = stripped

    # Collapse internal whitespace
    key = re.sub(r"\s+", " ", key).strip()

    # Look up alias map after stripping
    if key in _ALIAS_MAP:
        return _ALIAS_MAP[key]

    # Best-effort: title-case the cleaned string
    return key.title() if key else raw


def is_top_company(company: str | None) -> bool:
    """
    Return True if the (already normalized) company name is in the
    static top_companies.json dataset.

    Comparison is case-insensitive.
    """
    if not company:
        return False
    top = _load_top_companies()
    return company.lower().strip() in top
