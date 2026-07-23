from __future__ import annotations


class RequirementNotFoundError(Exception):
    """Raised when a requirement does not exist."""

    def __init__(self):
        super().__init__("Requirement not found.")


class ExtractedTextNotFoundError(Exception):
    """Raised when no extracted text is available."""

    def __init__(self):
        super().__init__("No extracted text found.")