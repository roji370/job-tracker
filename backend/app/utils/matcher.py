"""
Weighted job matching system.

Replaces the single TF-IDF cosine similarity with a structured, weighted
scoring model that is transparent and easily extensible.

Memory footprint: ~20-30 MB (scikit-learn only, no ML frameworks).

Weights used in match_job():
    Role Match       35%
    Skills Match     30%
    Experience Match 15%
    Location Match   10%
    Tech Stack Match 10%
"""
import logging
import re
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────────────

# Maps job experience_level strings → (min_years, max_years)
_EXP_LEVEL_RANGES: dict[str, tuple[int, int]] = {
    "entry":    (0, 2),
    "mid":      (2, 5),
    "senior":   (5, 8),
    "lead":     (7, 12),
    "director": (10, 99),
}

# Broad tech-stack groupings used for tech-stack group bonus
_TECH_GROUPS: list[set[str]] = [
    {"node.js", "express", "javascript", "typescript"},
    {"python", "fastapi", "django", "flask"},
    {"react", "vue", "angular", "next.js", "svelte"},
    {"postgresql", "mysql", "sqlite", "sql"},
    {"mongodb", "firestore", "dynamodb", "cassandra"},
    {"aws", "gcp", "azure", "cloud"},
    {"docker", "kubernetes", "terraform"},
    {"machine learning", "pytorch", "tensorflow", "keras", "scikit-learn"},
]


# ── Private helpers ───────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase, remove punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tfidf_similarity(text_a: str, text_b: str) -> float:
    """
    TF-IDF cosine similarity between two texts.
    Returns a score in [0, 100].
    """
    if not text_a or not text_b:
        return 0.0
    try:
        a, b = _normalize(text_a), _normalize(text_b)
        if not a or not b:
            return 0.0
        vec = TfidfVectorizer(ngram_range=(1, 2), max_features=10_000, sublinear_tf=True)
        tfidf = vec.fit_transform([a, b])
        score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(float(max(0.0, min(1.0, score))) * 100, 2)
    except Exception as e:
        logger.error("TF-IDF similarity failed: %s", e)
        return 0.0


def _safe_lower_set(items: list) -> set[str]:
    """Return a lower-cased set from a list, ignoring falsy values."""
    return {str(i).lower().strip() for i in (items or []) if i}


# ── Individual scoring functions ──────────────────────────────────────────────

def calculate_role_score(cv_roles: list[str], job_title: str) -> float:
    """
    Compare candidate's role titles against the job title.

    Strategy:
    - TF-IDF cosine similarity between the joined roles string and the job title.
    - +15 bonus if any individual role word appears in the title (capped at 100).

    Returns 0–100.
    """
    if not cv_roles or not job_title:
        return 50.0  # Neutral — no data to compare

    roles_text  = " ".join(cv_roles)
    score       = _tfidf_similarity(roles_text, job_title)
    title_lower = job_title.lower()

    # Word-level keyword boost
    for role in cv_roles:
        for word in role.lower().split():
            if len(word) > 3 and word in title_lower:
                score = min(100.0, score + 15)
                break

    return round(min(100.0, score), 2)


def calculate_skills_score(
    cv_skills: list[str],
    job_skills_required: list[str],
) -> float:
    """
    Overlap of candidate skills vs explicitly required job skills.

    Direct match counts 1.0, partial/alias match counts 0.7
    (e.g. "node" matches "node.js").
    Score = matched_weight / len(required_skills) * 100.

    Returns 0–100.
    """
    if not job_skills_required:
        return 70.0  # No requirements listed → assume reasonable fit

    if not cv_skills:
        return 0.0

    cv_set  = _safe_lower_set(cv_skills)
    job_set = _safe_lower_set(job_skills_required)

    direct  = cv_set & job_set

    # Partial / alias match for skills not already directly matched
    partial: set[str] = set()
    for jskill in job_set - direct:
        for cskill in cv_set:
            if jskill in cskill or cskill in jskill:
                partial.add(jskill)
                break

    matched_weight = len(direct) + len(partial) * 0.7
    return round(min(100.0, matched_weight / len(job_set) * 100), 2)


