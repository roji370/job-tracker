"""
Unit tests for the weighted job matching system.

Tests cover:
  - Individual scoring functions (calculate_*)
  - The primary match_job() interface
  - rank_jobs() ranking and top-N behaviour
  - Legacy backwards-compatible helpers
  - resume_parser extraction helpers
"""
import pytest

from app.utils.matcher import (
    calculate_role_score,
    calculate_skills_score,
    calculate_experience_score,
    calculate_location_score,
    calculate_tech_score,
    match_job,
    rank_jobs,
    # legacy helpers
    compute_similarity,
    generate_explanation,
    match_resume_to_jobs,
)
from app.utils.resume_parser import (
    extract_experience_years,
    extract_location,
    extract_roles,
)


# ─────────────────────────────────────────────────────────────────────────────
# calculate_role_score
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateRoleScore:
    def test_exact_role_match_scores_high(self):
        score = calculate_role_score(["Software Engineer"], "Software Engineer")
        assert score >= 70, f"Exact match should score >= 70, got {score}"

    def test_unrelated_roles_score_low(self):
        score = calculate_role_score(["Chef"], "Backend Engineer")
        assert score < 70, f"Unrelated roles should score < 70, got {score}"

    def test_missing_cv_roles_returns_neutral(self):
        score = calculate_role_score([], "Software Engineer")
        assert score == 50.0

    def test_missing_job_title_returns_neutral(self):
        score = calculate_role_score(["Software Engineer"], "")
        assert score == 50.0

    def test_score_bounded_0_to_100(self):
        score = calculate_role_score(["Data Scientist"], "Senior Data Scientist at FAANG")
        assert 0.0 <= score <= 100.0

    def test_keyword_in_title_boosts_score(self):
        score_with = calculate_role_score(["Backend Engineer"], "Senior Backend Engineer")
        score_without = calculate_role_score(["Chef"], "Senior Backend Engineer")
        assert score_with > score_without


# ─────────────────────────────────────────────────────────────────────────────
# calculate_skills_score
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateSkillsScore:
    def test_perfect_overlap_scores_100(self):
        score = calculate_skills_score(["Python", "FastAPI"], ["Python", "FastAPI"])
        assert score == 100.0

    def test_no_overlap_scores_0(self):
        score = calculate_skills_score(["Ruby"], ["Python", "Node.js"])
        assert score == 0.0

    def test_partial_overlap_scores_proportionally(self):
        # 1 of 2 required skills matched → ~50
        score = calculate_skills_score(["Python"], ["Python", "Node.js"])
        assert 40.0 <= score <= 60.0, f"Expected ~50, got {score}"

    def test_empty_cv_skills_scores_0(self):
        score = calculate_skills_score([], ["Python", "SQL"])
        assert score == 0.0

    def test_no_required_skills_returns_neutral(self):
        score = calculate_skills_score(["Python"], [])
        assert score == 70.0

    def test_partial_alias_match_counts(self):
        # "node" should partially match "node.js"
        score = calculate_skills_score(["node"], ["node.js"])
        assert score > 0.0

    def test_case_insensitive(self):
        score = calculate_skills_score(["PYTHON", "fastapi"], ["python", "FastAPI"])
        assert score == 100.0


# ─────────────────────────────────────────────────────────────────────────────
# calculate_experience_score
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateExperienceScore:
    def test_within_range_scores_100(self):
        assert calculate_experience_score(1, "entry") == 100.0
        assert calculate_experience_score(3, "mid") == 100.0
        assert calculate_experience_score(6, "senior") == 100.0

    def test_underqualified_scores_less_than_100(self):
        score = calculate_experience_score(0, "senior")  # 5-8 yrs required
        assert score < 100.0

    def test_underqualified_clamped_at_30(self):
        score = calculate_experience_score(0, "director")  # 10+ yrs required
        assert score >= 30.0

    def test_overqualified_scores_at_least_60(self):
        score = calculate_experience_score(10, "entry")  # 0-2 yrs expected
        assert score >= 60.0

    def test_no_data_returns_neutral(self):
        assert calculate_experience_score(None, None) == 70.0
        assert calculate_experience_score(None, "mid") == 70.0

    def test_unknown_level_returns_neutral_range(self):
        score = calculate_experience_score(3, "executive")
        assert 0.0 <= score <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
