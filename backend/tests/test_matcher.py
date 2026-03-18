"""
Unit tests for the AI matcher utility (TF-IDF version).
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

    def test_similar_texts_score_positive(self):
        resume = "Python developer skilled in FastAPI, SQLAlchemy, PostgreSQL, Docker"
        job = "Backend engineer needed: Python, FastAPI, databases, cloud deployment"
        score = compute_similarity(resume, job)
        assert score > 10, f"Similar texts should have some overlap, got {score}"

    def test_score_is_bounded_0_to_100(self):
        score = compute_similarity("hello world", "goodbye moon")
        assert 0.0 <= score <= 100.0

    def test_empty_string_a_returns_0(self):
        score = compute_similarity("", "some job description")
        assert score == 0.0

    def test_empty_string_b_returns_0(self):
        score = compute_similarity("Python developer", "")
        assert score == 0.0

    def test_both_empty_returns_0(self):
        score = compute_similarity("", "")
        assert score == 0.0

    def test_returns_float(self):
        score = compute_similarity("hello", "world")
        assert isinstance(score, float)

    def test_bigram_boost_for_technical_terms(self):
        """TF-IDF with bigrams should score 'machine learning' higher for ML jobs."""
        resume = "machine learning engineer with PyTorch and TensorFlow experience"
        ml_job = "machine learning researcher deep learning NLP computer vision"
        chef_job = "chef restaurant kitchen cooking culinary arts food prep"
        ml_score   = compute_similarity(resume, ml_job)
        chef_score = compute_similarity(resume, chef_job)
        assert ml_score > chef_score


class TestGenerateExplanation:
    def test_excellent_match_label(self):
        e = generate_explanation("resume text", {"title": "SDE", "company": "Stripe"}, 90.0)
        assert "Excellent" in e

    def test_good_match_label(self):
        e = generate_explanation("resume text", {"title": "SDE", "company": "Stripe"}, 75.0)
        assert "Good" in e

    def test_moderate_match_label(self):
        e = generate_explanation("resume text", {"title": "SDE", "company": "Stripe"}, 55.0)
        assert "Moderate" in e

    def test_low_match_label(self):
        e = generate_explanation("resume text", {"title": "SDE", "company": "Stripe"}, 30.0)
        assert "Low" in e

    def test_explanation_contains_title_and_company(self):
        e = generate_explanation("text", {"title": "ML Engineer", "company": "Netflix"}, 80.0)
        assert "ML Engineer" in e
        assert "Netflix" in e

    def test_explanation_contains_score(self):
        e = generate_explanation("text", {"title": "Dev", "company": "Acme"}, 77.5)
        assert "77.5" in e


class TestMatchResumeToJobs:
    def test_returns_empty_for_no_resume(self):
        assert match_resume_to_jobs("", [{"title": "Dev", "description": "Python"}]) == []

    def test_returns_empty_for_no_jobs(self):
        assert match_resume_to_jobs("Python developer", []) == []

    def test_returns_sorted_by_score_desc(self):
        resume = "Python FastAPI developer SQL databases"
        jobs = [
            {"title": "Chef",            "description": "Culinary arts",         "requirements": "cooking"},
            {"title": "Python Engineer", "description": "FastAPI SQL databases",  "requirements": "Python"},
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

    def test_extra_job_fields_preserved(self):
        """Extra fields (like url, company) should pass through unchanged."""
        resume = "Python engineer"
        jobs = [{
            "title": "Backend Dev",
            "description": "Python Django",
            "requirements": "Python",
            "url": "https://example.com/job/1",
            "company": "ACME",
        }]
        results = match_resume_to_jobs(resume, jobs)
        assert results[0]["url"] == "https://example.com/job/1"
        assert results[0]["company"] == "ACME"
