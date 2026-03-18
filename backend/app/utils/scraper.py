"""
Lightweight job fetcher using public ATS (Applicant Tracking System) APIs.

Replaces Playwright — no headless browser, no scraping.
All data comes from official public JSON APIs (no auth required).

Supported ATS platforms:
  - Greenhouse: boards-api.greenhouse.io
  - Lever:      api.lever.co

Add/remove companies in app/utils/company_sources.py.
"""
import re
import logging
import asyncio
from html.parser import HTMLParser

import httpx

from app.utils.company_sources import COMPANIES, JOB_TITLE_KEYWORDS
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Public API base URLs (no auth)
GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
LEVER_URL      = "https://api.lever.co/v0/postings/{slug}?mode=json"

REQUEST_TIMEOUT = 15  # seconds per company


# ── HTML stripper ─────────────────────────────────────────────────────────────

class _HTMLStripper(HTMLParser):
    """Minimal HTML → plain text converter."""
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts).strip()


def _strip_html(html: str) -> str:
    if not html:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(html)
    # Collapse whitespace
    return re.sub(r"\s+", " ", stripper.get_text()).strip()


# ── Title filter ──────────────────────────────────────────────────────────────

def _title_matches_filter(title: str) -> bool:
    """Return True if the job title contains at least one tracked keyword."""
    if not JOB_TITLE_KEYWORDS:
        return True  # No filter set — import everything
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in JOB_TITLE_KEYWORDS)


# ── Experience level inference ────────────────────────────────────────────────

# Each tuple: (level, list_of_regex_patterns)
# Ordered from most-specific to least-specific so the first match wins.
# \b = word boundary — handles keywords at start, end, or middle of title.
_EXPERIENCE_PATTERNS: list[tuple[str, list[str]]] = [
    ("director",  [r"\bdirector\b", r"\bvp\b", r"\bvice president\b", r"\bhead of\b", r"\bprincipal\b"]),
    ("lead",      [r"\blead\b", r"\bstaff\b", r"\barchitect\b", r"\bdistinguished\b"]),
    ("senior",    [r"\bsenior\b", r"\bsr\.\b", r"\bsr\b", r"\bexperienced\b"]),
    ("entry",     [r"\bjunior\b", r"\bjr\.\b", r"\bjr\b", r"\bentry\b", r"\bassociate\b", r"\bgraduate\b", r"\bintern\b", r"\bnew grad\b"]),
    ("mid",       []),   # Default / catch-all — applied if none of the above match
]

# Matches patterns like: "5+ years", "8 years", "3-5 years", "at least 6 years",
# "minimum 4 years", "10+ years of experience", "2–4 years"
_YEARS_RE = re.compile(
    r"(?:at\s+least\s+|minimum\s+|(?:\d+\s*[-–]\s*)?)"  # optional qualifier / range start
    r"(\d+)\s*\+?\s*"                                     # the main number
    r"years?\b",                                           # 'year' or 'years'
    re.IGNORECASE,
)

# Map max years found in description → experience level
_YEARS_TO_LEVEL: list[tuple[int, str]] = [
    (12, "director"),   # 12+ years → director / VP
    (8,  "lead"),       #  8+ years → lead / staff / architect
    (5,  "senior"),     #  5+ years → senior
    (2,  "mid"),        #  2+ years → mid-level
    (0,  "entry"),      #  < 2 years → entry
]


def _infer_level_from_years(text: str) -> str | None:
    """
    Scan free-form text for years-of-experience requirements and return the
    corresponding experience level, or None if no year pattern is found.

    Takes the *maximum* value when multiple patterns appear (e.g. a job listing
    both '1-3 years for one role' context and '5+ years for the core skill').
    """
    if not text:
        return None
    matches = _YEARS_RE.findall(text)
    if not matches:
        return None
    max_years = max(int(y) for y in matches)
    for threshold, level in _YEARS_TO_LEVEL:
        if max_years >= threshold:
            return level
    return "entry"


def _infer_experience_level(title: str, body: str = "") -> str:
    """
    Infer experience level from a job title (primary) with the job
    description / requirements as a fallback signal (secondary).

    Strategy:
      1. Title keywords win unconditionally (director/lead/senior/entry).
      2. If the title gives no signal (would default to 'mid'), scan `body`
         for years-of-experience patterns ("5+ years", "8 years", etc.).
      3. If still no signal, return 'mid' as the safe default.

    Returns one of: 'entry' | 'mid' | 'senior' | 'lead' | 'director'
    """
    title_lower = title.lower()
    for level, patterns in _EXPERIENCE_PATTERNS:
        if any(re.search(pat, title_lower) for pat in patterns):
            return level
    # Title gave no clear signal — try years-of-experience in the body text
    level_from_years = _infer_level_from_years(body)
    return level_from_years if level_from_years is not None else "mid"


# ── Greenhouse fetcher ────────────────────────────────────────────────────────

