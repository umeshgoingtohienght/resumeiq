"""Rule-based ATS analysis: skill match, keyword coverage, structure and impact.

Everything here runs offline and is deterministic, so the score is explainable
and testable. The optional AI coach (ai.py) builds on top of this report.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List

from .skills import SKILLS, extract_skills

SECTIONS = {
    "Summary": [r"summary", r"profile", r"objective", r"about me"],
    "Experience": [r"experience", r"internships?", r"employment", r"work history"],
    "Education": [r"education", r"academic qualifications?", r"academics", r"qualifications?"],
    "Skills": [r"skills", r"technical skills", r"tech stack", r"technologies"],
    "Projects": [r"projects?", r"personal projects", r"academic projects"],
    "Certifications": [r"certifications?", r"courses", r"licenses"],
    "Achievements": [r"achievements?", r"awards", r"honors", r"accomplishments"],
}
ESSENTIAL_SECTIONS = ["Experience", "Education", "Skills", "Projects"]

ACTION_VERBS = {
    "achieved", "analysed", "analyzed", "architected", "automated", "built", "collaborated",
    "created", "decreased", "delivered", "deployed", "designed", "developed", "drove",
    "engineered", "enhanced", "established", "evaluated", "executed", "generated", "implemented",
    "improved", "increased", "integrated", "launched", "led", "managed", "mentored", "migrated",
    "optimized", "optimised", "organized", "owned", "reduced", "refactored", "researched",
    "resolved", "scaled", "shipped", "simplified", "streamlined", "trained", "won", "wrote",
}
WEAK_PHRASES = [
    "responsible for", "worked on", "helped with", "involved in", "various", "etc",
    "hard working", "hardworking", "team player", "go-getter", "duties included",
]
STOPWORDS = set("""
a about above after again all also am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further
had has have having he her here hers him his how i if in into is it its itself just me more
most my no nor not now of off on once only or other our ours out over own same she should so
some such than that the their them then there these they this those through to too under
until up very was we were what when where which while who whom why will with would you your
yours we're you'll role team work working candidate candidates ability strong good experience
years year plus preferred required requirements responsibilities including include using use
knowledge understanding looking join company opportunity skills skill etc must well within across
new across e.g ie per job description position apply based able
""".split())

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){10}")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w-]+", re.I)
GITHUB_RE = re.compile(r"github\.com/[\w-]+", re.I)
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s?(?:%|x|\+|k|lakh|crore|ms|s\b|users|hrs|hours)?", re.I)


@dataclass
class Report:
    score: int
    breakdown: Dict[str, float]
    matched_skills: List[str]
    missing_skills: List[str]
    extra_skills: List[str]
    keyword_coverage: float
    matched_keywords: List[str]
    missing_keywords: List[str]
    sections: Dict[str, bool]
    contact: Dict[str, bool]
    word_count: int
    bullets: List[str]
    quantified_ratio: float
    action_verb_ratio: float
    weak_phrases: List[str]
    suggestions: List[str] = field(default_factory=list)

    @property
    def grade(self) -> str:
        if self.score >= 80:
            return "Excellent match"
        if self.score >= 65:
            return "Good match"
        if self.score >= 50:
            return "Fair match"
        return "Needs work"


GENERIC_JD_WORDS = set("""
junior senior intern internship engineer engineers engineering developer developers software
hybrid remote onsite office location company startup fictional client customer customers user
users help helps small large tool tools build building built feature features product products
business businesses field related graduate graduates welcome nice hands fast paced environment
day days week weeks month months salary ctc lpa benefit benefits culture mission vision growth
take part ship shipping manage managers manager people world class best great excellent
designer designers review reviews code idea ideas end full stack interface interfaces production
""".split())

INDIAN_CITIES = {"bengaluru", "bangalore", "mumbai", "delhi", "noida", "gurugram", "gurgaon", "pune",
                 "hyderabad", "chennai", "kolkata", "jaipur", "ahmedabad", "kochi", "indore", "india"}


SKILL_ALIASES = {a for _, aliases in SKILLS.values() for a in aliases}


def _normalise(word: str) -> str:
    word = word.lower().strip(".,;:()[]{}'\"!?")
    if word in SKILL_ALIASES:  # keep "pandas", "kubernetes" intact
        return word
    if "." in word or "+" in word or "#" in word:  # node.js, c++, c#
        return word
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith(("sses", "xes", "ches", "shes", "zes")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def top_keywords(text: str, n: int = 20) -> List[str]:
    """Most frequent meaningful words in a job description.

    Proper nouns (company names, places — words that are *always* capitalised in the JD
    and are not acronyms) are skipped because they never belong in a resume.
    """
    raw = re.findall(r"[A-Za-z][A-Za-z+#.\-/]{2,}", text)
    lower_set = {t.lower() for t in raw if t[0].islower()}
    tokens = []
    for t in raw:
        low = t.lower()
        is_proper = t[0].isupper() and not t.isupper() and low not in lower_set and low not in SKILL_ALIASES
        norm = _normalise(t)
        if is_proper or norm in STOPWORDS or norm in GENERIC_JD_WORDS or norm in INDIAN_CITIES:
            continue
        if len(norm) > 2 and not norm.isdigit():
            tokens.append(norm)
    return [w for w, _ in Counter(tokens).most_common(n)]


def detect_sections(text: str) -> Dict[str, bool]:
    """A heading is a short line (≤ 4 words) whose first few words contain a section name,
    e.g. 'EXPERIENCE', 'Work Experience:', 'Technical Skills'."""
    headings = []
    for line in text.splitlines():
        cleaned = re.sub(r"[^a-z ]", " ", line.lower()).split()
        if 0 < len(cleaned) <= 4:
            headings.append(" ".join(cleaned))
    return {
        name: any(re.match(rf"^(?:\w+ ){{0,2}}(?:{'|'.join(pats)})\b", h) for h in headings)
        for name, pats in SECTIONS.items()
    }


def extract_bullets(text: str) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    bullets = [re.sub(r"^[•\-\*▪◦●]\s*", "", ln) for ln in lines if re.match(r"^[•\-\*▪◦●]\s+\S", ln)]
    if len(bullets) < 3:  # fallback for resumes without bullet glyphs
        bullets = [ln for ln in lines if len(ln.split()) >= 8]
    return [b for b in bullets if len(b.split()) >= 4]


def analyze(resume: str, job_description: str) -> Report:
    # ---- skills -------------------------------------------------------
    resume_skills = extract_skills(resume)
    jd_skills = extract_skills(job_description)
    matched = sorted(resume_skills & jd_skills)
    missing = sorted(jd_skills - resume_skills)
    extra = sorted(resume_skills - jd_skills)
    skill_score = len(matched) / len(jd_skills) if jd_skills else 0.5

    # ---- keywords -----------------------------------------------------
    resume_tokens = {_normalise(t) for t in re.findall(r"[A-Za-z][A-Za-z+#.\-/]{2,}", resume)}
    keywords = top_keywords(job_description)
    kw_matched = [k for k in keywords if k in resume_tokens]
    kw_missing = [k for k in keywords if k not in resume_tokens]
    kw_score = len(kw_matched) / len(keywords) if keywords else 0.0

    # ---- structure ----------------------------------------------------
    sections = detect_sections(resume)
    section_score = sum(sections[s] for s in ESSENTIAL_SECTIONS) / len(ESSENTIAL_SECTIONS)

    # ---- impact -------------------------------------------------------
    bullets = extract_bullets(resume)
    quantified = [b for b in bullets if NUMBER_RE.search(b)]
    action = [b for b in bullets if b.split()[0].lower().strip(",.") in ACTION_VERBS]
    q_ratio = len(quantified) / len(bullets) if bullets else 0.0
    a_ratio = len(action) / len(bullets) if bullets else 0.0
    lowered = resume.lower()
    weak = [p for p in WEAK_PHRASES if re.search(rf"\b{re.escape(p)}\b", lowered)]
    impact_score = min(q_ratio / 0.5, 1) * 0.5 + min(a_ratio / 0.7, 1) * 0.5
    impact_score = max(impact_score - 0.05 * len(weak), 0)

    # ---- contact & length ----------------------------------------------
    contact = {
        "Email": bool(EMAIL_RE.search(resume)),
        "Phone": bool(PHONE_RE.search(resume)),
        "LinkedIn": bool(LINKEDIN_RE.search(resume)),
        "GitHub / Portfolio": bool(GITHUB_RE.search(resume)) or "portfolio" in lowered,
    }
    words = len(resume.split())
    length_ok = 1.0 if 300 <= words <= 900 else 0.6 if 200 <= words <= 1200 else 0.3
    format_score = (sum(contact.values()) / len(contact)) * 0.6 + length_ok * 0.4

    weights = {"Skills match": 40, "Keywords": 20, "Sections": 15, "Impact": 15, "Contact & format": 10}
    parts = {
        "Skills match": skill_score, "Keywords": kw_score, "Sections": section_score,
        "Impact": impact_score, "Contact & format": format_score,
    }
    breakdown = {k: round(parts[k] * weights[k], 1) for k in weights}
    score = round(sum(breakdown.values()))

    report = Report(
        score=score, breakdown=breakdown, matched_skills=matched, missing_skills=missing,
        extra_skills=extra, keyword_coverage=kw_score, matched_keywords=kw_matched,
        missing_keywords=kw_missing, sections=sections, contact=contact, word_count=words,
        bullets=bullets, quantified_ratio=q_ratio, action_verb_ratio=a_ratio, weak_phrases=weak,
    )
    report.suggestions = build_suggestions(report)
    return report


def build_suggestions(r: Report) -> List[str]:
    tips: List[str] = []
    if r.missing_skills:
        tips.append(
            f"Add the missing skills you genuinely have — {', '.join(r.missing_skills[:6])} — "
            "to your Skills section and show them in a project bullet."
        )
    for s in ESSENTIAL_SECTIONS:
        if not r.sections.get(s):
            tips.append(f"Add a clear **{s}** heading — ATS systems look for standard section names.")
    if r.quantified_ratio < 0.4:
        tips.append(
            f"Only {r.quantified_ratio:.0%} of your bullet points contain numbers. Quantify impact "
            "(e.g. 'reduced load time by 40%', 'served 2,000+ users')."
        )
    if r.action_verb_ratio < 0.6:
        tips.append("Start each bullet with a strong action verb such as Built, Designed, Optimized or Led.")
    if r.weak_phrases:
        tips.append(f"Replace weak phrases: {', '.join(repr(p) for p in r.weak_phrases[:4])}.")
    for item, ok in r.contact.items():
        if not ok:
            tips.append(f"Add your {item} in the header.")
    if r.word_count < 300:
        tips.append(f"Your resume is short ({r.word_count} words). Aim for 350–800 words with more project detail.")
    elif r.word_count > 900:
        tips.append(f"Your resume is long ({r.word_count} words). Trim it to one or two focused pages.")
    if r.missing_keywords:
        tips.append(f"Mirror important job keywords where truthful: {', '.join(r.missing_keywords[:8])}.")
    if not tips:
        tips.append("Great resume! Tailor the summary line to this specific role for an extra edge.")
    return tips
