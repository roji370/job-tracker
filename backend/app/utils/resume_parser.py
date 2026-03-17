"""
Resume parsing utility using PyMuPDF (fitz).
Extracts text, skills, and structured content from PDF/DOCX resumes.
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