async def fetch_greenhouse_jobs(
    client: httpx.AsyncClient,
    company_name: str,
    slug: str,
    limit: int = 20,
) -> list[dict]:
    """Fetch jobs from Greenhouse API for a single company."""
    url = GREENHOUSE_URL.format(slug=slug)
    try:
        resp = await client.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning("Greenhouse: company slug '%s' not found (404)", slug)
        else:
            logger.warning("Greenhouse '%s' HTTP %s", slug, e.response.status_code)
        return []
    except Exception as e:
        logger.warning("Greenhouse '%s' error: %s", slug, e)
        return []

    jobs = data.get("jobs", [])
    results = []

    for job in jobs:
        title = job.get("title", "").strip()
        if not title or not _title_matches_filter(title):
            continue

        description = _strip_html(job.get("content", ""))
        location_obj = job.get("location") or {}
        location = (location_obj.get("name") or "Remote").strip()
        posted = (job.get("updated_at") or "")[:10]

        results.append({
            "title": title,
            "company": company_name,
            "location": location,
            "description": description,
            "requirements": "",       # Greenhouse merges req into content
            "url": job.get("absolute_url", ""),
            "source": f"greenhouse:{slug}",
            "job_id_external": f"gh_{job.get('id', '')}",
            "employment_type": "Full-time",
            "posted_date": posted,
            "experience_level": _infer_experience_level(title, description),
            "is_synthetic": False,    # Real job from official API
        })

        if len(results) >= limit:
            break

    logger.info("Greenhouse '%s': fetched %d jobs", slug, len(results))
    return results


# ── Lever fetcher ─────────────────────────────────────────────────────────────

async def fetch_lever_jobs(
    client: httpx.AsyncClient,
    company_name: str,
    slug: str,
    limit: int = 20,
) -> list[dict]:
    """Fetch jobs from Lever API for a single company."""
    url = LEVER_URL.format(slug=slug)
    try:
        resp = await client.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        postings = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning("Lever: company slug '%s' not found (404)", slug)
        else:
            logger.warning("Lever '%s' HTTP %s", slug, e.response.status_code)
        return []
    except Exception as e:
        logger.warning("Lever '%s' error: %s", slug, e)
        return []

    results = []

    for posting in postings:
        title = posting.get("text", "").strip()
        if not title or not _title_matches_filter(title):
            continue

        categories = posting.get("categories") or {}
        location = (categories.get("location") or "Remote").strip()
        description = _strip_html(posting.get("descriptionPlain") or posting.get("description", ""))

        # Lever lists requirements separately
        lists = posting.get("lists") or []
        req_text = ""
        for section in lists:
            label = section.get("text", "").lower()
            if "requirement" in label or "qualif" in label:
                req_text = _strip_html(section.get("content", ""))
                break

        results.append({
            "title": title,
            "company": company_name,
            "location": location,
            "description": description,
            "requirements": req_text,
            "url": posting.get("hostedUrl", ""),
            "source": f"lever:{slug}",
            "job_id_external": f"lv_{posting.get('id', '')}",
            "employment_type": "Full-time",
            "posted_date": "",
            "experience_level": _infer_experience_level(title, description + " " + req_text),
            "is_synthetic": False,    # Real job from official API
        })

        if len(results) >= limit:
            break

    logger.info("Lever '%s': fetched %d jobs", slug, len(results))
    return results


# ── Main entry point ──────────────────────────────────────────────────────────

async def scrape_all_companies(
    limit_per_company: int = 20,
    company_slugs: list[str] | None = None,
) -> list[dict]:
    """
    Fetch jobs from all (or a subset of) companies in company_sources.COMPANIES.

    Args:
        limit_per_company: Max jobs to fetch per company.
        company_slugs: If provided, only scrape companies whose slug is in this list.
                       Pass None (default) to scrape all companies.

    Makes all requests concurrently (one per company) for speed.
    Returns a flat list of job dicts across all companies.
    """
    all_jobs: list[dict] = []

    # Filter the company list if slugs were specified
    target_companies = COMPANIES
    if company_slugs is not None:
        slugs_lower = {s.lower() for s in company_slugs}
        target_companies = [c for c in COMPANIES if c["slug"].lower() in slugs_lower]
        if not target_companies:
            logger.warning("No matching companies found for slugs: %s", company_slugs)
            return []

    async with httpx.AsyncClient(
        headers={"User-Agent": "JobTracker/1.0 (legitimate job aggregator)"},
        follow_redirects=True,
    ) as client:
        tasks = []
        for company in target_companies:
            name = company["name"]
            ats  = company["ats"].lower()
            slug = company["slug"]

            if ats == "greenhouse":
                tasks.append(fetch_greenhouse_jobs(client, name, slug, limit_per_company))
            elif ats == "lever":
                tasks.append(fetch_lever_jobs(client, name, slug, limit_per_company))
            else:
                logger.warning("Unknown ATS type '%s' for company '%s'", ats, name)

        # Fetch all companies concurrently, gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for company, result in zip(target_companies, results):
            if isinstance(result, Exception):
                logger.error("Failed to fetch '%s': %s", company["name"], result)
            elif isinstance(result, list):
                all_jobs.extend(result)

    logger.info(
        "Total jobs fetched: %d from %d companies",
        len(all_jobs),
        len(target_companies),
    )
    return all_jobs


# ── Backwards-compatible alias (used by services/pipeline.py) ─────────────────
async def scrape_amazon_jobs(
    query: str = "",
    limit: int = 20,
    company_slugs: list[str] | None = None,
) -> list[dict]:
    """
    Legacy alias — wraps scrape_all_companies.
    `query` and `limit` are ignored; configure via company_sources.py.
    Pass `company_slugs` to restrict scraping to specific companies.
    """
    return await scrape_all_companies(
        limit_per_company=settings.JOB_FETCH_LIMIT,
        company_slugs=company_slugs,
    )