def calculate_experience_score(
    cv_years: Optional[int],
    job_exp_level: Optional[str],
) -> float:
    """
    Match candidate years of experience against the job's experience level bucket.

    Scoring:
    - Within the level range         → 100
    - Slightly underqualified        → 60–80 (deduct 20 per missing year)
    - Overqualified                  → 60–90 (deduct 10 per excess year)
    - Missing data on either side    → 70 (neutral)

    Returns 0–100.
    """
    if cv_years is None and not job_exp_level:
        return 70.0

    level      = (job_exp_level or "").strip().lower()
    lo, hi     = _EXP_LEVEL_RANGES.get(level, (0, 99))

    if cv_years is None:
        return 70.0  # Level known but candidate years not parsed

    if lo <= cv_years <= hi:
        return 100.0

    if cv_years < lo:
        gap = lo - cv_years
        return round(max(30.0, 100.0 - gap * 20), 2)

    # Overqualified
    gap = cv_years - hi
    return round(max(60.0, 100.0 - gap * 10), 2)


def calculate_location_score(
    cv_location: Optional[str],
    cv_preferred_location: Optional[str],
    job_location: Optional[str],
) -> float:
    """
    Match candidate location preference against job location.

    Scoring:
    - Remote job + candidate open to remote         → 100
    - Remote job, candidate location not specified  → 85
    - Candidate prefers remote, job is on-site      → 50
    - City/country exact or substring match         → 100 / 80
    - No match                                      → 50

    Returns 0–100.
    """
    if not job_location:
        return 70.0  # Unknown job location → neutral

    job_loc = job_location.lower().strip()
    cv_loc  = (cv_location or "").lower().strip()
    cv_pref = (cv_preferred_location or "").lower().strip()

    # Remote job
    if "remote" in job_loc:
        if "remote" in cv_pref or "remote" in cv_loc:
            return 100.0
        return 85.0  # Remote role is broadly accessible

    # Candidate exclusively prefers remote, but job is on-site
    if cv_pref == "remote":
        return 50.0

    # Direct substring match (city/country)
    if cv_loc and (cv_loc in job_loc or job_loc in cv_loc):
        return 100.0

    # Country-level match heuristic
    _countries = ["india", "us", "uk", "canada", "germany", "australia", "singapore"]
    for kw in _countries:
        if kw in cv_loc and kw in job_loc:
            return 80.0

    return 50.0


def calculate_tech_score(
    cv_skills: list[str],
    job_description: str,
) -> float:
    """
    Broader tech-stack alignment between candidate skills and the job description.

    Uses TF-IDF similarity as a base, then adds a +5 group bonus for each
    technology grouping where both the candidate and the job share at least
    one skill (e.g. MERN stack affinity).

    Returns 0–100.
    """
    if not cv_skills or not job_description:
        return 50.0

    skills_text    = " ".join(cv_skills)
    base           = _tfidf_similarity(skills_text, job_description)

    cv_set         = _safe_lower_set(cv_skills)
    job_desc_lower = job_description.lower()

    bonus = 0.0
    for group in _TECH_GROUPS:
        cv_in_group  = group & cv_set
        job_in_group = {s for s in group if s in job_desc_lower}
        if cv_in_group and job_in_group:
            bonus += 5.0

    return round(min(100.0, base + bonus), 2)


# ── Primary public interface ───────────────────────────────────────────────────

def match_job(cv_data: dict, job_data: dict) -> dict:
    """
    Compute a weighted match score between a parsed CV and a job.

    cv_data expected keys:
        roles               list[str]   — e.g. ["Software Engineer", "Backend Dev"]
        skills              list[str]   — e.g. ["Python", "Node.js", "SQL"]
        experience_years    int | None  — e.g. 3
        location            str | None  — e.g. "Bangalore"
        preferred_location  str | None  — e.g. "Remote"

    job_data expected keys:
        title               str
        skills_required     list[str]   — explicit skill list (may be empty)
        experience_level    str | None  — "entry|mid|senior|lead|director"
        location            str | None
        description         str | None  — full job description text

    Returns:
        {
            "final_score": float,                 # 0–100 weighted total
            "breakdown":   {                      # per-dimension scores
                "role":       float,
                "skills":     float,
                "experience": float,
                "location":   float,
                "tech_stack": float,
            },
            "explanation": list[str],             # human-readable bullets
        }
    """
    try:
        role_score = calculate_role_score(
            cv_data.get("roles") or [],
            job_data.get("title") or "",
        )
        skills_score = calculate_skills_score(
            cv_data.get("skills") or [],
            job_data.get("skills_required") or [],
        )
        experience_score = calculate_experience_score(
            cv_data.get("experience_years"),
            job_data.get("experience_level"),
        )
        location_score = calculate_location_score(
            cv_data.get("location"),
            cv_data.get("preferred_location"),
            job_data.get("location"),
        )
        tech_score = calculate_tech_score(
            cv_data.get("skills") or [],
            job_data.get("description") or "",
        )

        final_score = round(
            0.35 * role_score
            + 0.30 * skills_score
            + 0.15 * experience_score
            + 0.10 * location_score
            + 0.10 * tech_score,
            2,
        )

        breakdown = {
            "role":       role_score,
            "skills":     skills_score,
            "experience": experience_score,
            "location":   location_score,
            "tech_stack": tech_score,
        }

        return {
            "final_score": final_score,
            "breakdown":   breakdown,
            "explanation": _build_explanation(cv_data, job_data, breakdown),
        }

    except Exception as e:
        logger.error("match_job error: %s", e)
        return {
            "final_score": 0.0,
            "breakdown":   {k: 0.0 for k in ("role", "skills", "experience", "location", "tech_stack")},
            "explanation": ["Error computing match score."],
        }


