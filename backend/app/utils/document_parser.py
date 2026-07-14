from __future__ import annotations

from pathlib import Path

import fitz
from docx import Document


def extract_pdf_text(file_path: str) -> str:
    """
    Extract text from a PDF file.
    """
    document = fitz.open(file_path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text.strip()


def extract_docx_text(file_path: str) -> str:
    """
    Extract text from a DOCX file.
    """
    document = Document(file_path)

    text = "\n".join(
        paragraph.text
        for paragraph in document.paragraphs
    )

    return text.strip()


def extract_text(file_path: str) -> str:
    """
    Automatically choose the correct parser.
    """
    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        return extract_pdf_text(file_path)

    if extension == ".docx":
        return extract_docx_text(file_path)

    raise ValueError(
        f"Unsupported file type: {extension}"
    )