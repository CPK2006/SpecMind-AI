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
        text += page.get_text() + "\n\n"

    document.close()

    return text.strip()


def extract_docx_text(file_path: str) -> str:
    """
    Extract text from a DOCX file.
    """
    document = Document(file_path)

    blocks: list[str] = []
    for content in document.iter_inner_content():
        if hasattr(content, "rows"):
            for row in content.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                if any(cells):
                    blocks.append(" | ".join(cells))
        elif getattr(content, "text", "").strip():
            blocks.append(content.text.strip())

    for section in document.sections:
        for label, container in (("Header", section.header), ("Footer", section.footer)):
            text = "\n".join(p.text.strip() for p in container.paragraphs if p.text.strip())
            if text:
                blocks.append(f"{label}: {text}")
    return "\n\n".join(blocks).strip()


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