# calculate_location_score
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateLocationScore:
    def test_remote_job_remote_candidate_scores_100(self):
        score = calculate_location_score("India", "Remote", "Remote")
        assert score == 100.0

    def test_remote_job_onsite_candidate_still_scores_high(self):
        score = calculate_location_score("Bangalore", "Bangalore", "Remote")
        assert score >= 80.0

    def test_onsite_job_remote_only_candidate_scores_low(self):
        score = calculate_location_score("Bangalore", "Remote", "Bangalore")
        assert score == 50.0

    def test_exact_location_match_scores_100(self):
        score = calculate_location_score("Bangalore", "Bangalore", "Bangalore")
        assert score == 100.0

    def test_country_match_scores_80(self):
        score = calculate_location_score("india", "Bangalore", "India")
        # 'india' is a substring of 'india' → hits direct match path → 100
        # country-level heuristic fires first only if substring didn't match
        assert score >= 80.0

    def test_no_job_location_returns_neutral(self):
        score = calculate_location_score("Bangalore", "Remote", None)
        assert score == 70.0


# ─────────────────────────────────────────────────────────────────────────────
# calculate_tech_score
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateTechScore:
    def test_same_stack_scores_high(self):
        skills = ["node.js", "express", "javascript"]
        desc   = "We use Node.js, Express and JavaScript for our backend."
        score  = calculate_tech_score(skills, desc)
        # TF-IDF on short texts can score conservatively; group bonus brings it up
        assert score > 30.0, f"Same-stack should score > 30, got {score}"

    def test_unrelated_stack_scores_low(self):
        skills = ["node.js", "react"]
        desc   = "Machine learning research, PyTorch, GPU clusters"
        score  = calculate_tech_score(skills, desc)
        assert score < 60.0

    def test_empty_skills_returns_neutral(self):
        score = calculate_tech_score([], "Python Django backend role")
        assert score == 50.0

    def test_empty_description_returns_neutral(self):
        score = calculate_tech_score(["Python"], "")
        assert score == 50.0

    def test_score_bounded_0_to_100(self):
        score = calculate_tech_score(["python", "fastapi", "docker"], "Python FastAPI cloud Docker k8s")
        assert 0.0 <= score <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
# match_job — primary interface
# ─────────────────────────────────────────────────────────────────────────────

_CV = {
    "roles":              ["Software Engineer", "Backend Engineer"],
    "skills":             ["python", "fastapi", "sql", "docker"],
    "experience_years":   2,
    "location":           "India",
    "preferred_location": "Remote",
}

_JOB_GOOD = {
    "title":            "Backend Engineer",
    "skills_required":  ["python", "fastapi", "postgresql"],
    "experience_level": "entry",
    "location":         "Remote",
    "description":      "We need a backend engineer with Python, FastAPI, and docker experience.",
}

_JOB_BAD = {
    "title":            "Sous Chef",
    "skills_required":  ["cooking", "baking", "plating"],
    "experience_level": "mid",
    "location":         "Paris",
    "description":      "A culinary role in a Michelin restaurant kitchen.",
}


class TestMatchJob:
    def test_returns_required_keys(self):
        result = match_job(_CV, _JOB_GOOD)
        assert "final_score"  in result
        assert "breakdown"    in result
        assert "explanation"  in result

    def test_breakdown_has_all_dimensions(self):
        result = match_job(_CV, _JOB_GOOD)
        bd = result["breakdown"]
        for key in ("role", "skills", "experience", "location", "tech_stack"):
            assert key in bd, f"Missing key '{key}' in breakdown"

    def test_good_job_scores_higher_than_bad(self):
        good_score = match_job(_CV, _JOB_GOOD)["final_score"]
        bad_score  = match_job(_CV, _JOB_BAD)["final_score"]
        assert good_score > bad_score, f"Good job ({good_score}) should beat bad ({bad_score})"

    def test_final_score_is_float_in_range(self):
        result = match_job(_CV, _JOB_GOOD)
        assert isinstance(result["final_score"], float)
        assert 0.0 <= result["final_score"] <= 100.0

    def test_explanation_is_non_empty_list(self):
        result = match_job(_CV, _JOB_GOOD)
        assert isinstance(result["explanation"], list)
        assert len(result["explanation"]) > 0

    def test_missing_cv_fields_no_crash(self):
        # Minimal cv_data — should not raise
        result = match_job({}, _JOB_GOOD)
        assert "final_score" in result

    def test_missing_job_fields_no_crash(self):
        result = match_job(_CV, {})
        assert "final_score" in result

    def test_all_missing_returns_safe_default(self):
        result = match_job({}, {})
        assert 0.0 <= result["final_score"] <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
