from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    project_type: str = "Software Project"
    creation_mode: Literal["pitch", "upload"] = "upload"
    idea_pitch: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    project_type: str | None = None
    creation_mode: Literal["pitch", "upload"] | None = None
    idea_pitch: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    project_type: str
    creation_mode: Literal["pitch", "upload"]
    idea_pitch: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)