from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base



class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    project_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    creation_mode: Mapped[str] = mapped_column(
        String(20),
        default="upload",
        nullable=False,
    )

    idea_pitch: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    generated_srs_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="Draft",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    requirements = relationship(
    "Requirement",
    back_populates="project",
    cascade="all, delete-orphan",
)