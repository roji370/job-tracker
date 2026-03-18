"""
Lightweight job matching using TF-IDF cosine similarity (scikit-learn).

Replaces sentence-transformers + PyTorch.
  Before: ~500 MB RAM, 30s cold start, requires GPU-class hardware
  After:  ~15 MB RAM, <100ms, runs on any free-tier server

Public interface is identical — no other file needs changes.
"""
import logging
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


# ── Text normalisation ────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── Core similarity ───────────────────────────────────────────────────────────

def compute_similarity(text_a: str, text_b: str) -> float:
    """
    Compute TF-IDF cosine similarity between two texts.
    Returns a score between 0.0 and 100.0.
    """
    if not text_a or not text_b:
        return 0.0

    try:
        a = _normalize(text_a)
        b = _normalize(text_b)

        if not a or not b:
            return 0.0

        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),   # unigrams + bigrams for better context matching
            max_features=10_000,
            sublinear_tf=True,    # TF smoothing
        )
        tfidf = vectorizer.fit_transform([a, b])
        score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(float(max(0.0, min(1.0, score))) * 100, 2)

    except Exception as e:
        logger.error("Similarity computation failed: %s", e)
        return 0.0


# ── Explanation ───────────────────────────────────────────────────────────────

def generate_explanation(resume_text: str, job: dict, score: float) -> str:
    """Generate a human-readable explanation for the match score."""
    title   = job.get("title", "this position")
    company = job.get("company", "the company")

    if score >= 85:
        quality = "Excellent"
        detail  = "Your background is a strong fit for the required skills and experience."
    elif score >= 70:
        quality = "Good"
        detail  = "Your profile aligns well with the key requirements of this role."
    elif score >= 50:
        quality = "Moderate"
        detail  = "You meet some requirements, but there may be skill gaps to address."
    else:
        quality = "Low"
        detail  = "This role has requirements that differ significantly from your profile."

    return f"{quality} match ({score:.1f}%) for {title} at {company}. {detail}"


# ── Batch matching ────────────────────────────────────────────────────────────

def match_resume_to_jobs(resume_text: str, jobs: list[dict]) -> list[dict]:
    """
    Match a resume against a list of jobs.

    Args:
        resume_text: Extracted resume content
        jobs: List of job dicts with 'title', 'description', 'requirements'

    Returns:
        Jobs + match_score + explanation, sorted by score descending.
    """
    if not resume_text or not jobs:
        return []

    results = []
    for job in jobs:
        job_text = " ".join(filter(None, [
            job.get("title", ""),
            job.get("description", ""),
            job.get("requirements", ""),
        ]))

        score       = compute_similarity(resume_text, job_text)
        explanation = generate_explanation(resume_text, job, score)

        results.append({**job, "match_score": score, "explanation": explanation})

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results
