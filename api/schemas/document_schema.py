# api/schemas/document.py
from typing import Any, Dict, Optional
from pydantic import BaseModel
from datetime import datetime
from src.db.models import DocumentStatus
from llama_index.core import Document
class DocumentBase(BaseModel):
    """Base model for Document"""
    name: str
    source: Optional[str] = None
    extension: str
    extra_info: Optional[Dict[str, Any]] = None

class DocumentCreate(BaseModel):
    """Create model for Document"""
    pass

class DocumentUpdate(BaseModel):
    """Update model for Document"""
    name: Optional[str] = None
    source: Optional[str] = None
    extension: Optional[str] = None
    status: Optional[DocumentStatus] = None
    extra_info: Optional[Dict[str, Any]] = None

class DocumentResponse(DocumentBase):
    """Response model for Document"""
    uuid: str
    status: DocumentStatus
    job_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    