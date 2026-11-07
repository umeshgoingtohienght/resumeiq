"""Extract plain text from resumes (PDF, DOCX or TXT)."""
from __future__ import annotations

import io
import re
from typing import BinaryIO

from docx import Document
from pypdf import PdfReader


def extract_text(file: BinaryIO, filename: str) -> str:
    """Return the text of an uploaded resume. Raises ValueError for unsupported types."""
    name = filename.lower()
    data = file.read()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    elif name.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        text = "\n".join(parts)
    elif name.endswith(".txt"):
        text = data.decode("utf-8", errors="ignore")
    else:
        raise ValueError("Unsupported file type. Please upload a PDF, DOCX or TXT file.")
    return clean(text)


def clean(text: str) -> str:
    # PDF generators encode bullet glyphs in many ways; normalise them all to "•"
    for glyph in ("•", "", "", "▪", "●", "‣", "⁃", "\x7f", ""):
        text = text.replace(glyph, "\n• ")
    text = re.sub(r"\n• +\n", "\n• ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()
