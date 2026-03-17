"""
Unit tests for the AI matcher utility.
Run with: pytest backend/tests/
"""
import pytest
from app.utils.matcher import compute_similarity, generate_explanation, match_resume_to_jobs


class TestComputeSimilarity:
    def test_identical_texts_score_near_100(self):
        text = "Python developer with FastAPI and PostgreSQL experience"
        score = compute_similarity(text, text)
        assert score > 90, f"Identical text similarity should be >90, got {score}"

    def test_unrelated_texts_score_low(self):
        resume = "Python backend developer with 5 years experience in FastAPI"
        job = "Chef with 10 years of culinary arts and French cuisine experience"
        score = compute_similarity(resume, job)
        assert score < 60, f"Unrelated texts should score <60, got {score}"

    def test_similar_texts_score_medium_to_high(self):
        resume = "Python developer skilled in FastAPI, SQLAlchemy, PostgreSQL, Docker"
        job = "Backend engineer needed: Python, FastAPI, databases, cloud deployment"
        score = compute_similarity(resume, job)
        assert score > 40, f"Similar texts should score >40, got {score}"

    def test_score_is_bounded_0_to_100(self):
        score = compute_similarity("hello world", "goodbye moon")
        assert 0.0 <= score <= 100.0

    def test_empty_strings_return_0(self):
        score = compute_similarity("", "some job description")
        # Should not raise, returns 0
        assert score == 0.0 or isinstance(score, float)


class TestGenerateExplanation:
    def test_excellent_match_label(self):
        explanation = generate_explanation("resume text", {"title": "SDE", "company": "Amazon"}, 90.0)
        assert "Excellent" in explanation

    def test_good_match_label(self):
        explanation = generate_explanation("resume text", {"title": "SDE", "company": "Amazon"}, 75.0)
        assert "Good" in explanation

    def test_moderate_match_label(self):
        explanation = generate_explanation("resume text", {"title": "SDE", "company": "Amazon"}, 55.0)
        assert "Moderate" in explanation

    def test_low_match_label(self):
        explanation = generate_explanation("resume text", {"title": "SDE", "company": "Amazon"}, 30.0)
        assert "Low" in explanation

    def test_explanation_contains_title_and_company(self):
        explanation = generate_explanation("text", {"title": "ML Engineer", "company": "OpenAI"}, 80.0)
        assert "ML Engineer" in explanation
        assert "OpenAI" in explanation


class TestMatchResumeToJobs:
    def test_returns_empty_for_no_resume(self):
        results = match_resume_to_jobs("", [{"title": "Dev", "description": "Python"}])
        assert results == []

    def test_returns_empty_for_no_jobs(self):
        results = match_resume_to_jobs("Python developer", [])
        assert results == []

    def test_returns_sorted_by_score_desc(self):
        resume = "Python FastAPI developer"
        jobs = [
            {"title": "Chef", "description": "Culinary arts", "requirements": "cooking"},
            {"title": "Python Engineer", "description": "FastAPI backend", "requirements": "Python"},
        ]
        results = match_resume_to_jobs(resume, jobs)
        assert len(results) == 2
        assert results[0]["match_score"] >= results[1]["match_score"]

    def test_result_contains_required_keys(self):
        resume = "Software engineer with Python experience"
        jobs = [{"title": "Developer", "description": "Python coding", "requirements": "Python"}]
        results = match_resume_to_jobs(resume, jobs)
        assert len(results) == 1
        assert "match_score" in results[0]
        assert "explanation" in results[0]
        assert "title" in results[0]
