"""Optional AI coach powered by Google Gemini (structured JSON output)."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from google import genai
from google.genai import types

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM = (
    "You are an expert technical recruiter and resume coach for early-career candidates in India. "
    "Be specific, honest and practical. Never invent experience the candidate does not have: "
    "rewrite only what is in the resume."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "A tailored 2-3 line professional summary"},
        "rewritten_bullets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"original": {"type": "string"}, "improved": {"type": "string"}},
                "required": ["original", "improved"],
            },
        },
        "interview_questions": {"type": "array", "items": {"type": "string"}},
        "learning_plan": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "rewritten_bullets", "interview_questions", "learning_plan"],
}


def build_prompt(resume: str, job_description: str, missing_skills: list[str]) -> str:
    return (
        f"JOB DESCRIPTION:\n{job_description[:6000]}\n\n"
        f"RESUME:\n{resume[:8000]}\n\n"
        f"Skills in the job that the resume lacks: {', '.join(missing_skills) or 'none'}\n\n"
        "Return JSON with:\n"
        "1. summary — a tailored professional summary for this job.\n"
        "2. rewritten_bullets — pick the 4 weakest resume bullets and rewrite each with an action verb, "
        "the tech used and a measurable result (use [X] as a placeholder where a number is unknown).\n"
        "3. interview_questions — 6 likely interview questions for this candidate and job.\n"
        "4. learning_plan — 4 concrete steps (with a mini-project idea) to close the skill gaps."
    )


def coach(resume: str, job_description: str, missing_skills: list[str], api_key: str) -> Dict[str, Any]:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL,
        contents=build_prompt(resume, job_description, missing_skills),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            temperature=0.4,
            response_mime_type="application/json",
            response_schema=SCHEMA,
        ),
    )
    return json.loads(response.text)
