from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status


UPLOAD_DIR = Path("uploads")
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
}


def save_uploaded_file(file: UploadFile) -> tuple[str, str]:
    """
    Save an uploaded file and return:
    (original_filename, saved_file_path)
    """

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A filename is required.",
        )

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

    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("wb") as buffer:
        total_size = 0
        while chunk := file.file.read(1024 * 1024):
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE_BYTES:
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Uploaded files must be smaller than 10 MB.",
                )
            buffer.write(chunk)

    return file.filename, str(destination)