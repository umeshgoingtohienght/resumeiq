"""Generates samples/sample_resume.pdf — a fictional candidate used for the demo."""
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

BLUE = HexColor("#1f4f9a")
name = ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=BLUE)
contact = ParagraphStyle("contact", fontName="Helvetica", fontSize=9.5, leading=13)
head = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=BLUE,
                      spaceBefore=9, spaceAfter=3)
body = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=13.5)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=10, bulletIndent=0)
sub = ParagraphStyle("sub", parent=body, fontName="Helvetica-Bold")

story = [
    Paragraph("Aarav Sharma", name),
    Paragraph("Jaipur, Rajasthan · aarav.sharma.dev@example.com · +91 98765 43210 · "
              "github.com/aarav-sharma-dev", contact),
    Paragraph("SUMMARY", head),
    Paragraph("Final-year B.Tech Computer Science student passionate about web development and machine "
              "learning. Hardworking team player looking for an opportunity to grow.", body),
    Paragraph("EDUCATION", head),
    Paragraph("B.Tech, Computer Science — Rajasthan Technical University (2022–2026) · CGPA 8.4/10", body),
    Paragraph("SKILLS", head),
    Paragraph("Python, JavaScript, React, Node.js, Express, MongoDB, SQL, Pandas, NumPy, scikit-learn, "
              "Git, HTML, CSS, REST APIs, Data Structures and Algorithms", body),
    Paragraph("EXPERIENCE", head),
    Paragraph("Web Development Intern — BrightLeaf Solutions, Jaipur (May 2025 – Jul 2025)", sub),
    Paragraph("Responsible for building React components for the company dashboard.", bullet, bulletText="•"),
    Paragraph("Developed 12 REST API endpoints in Node.js and Express, cutting average response time by 35%.",
              bullet, bulletText="•"),
    Paragraph("Worked on bug fixes and various UI improvements.", bullet, bulletText="•"),
    Paragraph("PROJECTS", head),
    Paragraph("Student Performance Predictor — Python, scikit-learn, Streamlit", sub),
    Paragraph("Trained a random forest model on 5,000 student records reaching 87% accuracy.",
              bullet, bulletText="•"),
    Paragraph("Built an interactive Streamlit app so teachers can flag at-risk students early.",
              bullet, bulletText="•"),
    Paragraph("Campus Event Portal — React, Node.js, MongoDB", sub),
    Paragraph("Helped with the backend and database design for event registrations.", bullet, bulletText="•"),
    Paragraph("Implemented JWT authentication and role-based access for 3 user types.",
              bullet, bulletText="•"),
    Paragraph("ACHIEVEMENTS", head),
    Paragraph("Top 10 out of 180 teams in Smart India Hackathon internal round (2024).", bullet, bulletText="•"),
    Paragraph("Solved 300+ problems on LeetCode and GeeksforGeeks.", bullet, bulletText="•"),
]

out = Path(__file__).with_name("sample_resume.pdf")
SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                  topMargin=16 * mm, bottomMargin=16 * mm, title="Aarav Sharma - Resume").build(story)
print(f"Saved {out}")