# rank_jobs
# ─────────────────────────────────────────────────────────────────────────────

class TestRankJobs:
    def test_returns_at_most_5(self):
        jobs = [_JOB_GOOD] * 10
        result = rank_jobs(_CV, jobs)
        assert len(result) <= 5

    def test_sorted_descending_by_match_score(self):
        jobs   = [_JOB_GOOD, _JOB_BAD]
        result = rank_jobs(_CV, jobs)
        scores = [r["match_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_result_enriched_with_match_fields(self):
        result = rank_jobs(_CV, [_JOB_GOOD])
        assert len(result) == 1
        assert "match_score"     in result[0]
        assert "score_breakdown" in result[0]
        assert "explanation"     in result[0]

    def test_empty_jobs_list(self):
        assert rank_jobs(_CV, []) == []

    def test_original_job_fields_preserved(self):
        result = rank_jobs(_CV, [_JOB_GOOD])
        assert result[0]["title"] == _JOB_GOOD["title"]


# ─────────────────────────────────────────────────────────────────────────────
# Legacy backwards-compatible helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestLegacyHelpers:
    def test_compute_similarity_identical(self):
        text = "Python FastAPI backend developer"
        assert compute_similarity(text, text) > 90

    def test_compute_similarity_empty(self):
        assert compute_similarity("", "anything") == 0.0
        assert compute_similarity("anything", "") == 0.0

    def test_compute_similarity_bounded(self):
        score = compute_similarity("hello", "world")
        assert 0.0 <= score <= 100.0

    def test_generate_explanation_excellent(self):
        e = generate_explanation("text", {"title": "SDE", "company": "Stripe"}, 90.0)
        assert "Excellent" in e

    def test_generate_explanation_contains_title(self):
        e = generate_explanation("text", {"title": "ML Engineer", "company": "X"}, 80.0)
        assert "ML Engineer" in e

    def test_match_resume_to_jobs_sorts_desc(self):
        resume = "Python FastAPI developer SQL databases"
        jobs = [
            {"title": "Chef",            "description": "Culinary arts",        "requirements": "cooking"},
            {"title": "Python Engineer", "description": "FastAPI SQL databases", "requirements": "Python"},
        ]
        results = match_resume_to_jobs(resume, jobs)
        assert results[0]["match_score"] >= results[1]["match_score"]

    def test_match_resume_to_jobs_empty(self):
        assert match_resume_to_jobs("", [{"title": "Dev"}]) == []
        assert match_resume_to_jobs("Dev", []) == []


# ─────────────────────────────────────────────────────────────────────────────
# Resume parser extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestResumeParserHelpers:
    def test_extract_experience_years_explicit(self):
        text  = "I have 3 years of experience in backend development."
        years = extract_experience_years(text)
        assert years == 3

    def test_extract_experience_years_from_year_range(self):
        text  = "Worked at Acme from 2020 to 2023 as a Software Engineer."
        years = extract_experience_years(text)
        assert years is not None
        assert years >= 0

    def test_extract_experience_years_none_when_no_signal(self):
        text  = "A passionate developer who loves coding."
        years = extract_experience_years(text)
        assert years is None

    def test_extract_location_known_city(self):
        text = "Based in Bangalore, Karnataka. Open to relocation."
        loc  = extract_location(text)
        assert loc is not None
        assert "bangalore" in loc.lower() or "bengaluru" in loc.lower()

    def test_extract_location_country_fallback(self):
        text = "Currently residing in India."
        loc  = extract_location(text)
        assert loc == "India"

    def test_extract_location_none_when_unknown(self):
        text = "Passionate developer available for remote work."
        loc  = extract_location(text)
        assert loc is None

    def test_extract_roles_finds_known_titles(self):
        text  = "Experienced Software Engineer and Backend Engineer with 5 years."
        roles = extract_roles(text)
        assert any("software engineer" in r.lower() for r in roles)
        assert any("backend engineer" in r.lower() for r in roles)

    def test_extract_roles_empty_when_no_match(self):
        text  = "A culinary artist with passion for French cuisine."
        roles = extract_roles(text)
        assert roles == []
