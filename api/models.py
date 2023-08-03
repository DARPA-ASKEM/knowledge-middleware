from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

class Status(Enum):
    started = "started"
    finished = "finished"    
    cancelled = "cancelled"
    complete = "complete"
    error = "error"
    queued = "queued"
    running = "running"
    failed = "failed"

class Result(BaseModel):
    created_at: datetime
    enqueued_at: datetime
    started_at: datetime
    job_result: dict | None
    job_error: str | None

class ExtractionJob(BaseModel):
    id: str
    status: Status
    result: Result | None

class EquationType(Enum):
    LATEX = "latex"
    MATHML = "mathml"