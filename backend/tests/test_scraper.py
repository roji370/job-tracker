"""
Integration tests for the job scraper fetchers.
Calls the live Greenhouse and Lever public APIs.

These tests require internet access and may be slow (~5-15s).
Run with: pytest tests/test_scraper.py -v -s
"""
import pytest
import httpx

from app.utils.scraper import (
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    scrape_all_companies,
    _strip_html,
    _title_matches_filter,
    _infer_level_from_years,
    _infer_experience_level,
)

REQUIRED_JOB_KEYS = {"title", "company", "location", "description", "url", "source", "job_id_external", "is_synthetic"}


# ── HTML stripping ─────────────────────────────────────────────────────────────

class TestStripHtml:
    def test_strips_basic_tags(self):
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_empty_string(self):
        assert _strip_html("") == ""

    def test_none_like_empty(self):
        assert _strip_html(None) == ""

    def test_plain_text_unchanged(self):
        result = _strip_html("No HTML here")
        assert "No HTML here" in result


# ── Title filter ───────────────────────────────────────────────────────────────

class TestTitleFilter:
    def test_engineer_passes(self):
        assert _title_matches_filter("Senior Software Engineer")

    def test_chef_filtered_out(self):
        assert not _title_matches_filter("Head Chef")

    def test_data_scientist_passes(self):
        assert _title_matches_filter("Data Scientist II")

    def test_marketing_filtered_out(self):
        assert not _title_matches_filter("Marketing Manager")

    def test_case_insensitive(self):
        assert _title_matches_filter("BACKEND ENGINEER")


# ── Experience-level inference: years-from-description ─────────────────────────

class TestInferLevelFromYears:
    """Tests for _infer_level_from_years() — parses year counts from free text."""

    # ── Basic number patterns ──
    def test_5_plus_years_is_senior(self):
        assert _infer_level_from_years("Requires 5+ years of experience.") == "senior"

    def test_8_years_is_lead(self):
        assert _infer_level_from_years("8 years of relevant experience required.") == "lead"

    def test_12_plus_years_is_director(self):
        assert _infer_level_from_years("12+ years leading engineering teams.") == "director"

    def test_2_years_is_mid(self):
        assert _infer_level_from_years("2 years experience preferred.") == "mid"

    def test_1_year_is_entry(self):
        assert _infer_level_from_years("1 year of Java experience required.") == "entry"

    # ── Range patterns ──
    def test_range_3_5_years_takes_max(self):
        # "3-5 years" → max is 5 → senior
        assert _infer_level_from_years("3-5 years of software development experience.") == "senior"

    def test_range_1_3_years_takes_max(self):
        # "1-3 years" → max is 3 → mid
        assert _infer_level_from_years("Looking for someone with 1-3 years experience.") == "mid"

    def test_range_with_en_dash(self):
        # "2–4 years" (en-dash)
        assert _infer_level_from_years("2\u20134 years of Python experience.") == "mid"

    # ── Qualifiers ──
    def test_at_least_6_years(self):
        assert _infer_level_from_years("At least 6 years of engineering experience.") == "senior"

    def test_minimum_10_years(self):
        assert _infer_level_from_years("Minimum 10 years in a leadership role.") == "lead"

    # ── Multiple mentions — takes max ──
    def test_multiple_mentions_takes_max(self):
        # "1+ years Python, 7+ years overall" → max=7 → lead
        text = "1+ years of Python experience. 7+ years of overall software experience."
        assert _infer_level_from_years(text) == "lead"

    # ── Spelling variants ──
    def test_singular_year(self):
        assert _infer_level_from_years("Requires 1 year of experience.") == "entry"

    def test_case_insensitive(self):
        assert _infer_level_from_years("REQUIRES 5 YEARS OF EXPERIENCE.") == "senior"

    # ── No match ──
    def test_no_years_returns_none(self):
        assert _infer_level_from_years("Bachelor's degree in Computer Science preferred.") is None

    def test_empty_string_returns_none(self):
        assert _infer_level_from_years("") is None

    def test_none_like_empty(self):
        assert _infer_level_from_years(None) is None


# ── Experience-level inference: title + description combined ───────────────────

