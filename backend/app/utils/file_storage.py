from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status


UPLOAD_DIR = Path("uploads")

ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
}


def save_uploaded_file(file: UploadFile) -> tuple[str, str]:
    """
    Save an uploaded file and return:
    (original_filename, saved_file_path)
    """

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are allowed.",
        )

    folder = ALLOWED_EXTENSIONS[extension]

    unique_filename = f"{uuid.uuid4()}{extension}"

    destination = (
        UPLOAD_DIR
        / folder
        / unique_filename
    )

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return file.filename, str(destination)