"""
Playwright-based scraper for Amazon Jobs (jobs.amazon.com).
Runs headless and returns structured job data.
Fix #8: Fallback jobs are now marked with is_synthetic=True so the DB
and UI can distinguish real scraped descriptions from generated ones.
"""
import asyncio
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

AMAZON_JOBS_URL = (
    "https://www.amazon.jobs/en/search?offset=0&result_limit=20&sort=relevant"
    "&category[]=software-development&country[]=USA"
)


async def scrape_amazon_jobs(
    query: str = "software engineer",
    location: str = "USA",
    limit: int = 20,
) -> list[dict]:
    """
    Scrape Amazon jobs using Playwright headless browser.

    Returns:
        List of job dicts. Jobs from the actual site have is_synthetic=False.
        Fallback jobs (when scraping fails) have is_synthetic=True.
    """
    try:
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    except ImportError:
        logger.error("Playwright is not installed.")
        raise

    jobs = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 720},
            )
            page = await context.new_page()

            url = (
                f"https://www.amazon.jobs/en/search?"
                f"offset=0&result_limit={limit}&sort=relevant"
                f"&base_query={query.replace(' ', '+')}"
                f"&loc_query={location}"
            )

            logger.info("Scraping Amazon Jobs: %s", url)
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")

            try:
                await page.wait_for_selector(".job-tile", timeout=15000)
            except PlaywrightTimeout:
                logger.warning("Job tiles not found. Page may have changed structure.")
                await browser.close()
                return _get_fallback_jobs(query)

            job_tiles = await page.query_selector_all(".job-tile")
            logger.info("Found %d job tiles", len(job_tiles))

            for tile in job_tiles[:limit]:
                try:
                    job = await _extract_job_from_tile(tile, page)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning("Failed to extract job from tile: %s", e)
                    continue

            await browser.close()

    except PlaywrightTimeout:
        logger.error("Playwright timed out while scraping. Using fallback data.")
        return _get_fallback_jobs(query)
    except Exception as e:
        logger.error("Scraping failed: %s. Using fallback data.", e)
        return _get_fallback_jobs(query)

    if not jobs:
        logger.warning("No jobs scraped. Returning fallback dataset.")
        return _get_fallback_jobs(query)

    return jobs


async def _extract_job_from_tile(tile, page) -> Optional[dict]:
    """Extract structured data from a single Amazon job tile."""
    try:
        title_el = await tile.query_selector("h3.job-title a, .job-title a")
        title = await title_el.inner_text() if title_el else "Unknown Position"
        title = title.strip()

        href = await title_el.get_attribute("href") if title_el else None
        url = f"https://www.amazon.jobs{href}" if href else None

        job_id = None
        if url:
            match = re.search(r"/jobs/(\d+)", url)
            job_id = match.group(1) if match else None

        location_el = await tile.query_selector(".location-and-id .location")
        location = await location_el.inner_text() if location_el else "Remote"
        location = location.strip()

        posted_el = await tile.query_selector(".updated-time")
        posted_date = await posted_el.inner_text() if posted_el else ""
        posted_date = posted_date.strip()

        category_el = await tile.query_selector(".job-category")
        category = await category_el.inner_text() if category_el else ""

        description = _generate_description(title, category)

        return {
            "title": title,
            "company": "Amazon",
            "location": location,
            "description": description,
            "requirements": _generate_requirements(title),
            "url": url,
            "source": "amazon",
            "job_id_external": job_id,
            "employment_type": "Full-time",
            "posted_date": posted_date,
            # Fix #8: Real scraped jobs — description is generated but job metadata is real
            # Mark as synthetic since we can't scrape rich description from the tile alone
            "is_synthetic": True,
        }
    except Exception as e:
        logger.warning("Error parsing job tile: %s", e)
        return None


def _generate_description(title: str, category: str = "") -> str:
    """Generate a basic description based on job title."""
    base = (
        f"We are looking for a talented {title} to join our team at Amazon. "
        f"You will work on cutting-edge technology at scale, solving complex problems "
        f"that impact millions of customers worldwide. "
    )
    if category:
        base += f"This role falls under {category}. "
    base += (
        "You'll collaborate with cross-functional teams, drive innovation, "
        "and contribute to Amazon's mission of being the Earth's most customer-centric company."
    )
    return base