class TestInferExperienceLevel:
    """Tests for _infer_experience_level(title, body) — combined two-tier logic."""

    # ── Title keyword: director tier ──
    def test_director_in_title(self):
        assert _infer_experience_level("Director of Engineering") == "director"

    def test_vp_in_title(self):
        assert _infer_experience_level("VP of Product") == "director"

    def test_principal_in_title(self):
        assert _infer_experience_level("Principal Engineer") == "director"

    def test_head_of_in_title(self):
        assert _infer_experience_level("Head of Platform Engineering") == "director"

    # ── Title keyword: lead tier ──
    def test_lead_at_end_of_title(self):
        # Previously broken with trailing-space pattern
        assert _infer_experience_level("Tech Lead") == "lead"

    def test_lead_at_start_of_title(self):
        assert _infer_experience_level("Lead Software Engineer") == "lead"

    def test_staff_engineer(self):
        assert _infer_experience_level("Staff Engineer") == "lead"

    def test_architect_in_title(self):
        assert _infer_experience_level("Solutions Architect") == "lead"

    # ── Title keyword: senior tier ──
    def test_senior_in_title(self):
        assert _infer_experience_level("Senior Backend Engineer") == "senior"

    def test_sr_abbreviation(self):
        assert _infer_experience_level("Sr. Software Engineer") == "senior"

    # ── Title keyword: entry tier ──
    def test_junior_in_title(self):
        assert _infer_experience_level("Junior Developer") == "entry"

    def test_intern_in_title(self):
        assert _infer_experience_level("Software Engineering Intern") == "entry"

    def test_new_grad_in_title(self):
        assert _infer_experience_level("New Grad Software Engineer") == "entry"

    # ── Fallback: years from description when title is ambiguous ──
    def test_ambiguous_title_uses_description_years(self):
        # "Software Engineer" has no level keyword → fall back to "7+ years" in desc
        result = _infer_experience_level(
            "Software Engineer",
            "We require 7+ years of backend development experience."
        )
        assert result == "lead"

    def test_ambiguous_title_senior_from_description(self):
        result = _infer_experience_level(
            "Backend Developer",
            "Minimum 5 years of Python experience required."
        )
        assert result == "senior"

    def test_ambiguous_title_entry_from_description(self):
        result = _infer_experience_level(
            "Software Engineer",
            "Looking for candidates with 0-1 years of experience."
        )
        assert result == "entry"

    # ── Title always wins over description ──
    def test_title_beats_description(self):
        # Title says "Senior" but description says "12+ years" (would be director)
        result = _infer_experience_level(
            "Senior Software Engineer",
            "12+ years of experience preferred."
        )
        assert result == "senior"   # title wins

    # ── Total no signal → mid ──
    def test_no_signal_defaults_to_mid(self):
        assert _infer_experience_level("Software Engineer") == "mid"

    def test_empty_title_and_body(self):
        assert _infer_experience_level("") == "mid"


# ── Live API tests ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_greenhouse_stripe_returns_jobs():
    """Stripe uses Greenhouse — should return real job listings."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        jobs = await fetch_greenhouse_jobs(client, "Stripe", "stripe", limit=5)
    assert isinstance(jobs, list)
    # Stripe almost always has engineering jobs
    if len(jobs) > 0:
        job = jobs[0]
        assert "title" in job
        assert "url" in job
        assert job["company"] == "Stripe"
        assert job["is_synthetic"] is False
        assert REQUIRED_JOB_KEYS.issubset(job.keys())


@pytest.mark.anyio
async def test_greenhouse_invalid_slug_returns_empty():
    """A non-existent slug should return [] without crashing."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        jobs = await fetch_greenhouse_jobs(client, "FakeCompany", "xxxxnotacompanyxxxx", limit=5)
    assert jobs == []


@pytest.mark.anyio
async def test_lever_lever_returns_jobs():
    """Netflix uses Lever ATS."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        jobs = await fetch_lever_jobs(client, "Netflix", "netflix", limit=5)
    assert isinstance(jobs, list)
    if len(jobs) > 0:
        job = jobs[0]
        assert job["company"] == "Netflix"
        assert job["is_synthetic"] is False
        assert REQUIRED_JOB_KEYS.issubset(job.keys())


@pytest.mark.anyio
async def test_lever_invalid_slug_returns_empty():
    async with httpx.AsyncClient(follow_redirects=True) as client:
        jobs = await fetch_lever_jobs(client, "FakeCompany", "xxxxnotacompanyxxxx", limit=5)
    assert jobs == []


@pytest.mark.anyio
async def test_scrape_all_companies_returns_list():
    """Full scrape should return a list (may be empty if all APIs are down)."""
    jobs = await scrape_all_companies(limit_per_company=3)
    assert isinstance(jobs, list)
    # Sanity-check shape of any returned jobs
    for job in jobs:
        assert "title" in job
        assert "company" in job
        assert "is_synthetic" in job
        assert job["is_synthetic"] is False