def rank_jobs(cv_data: dict, jobs: list[dict]) -> list[dict]:
    """
    Rank a list of jobs against a CV and return the top 5 by match score.

    Each returned dict is the original job dict enriched with:
        match_score     (float)
        score_breakdown (dict)
        explanation     (list[str])
    """
    results = []
    for job in jobs:
        result = match_job(cv_data, job)
        results.append({
            **job,
            "match_score":     result["final_score"],
            "score_breakdown": result["breakdown"],
            "explanation":     result["explanation"],
        })
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:5]


# ── Explanation builder ───────────────────────────────────────────────────────

def _build_explanation(
    cv_data: dict,
    job_data: dict,
    breakdown: dict,
) -> list[str]:
    """Build a list of human-readable match quality bullets."""
    lines: list[str] = []

    cv_skills  = _safe_lower_set(cv_data.get("skills") or [])
    job_skills = _safe_lower_set(job_data.get("skills_required") or [])
    matched    = cv_skills & job_skills
    missing    = job_skills - cv_skills

    # Role bullet
    r = breakdown["role"]
    title = job_data.get("title") or "this position"
    if r >= 80:
        lines.append(f"Strong role alignment with '{title}'.")
    elif r >= 50:
        lines.append(f"Partial role match — some relevance to '{title}'.")
    else:
        lines.append(f"Role may not closely align with '{title}'.")

    # Skills bullets
    if matched:
        lines.append(f"Matched skills: {', '.join(sorted(matched))}.")
    if missing:
        lines.append(f"Missing skills: {', '.join(sorted(missing))}.")
    if not job_skills:
        lines.append("No explicit skill requirements listed by the employer.")

    # Experience bullet
    e          = breakdown["experience"]
    exp_years  = cv_data.get("experience_years")
    exp_level  = job_data.get("experience_level")
    if e == 100.0:
        lines.append("Experience level aligns with the job requirements.")
    elif exp_years is not None and exp_level:
        gap_label = "slight gap" if e >= 60 else "notable gap"
        lines.append(
            f"Experience ({exp_years} yr) vs required level '{exp_level}' — {gap_label}."
        )

    # Location bullet
    loc = breakdown["location"]
    if loc >= 90:
        lines.append("Location or remote preference is a strong match.")
    elif loc < 60:
        lines.append("Location may be a concern — check if remote options are available.")

    return lines or ["No specific match points identified."]


# ── Backwards-compatible helpers (kept so pipeline.py doesn't break) ──────────

def compute_similarity(text_a: str, text_b: str) -> float:
    """Legacy TF-IDF similarity interface — still used by existing pipeline."""
    return _tfidf_similarity(text_a, text_b)


def generate_explanation(resume_text: str, job: dict, score: float) -> str:
    """Legacy single-string explanation builder — kept for pipeline compatibility."""
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


def match_resume_to_jobs(resume_text: str, jobs: list[dict]) -> list[dict]:
    """Legacy batch interface — kept for backwards compatibility with existing tests."""
    if not resume_text or not jobs:
        return []
    results = []
    for job in jobs:
        job_text = " ".join(filter(None, [
            job.get("title", ""),
            job.get("description", ""),
            job.get("requirements", ""),
        ]))
        score       = _tfidf_similarity(resume_text, job_text)
        explanation = generate_explanation(resume_text, job, score)
        results.append({**job, "match_score": score, "explanation": explanation})
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results
