import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from src.ai import build_prompt  # noqa: E402
from src.analyzer import analyze, detect_sections, top_keywords  # noqa: E402
from src.parser import extract_text  # noqa: E402
from src.skills import extract_skills  # noqa: E402

GOOD = """
Priya Verma
priya@example.com | +91 91234 56789 | linkedin.com/in/priya | github.com/priya
SUMMARY
Backend developer focused on Python and cloud.
EXPERIENCE
• Built 8 FastAPI microservices handling 50,000 requests per day on AWS.
• Reduced Docker image size by 60% and cut deploy time from 12 to 3 minutes with GitHub Actions.
• Designed PostgreSQL schemas and wrote pytest suites reaching 90% coverage.
EDUCATION
B.Tech Computer Science, 2025
PROJECTS
• Developed a RAG chatbot with LangChain and FAISS answering 1,000+ queries.
SKILLS
Python, FastAPI, Docker, AWS, PostgreSQL, Git, Linux
""" + " filler" * 260

JD = "We need a Python developer with FastAPI, Docker, AWS, PostgreSQL and Kubernetes experience."


def test_skill_extraction_handles_aliases_and_symbols():
    found = extract_skills("Worked with ReactJS, Node.js, C++, scikit-learn and GitHub Actions")
    assert {"React", "Node.js", "C++", "scikit-learn", "CI/CD"} <= found


def test_skill_extraction_avoids_false_positives():
    found = extract_skills("I like to go to the mall and catch a train. We rest on Sundays.")
    assert "Go" not in found and "REST APIs" not in found


def test_sections_detected_with_variants():
    s = detect_sections("Work Experience:\n...\nTECHNICAL SKILLS\n...\nAcademic Projects\n")
    assert s["Experience"] and s["Skills"] and s["Projects"] and not s["Education"]


def test_keywords_skip_company_and_city_names():
    kws = top_keywords("Acmecorp is hiring in Bengaluru. Acmecorp needs testing, testing and monitoring.")
    assert "acmecorp" not in kws and "bengaluru" not in kws and "testing" in kws


def test_strong_resume_scores_high_and_reports_gaps():
    r = analyze(GOOD, JD)
    assert r.missing_skills == ["Kubernetes"]
    assert r.score >= 70
    assert r.quantified_ratio == 1.0
    assert all(r.contact.values())


def test_weak_resume_gets_actionable_suggestions():
    weak = "John\nResponsible for various tasks. Worked on stuff etc.\nSkills: Java"
    r = analyze(weak, JD)
    assert r.score < 40
    text = " ".join(r.suggestions)
    assert "Experience" in text and "weak phrases" in text.lower()


def test_sample_resume_pdf_is_parsed():
    pdf = ROOT / "samples" / "sample_resume.pdf"
    text = extract_text(io.BytesIO(pdf.read_bytes()), pdf.name)
    assert "Aarav Sharma" in text and "• Developed 12 REST API" in text


def test_unsupported_file_type():
    with pytest.raises(ValueError):
        extract_text(io.BytesIO(b"x"), "resume.png")


def test_ai_prompt_includes_gaps():
    prompt = build_prompt("resume text", "job text", ["Docker", "AWS"])
    assert "Docker, AWS" in prompt and "[X]" in prompt
