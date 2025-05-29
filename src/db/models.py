# src/db/models.py
from sqlmodel import (
    SQLModel,
    Field,
    Session,
    Text,
    create_engine,
    MetaData,
    Column,
    Enum,
    JSON,
)
import enum
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import os
from datetime import datetime,timezone
from src.logger import get_formatted_logger


db_metadata = MetaData()
SQLModel.metadata = db_metadata
load_dotenv()
logger = get_formatted_logger(__file__)
# Database connection for data warehouse
DATABASE_URL = f"postgresql+psycopg2://{os.environ.get('DB_USER')}:{os.environ.get('DB_PASSWORD')}@{os.environ.get('DB_HOST')}:{os.environ.get('DB_PORT')}/{os.environ.get('DB_NAME')}"
db_engine = create_engine(DATABASE_URL, echo=True)


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentStep(str, enum.Enum):
    UPLOAD = "upload"
    PARSE = "parse"
    GENERATE = "generate"

class DocumentStatus(str, enum.Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class JobType(str, enum.Enum):
    UPLOAD = "upload"
    DELETE = "delete"
    PARSE = "parse"
    OTHER = "other"


### Main Table Job table manager process job
class Job(SQLModel, table=True, metadata=db_metadata):
    __tablename__ = "jobs"

    id: Optional[int] = Field(primary_key=True, default=None)
    uuid: str = Field(index=True, unique=True)
    type: JobType = Field(
        default=JobType.UPLOAD, sa_column=Column(Enum(JobType))
    )
    
    file: Optional[str] = None
    status: JobStatus = Field(
        default=JobStatus.PENDING, sa_column=Column(Enum(JobStatus))
    )
    task: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    progress: int = 0
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentJobs(SQLModel, table=True, metadata=db_metadata):
    __tablename__ = "document_jobs"

    id: Optional[int] = Field(primary_key=True, default=None)
    job_uuid: Optional[str] = Field(default=None)
    document_uuid: Optional[str] = Field(default=None)

class Document(SQLModel, table=True, metadata=db_metadata):
    __tablename__ = "documents"

    id: Optional[int] = Field(primary_key=True, default=None)
    uuid: str = Field(index=True, unique=True)
    name: Optional[str] = None
    source: Optional[str] = None
    extension: Optional[str] = None
    text: Optional[str] = Field(sa_column=Column(Text), default=None)
    step: DocumentStep = Field(
        default=DocumentStep.UPLOAD, sa_column=Column(Enum(DocumentStep))
    )
    status: DocumentStatus = Field(
        default=DocumentStatus.UPLOADING,
        sa_column=Column(Enum(DocumentStatus)),
    )
    extra_info: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    is_deleted: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Relationship - one Document can have many DocumentJobs


class DocumentChunk(SQLModel, table=True, metadata=db_metadata):
    __tablename__ = "document_chunks"

    id: Optional[int] = Field(primary_key=True, default=None)
    uuid: str = Field(index=True, unique=True)
    document_uuid: Optional[str] = Field(default=None)
    chunk_index: int = Field(default=0)
    text: Optional[str] = Field(sa_column=Column(Text), default=None)
    token_count: int = Field(default=0)
    vector: Optional[List[float]] = Field(default=None, sa_column=Column(JSON))
    extra_info: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Create tables
def create_db_tables():
    db_metadata.create_all(db_engine)
    logger.info("✅ Database tables created successfully!")


def initialize_all_databases():
    """Initialize all database tables for app architecture."""
    try:
        logger.info("🔄 Initializing database...")
        create_db_tables()
        logger.info("✅ All databases initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Error initializing databases: {str(e)}")
        return False


def get_session():
    with Session(db_engine) as session:
        try:
            yield session
        finally:
            session.close()
def get_local_session():
    return Session(db_engine)
