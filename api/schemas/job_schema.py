from typing import Any, Dict, Optional
from pydantic import BaseModel
from datetime import datetime
from src.db.models import JobStatus, JobType
from api.schemas.document_schema import DocumentResponse
class JobBase(BaseModel):
    """Base model for Job"""
    type: JobType = JobType.UPLOAD
    file: Optional[str] = None
    progress: int
    task: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    status: JobStatus = JobStatus.PENDING

class JobResponse(JobBase):
    """Response model for Job"""
    uuid: str
    created_at: datetime
    updated_at: Optional[datetime] = None
