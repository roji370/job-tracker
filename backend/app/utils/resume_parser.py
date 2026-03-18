"""
Resume parsing utility using PyMuPDF (fitz).
Extracts text, skills, and structured content from PDF/DOCX resumes.

Also exposes:
  extract_experience_years(text) -> int | None
  extract_location(text)         -> str | None
  extract_roles(text)            -> list[str]
  build_cv_data(resume)          -> dict   (used by the pipeline matcher)
"""
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Common tech skills for extraction
SKILL_KEYWORDS = [
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "ruby",
    "php", "swift", "kotlin", "scala", "r", "matlab", "perl", "bash", "shell",
    # Web
    "react", "vue", "angular", "next.js", "nuxt", "svelte", "html", "css", "sass",
    "tailwind", "bootstrap", "jquery", "node.js", "express", "fastapi", "django",
    "flask", "spring", "rails", "laravel",
    # Data / AI
    "machine learning", "deep learning", "nlp", "computer vision", "tensorflow",
    "pytorch", "keras", "scikit-learn", "pandas", "numpy", "matplotlib", "spark",
    "hadoop", "kafka", "airflow", "dbt",
    # Cloud / Infra
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
    "ci/cd", "jenkins", "github actions", "linux", "nginx", "redis", "rabbitmq",
    # Databases
    "postgresql", "mysql", "mongodb", "sqlite", "elasticsearch", "cassandra",
    "dynamodb", "firestore", "snowflake", "bigquery",
    # Misc
    "git", "agile", "scrum", "rest api", "graphql", "grpc", "microservices",
]


def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text from PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(file_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except ImportError:
        logger.error("PyMuPDF (fitz) is not installed.")
        raise
    except Exception as e:
        logger.error(f"Failed to extract text from PDF {file_path}: {e}")
        raise


def extract_text_from_docx(file_path: str) -> str:
    """Extract raw text from DOCX using python-docx."""
    try:
        from docx import Document

        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(paragraphs)
    except ImportError:
        logger.error("python-docx is not installed.")
        raise
    except Exception as e:
        logger.error(f"Failed to extract text from DOCX {file_path}: {e}")
        raise


def parse_resume(file_path: str) -> dict:
    """
    Parse a resume file and return extracted text + skills.

    Returns:
        dict with keys: text, skills (list)
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif suffix in (".docx", ".doc"):
        text = extract_text_from_docx(file_path)
    elif suffix == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    skills = extract_skills(text)
    return {"text": text, "skills": skills}


def extract_skills(text: str) -> list[str]:
    """Extract known tech skills from resume text."""
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        # Use word boundary matching
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found.append(skill)
    return list(set(found))


def extract_email(text: str) -> str | None:
    """Extract first email found in text."""
    match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else None


def extract_phone(text: str) -> str | None:
    """Extract first phone number found in text."""
    match = re.search(
        r"(\+?\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}", text
    )
    return match.group(0) if match else None


# ── Structured extraction for the weighted matcher ────────────────────────────

# Current year — computed once at import time so it stays correct year-over-year
from datetime import date as _date
_CURRENT_YEAR: int = _date.today().year

# Role title keywords to scan for in resume text
_ROLE_KEYWORDS: list[str] = [
    "software engineer", "backend engineer", "frontend engineer",
    "full stack engineer", "fullstack engineer", "data engineer",
    "data scientist", "ml engineer", "devops engineer", "cloud engineer",
    "mobile developer", "android developer", "ios developer",
    "product manager", "engineering manager", "tech lead",
    "software developer", "web developer", "site reliability engineer",
    "security engineer", "qa engineer", "test engineer",
    "solutions architect", "systems analyst", "database administrator",
    "machine learning engineer", "ai engineer",
]

# Known locations for simple city/country detection
_KNOWN_CITIES: list[str] = [
    "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad",
    "chennai", "pune", "kolkata", "new york", "san francisco",
    "london", "berlin", "toronto", "singapore", "sydney",
]
_COUNTRY_MAP: dict[str, str] = {
    "india":         "India",
    "united states": "US",
    "united kingdom": "UK",
    "canada":        "Canada",
    "australia":     "Australia",
    "germany":       "Germany",
    "singapore":     "Singapore",
}


def extract_experience_years(text: str) -> int | None:
    """
    Infer total years of experience from resume text.

    Strategies (tried in order):
    1. Explicit pattern: "X years of experience" / "X+ yrs experience"
    2. Year-range heuristic: earliest 4-digit year found → _CURRENT_YEAR

    Returns int or None if no signal found.
    """
    # Strategy 1: explicit phrase
    explicit_patterns = [
        r"(\d+)\+?\s*years?\s+of\s+(?:professional\s+)?experience",
        r"(\d+)\+?\s*yrs?\s+of\s+(?:professional\s+)?experience",
        r"experience\s*(?:of|:)?\s+(\d+)\+?\s*years?",
    ]
    for pat in explicit_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))

    # Strategy 2: earliest 20xx year in text → compute tenure
    years_found = re.findall(r"\b(20\d{2})\b", text)
    if len(years_found) >= 2:
        years_int = sorted(int(y) for y in years_found)
        computed  = _CURRENT_YEAR - years_int[0]
        if 0 <= computed <= 40:
            return computed

    return None


def extract_location(text: str) -> str | None:
    """
    Attempt to identify the candidate's location from resume text.

    Checks known cities first, then falls back to country names.
    Returns a human-readable location string or None.
    """
    text_lower = text.lower()

    for city in _KNOWN_CITIES:
        if city in text_lower:
            return city.title()

    for key, val in _COUNTRY_MAP.items():
        if key in text_lower:
            return val

    return None


def extract_roles(text: str) -> list[str]:
    """
    Extract job role titles from resume text using a keyword list.
    Returns de-duplicated role strings in title-case, preserving order.
    """
    text_lower = text.lower()
    found: list[str] = []
    for role in _ROLE_KEYWORDS:
        if re.search(r"\b" + re.escape(role) + r"\b", text_lower):
            found.append(role.title())
    # Preserve insertion order while deduplicating
    return list(dict.fromkeys(found))


def build_cv_data(resume) -> dict:
    """
    Assemble a structured cv_data dict from a Resume ORM object.

    This is the primary input to match_job() / rank_jobs().

    Returns:
        {
            "roles":              list[str],
            "skills":             list[str],
            "experience_years":   int | None,
            "location":           str | None,
            "preferred_location": str,        # defaults to "Remote"
        }
    """
    text = resume.extracted_text or ""
    return {
        "roles":              extract_roles(text),
        "skills":             resume.skills or [],
        "experience_years":   extract_experience_years(text),
        "location":           extract_location(text),
        "preferred_location": "Remote",  # Conservative default; shown in UI later
    }
