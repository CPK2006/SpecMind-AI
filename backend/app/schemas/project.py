from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    project_type: str


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    project_type: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    project_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)