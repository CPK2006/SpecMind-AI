from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    document_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    document_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Cached AI Analysis
    analysis_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Cached Test Cases
    test_cases_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Cached Quality Report
    quality_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    refactored_srs_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    clarification_questions_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    improvement_report_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="Uploaded",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    project = relationship(
        "Project",
        back_populates="requirements",
    )