def _generate_requirements(title: str) -> str:
    """Generate requirements string based on job title."""
    title_lower = title.lower()
    if "data" in title_lower or "ml" in title_lower or "machine learning" in title_lower:
        return (
            "BS/MS in Computer Science or related field. "
            "3+ years experience in data engineering or machine learning. "
            "Proficiency in Python, SQL, Spark. Experience with AWS services. "
            "Strong understanding of ML algorithms and model deployment."
        )
    elif "frontend" in title_lower or "ui" in title_lower or "react" in title_lower:
        return (
            "BS in Computer Science or equivalent. "
            "3+ years of experience with React/TypeScript. "
            "Strong CSS and web performance skills. "
            "Experience with testing frameworks."
        )
    elif "devops" in title_lower or "sre" in title_lower or "platform" in title_lower:
        return (
            "BS in Computer Science or related field. "
            "3+ years in DevOps or SRE roles. "
            "Experience with Kubernetes, Terraform, CI/CD pipelines. "
            "Strong scripting skills (Python, Bash)."
        )
    else:
        return (
            "BS/MS in Computer Science or related field. "
            "3+ years of software development experience. "
            "Proficiency in one or more programming languages (Java, Python, C++). "
            "Strong problem-solving skills and customer obsession."
        )


def _get_fallback_jobs(query: str = "software engineer") -> list[dict]:
    """
    Return realistic fallback job data when scraping fails.
    Fix #8: All fallback jobs are marked is_synthetic=True.
    """
    return [
        {
            "title": "Software Development Engineer II",
            "company": "Amazon",
            "location": "Seattle, WA",
            "description": (
                "Join Amazon's core platform team to design and build highly scalable "
                "distributed systems that power Amazon's retail infrastructure. You'll "
                "work on low-latency, high-availability services serving millions of TPS."
            ),
            "requirements": (
                "BS/MS in CS. 4+ years software development experience. "
                "Deep expertise in Java or C++. Experience with distributed systems, "
                "microservices architecture, and AWS cloud services."
            ),
            "url": "https://www.amazon.jobs/en/jobs/2345678/sde-ii",
            "source": "amazon",
            "job_id_external": "2345678",
            "employment_type": "Full-time",
            "posted_date": "2 days ago",
            "is_synthetic": True,
        },
        {
            "title": "Senior Data Engineer",
            "company": "Amazon",
            "location": "New York, NY",
            "description": (
                "Build and optimize data pipelines that process petabytes of customer "
                "behavior data. You'll design ETL workflows, work with Redshift, Glue, "
                "and contribute to Amazon's data lake infrastructure."
            ),
            "requirements": (
                "BS in CS or Data Engineering. 5+ years data engineering experience. "
                "Proficient in Python, Spark, SQL. Expertise with AWS Glue, Redshift, S3. "
                "Experience with streaming data using Kafka or Kinesis."
            ),
            "url": "https://www.amazon.jobs/en/jobs/2345679/senior-data-engineer",
            "source": "amazon",
            "job_id_external": "2345679",
            "employment_type": "Full-time",
            "posted_date": "1 day ago",
            "is_synthetic": True,
        },
        {
            "title": "Machine Learning Engineer",
            "company": "Amazon",
            "location": "Palo Alto, CA",
            "description": (
                "Design and deploy production ML models for Amazon's recommendation "
                "engine. Work with massive datasets, build feature pipelines, and use "
                "SageMaker to train and serve models at scale."
            ),
            "requirements": (
                "MS/PhD in ML or CS. 3+ years ML engineering experience. "
                "Strong Python, TensorFlow/PyTorch skills. "
                "Experience with model deployment and MLOps practices."
            ),
            "url": "https://www.amazon.jobs/en/jobs/2345680/ml-engineer",
            "source": "amazon",
            "job_id_external": "2345680",
            "employment_type": "Full-time",
            "posted_date": "3 days ago",
            "is_synthetic": True,
        },
        {
            "title": "Frontend Engineer – React",
            "company": "Amazon",
            "location": "Remote",
            "description": (
                "Build beautiful, fast, and accessible customer-facing UI experiences "
                "using React and TypeScript. Work on A/B experiments that affect "
                "millions of Amazon customers globally."
            ),
            "requirements": (
                "BS in CS or equivalent. 3+ years React experience. "
                "TypeScript proficiency. Performance optimization skills. "
                "Experience with design systems and accessibility (WCAG)."
            ),
            "url": "https://www.amazon.jobs/en/jobs/2345681/frontend-engineer",
            "source": "amazon",
            "job_id_external": "2345681",
            "employment_type": "Full-time",
            "posted_date": "4 days ago",
            "is_synthetic": True,
        },
        {
            "title": "DevOps / Platform Engineer",
            "company": "Amazon",
            "location": "Austin, TX",
            "description": (
                "Build and maintain mission-critical CI/CD infrastructure and Kubernetes "
                "clusters. Improve developer experience, deployment velocity, and "
                "system reliability across Amazon's engineering organization."
            ),
            "requirements": (
                "BS in CS or equivalent. 4+ years DevOps experience. "
                "Kubernetes, Terraform, Jenkins expertise. "
                "Strong scripting skills in Python and Bash. "
                "Experience with observability tools (Prometheus, Grafana, Datadog)."
            ),
            "url": "https://www.amazon.jobs/en/jobs/2345682/devops-platform-engineer",
            "source": "amazon",
            "job_id_external": "2345682",
            "employment_type": "Full-time",
            "posted_date": "5 days ago",
            "is_synthetic": True,
        },
        {
            "title": "Backend Engineer – Python/FastAPI",
            "company": "Amazon",
            "location": "Vancouver, BC",
            "description": (
                "Develop high-performance REST APIs and microservices using Python and "
                "FastAPI. Design PostgreSQL schemas, integrate with AWS services, and "
                "ensure API reliability and scalability."
            ),
            "requirements": (
                "BS in CS. 3+ years Python backend development. "
                "FastAPI or Django REST Framework experience. "
                "PostgreSQL, Redis proficiency. Docker and AWS experience."
            ),
            "url": "https://www.amazon.jobs/en/jobs/2345683/backend-engineer-python",
            "source": "amazon",
            "job_id_external": "2345683",
            "employment_type": "Full-time",
            "posted_date": "1 week ago",
            "is_synthetic": True,
        },
        {
            "title": "Cloud Solutions Architect",
            "company": "Amazon Web Services",
            "location": "Chicago, IL",
            "description": (
                "Work directly with enterprise customers to architect, design, and build "
                "cloud solutions on AWS. Lead technical workshops, create reference "
                "architectures, and drive customer success."
            ),
            "requirements": (
                "BS in CS or Engineering. 6+ years cloud architecture experience. "
                "AWS Solutions Architect Professional certification preferred. "
                "Strong communication and presentation skills."
            ),
            "url": "https://www.amazon.jobs/en/jobs/2345684/cloud-architect",
            "source": "amazon",
            "job_id_external": "2345684",
            "employment_type": "Full-time",
            "posted_date": "2 days ago",
            "is_synthetic": True,
        },
        {
            "title": "Security Engineer",
            "company": "Amazon",
            "location": "Washington, D.C.",
            "description": (
                "Protect Amazon's infrastructure by identifying and mitigating security "
                "vulnerabilities. Conduct penetration testing, security reviews, and "
                "build automated security tooling."
            ),
            "requirements": (
                "BS in CS or Security. 4+ years application security experience. "
                "CISSP or CEH certification preferred. "
                "Proficiency in vulnerability assessment, SAST/DAST tools."
            ),
            "url": "https://www.amazon.jobs/en/jobs/2345685/security-engineer",
            "source": "amazon",
            "job_id_external": "2345685",
            "employment_type": "Full-time",
            "posted_date": "3 days ago",
            "is_synthetic": True,
        },
    ]
