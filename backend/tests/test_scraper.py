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
