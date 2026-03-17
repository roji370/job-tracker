"""
AI-powered job matching using sentence-transformers.
Computes cosine similarity between resume embedding and job description embedding.
"""
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_model():
    """Load sentence-transformer model once and cache it."""
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformer model: all-MiniLM-L6-v2")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Model loaded successfully.")
        return model
    except ImportError:
        logger.error("sentence-transformers is not installed.")
        raise


def compute_similarity(text_a: str, text_b: str) -> float:
    """
    Compute cosine similarity between two texts.
    Returns a score between 0 and 100.
    """
    try:
        from sentence_transformers import util
        import torch

        model = get_model()
        embeddings = model.encode([text_a, text_b], convert_to_tensor=True)
        similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
        # Normalize to 0–100
        score = max(0.0, min(100.0, similarity * 100))
        return round(score, 2)
    except Exception as e:
        logger.error(f"Similarity computation failed: {e}")
        return 0.0


def generate_explanation(resume_text: str, job: dict, score: float) -> str:
    """Generate a human-readable explanation for the match score."""
    title = job.get("title", "this position")
    company = job.get("company", "the company")

    if score >= 85:
        quality = "Excellent"
        detail = "Your background is a strong fit for the required skills and experience."
    elif score >= 70:
        quality = "Good"
        detail = "Your profile aligns well with the key requirements of this role."
    elif score >= 50:
        quality = "Moderate"
        detail = "You meet some requirements, but there may be skill gaps to address."
    else:
        quality = "Low"
        detail = "This role has requirements that differ significantly from your profile."

    return (
        f"{quality} match ({score:.1f}%) for {title} at {company}. "
        f"{detail}"
    )


def match_resume_to_jobs(resume_text: str, jobs: list[dict]) -> list[dict]:
    """
    Match a resume against a list of jobs.

    Args:
        resume_text: Extracted resume content
        jobs: List of job dicts with 'title', 'description', 'requirements', etc.

    Returns:
        List of dicts with job + match_score + explanation, sorted by score desc
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

        score = compute_similarity(resume_text, job_text)
        explanation = generate_explanation(resume_text, job, score)

        results.append({
            **job,
            "match_score": score,
            "explanation": explanation,
        })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results
