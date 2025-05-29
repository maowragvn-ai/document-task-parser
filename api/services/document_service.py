# api/services/document_service.py
import uuid
from sqlmodel import Session, select
from fastapi import UploadFile, HTTPException
from src.logger import get_formatted_logger
from src.db import (
    JobStatus,
    JobType,
    Document,
    DocumentStatus,DocumentStep,
    DocumentJobs, Job
)
from src.tasks import (
    upload_document,
    parse_document,
)
from api.schemas.document_schema import DocumentResponse
from api.schemas.job_schema import JobResponse
from api.services.job_service import JobService
import base64

logger = get_formatted_logger(__name__)


class DocumentService:
    def __init__(self, session: Session):
        self.session = session
        self.job_service = JobService(session)

    async def create_and_upload_document(
        self, file: UploadFile
    ) -> DocumentResponse:
        """Create a new document and start the upload process asynchronously"""
        # Generate job ID and document ID
        job_uuid = str(uuid.uuid4())
        doc_uuid = str(uuid.uuid4())

        try:
            filename = file.filename.lower() if file.filename else "unknown_file"

            # Read file content
            file_content = await file.read()

            # Create job record first
            job = await self.job_service.create_job(
                job_uuid=job_uuid,
                message=f"Upload task submitted to queue, document: {filename}",
                file=filename,
                type=JobType.UPLOAD,
                status=JobStatus.PENDING,  # Change to PROCESSING immediately
            )

            # Create document record with initial status
            document = Document(
                uuid=doc_uuid,
                name=filename,
                step=DocumentStep.UPLOAD,
                source="",  # Temporary source until updated by task
                extension=filename.split(".")[-1] if "." in filename else "",
                status=DocumentStatus.UPLOADING,  # New status to indicate process started
                text=base64.b64encode(file_content).decode("ascii"),
                extra_info={},
            )

            self.session.add(document)
            self.session.flush()
            self.session.refresh(document)
            response = DocumentResponse(**document.model_dump())

            document_jobs = DocumentJobs(document_uuid=document.uuid, job_uuid=job_uuid)
            self.session.add(document_jobs)
            self.session.commit()
            
            upload_document.apply_async(
                args=[
                    "test-bucket",
                    file_content,
                    filename,
                ],
                task_id=job_uuid,
            )
            response.job_id = job_uuid  # Include job ID for status checking

            return response

        except Exception as e:
            # Rollback and set failure status
            self.session.rollback()
            
            if 'job' in locals():
                await self.job_service.update_job(
                    job_uuid=job_uuid,
                    task={"error": str(e)},
                    status=JobStatus.FAILED,
                    message=f"Failed to initiate document upload: {str(e)}",
                )
                
            logger.error(f"Error creating document: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to create document: {str(e)}"
            )

    async def parse_document(self, document_uuid: str) -> DocumentResponse:
        """Parse a document and extract its content"""
        job_uuid = str(uuid.uuid4())
        job = None
        document = None
        document_jobs = None
        document = await self.get_document(document_uuid)
        try:
            if (document.step == DocumentStep.PARSE and document.status == DocumentStatus.PARSED) or document.step == DocumentStep.GENERATE:
                # Retrieve the parsing job to get parsed documents
                statement = (
                    select(DocumentJobs)
                    .join(Document, DocumentJobs.document_uuid == Document.uuid)
                    .where(Document.uuid == document_uuid)
                )
                existing_doc_jobs = self.session.exec(statement).all()

                # Find the PARSE job
                for doc_job in existing_doc_jobs:
                    job_details = await self.job_service.get_job_by_uuid(doc_job.job_uuid)
                    if (
                        job_details
                        and job_details.type == JobType.PARSE
                        and job_details.status == JobStatus.COMPLETED
                    ):
                        # Return the existing parsed data
                        return DocumentResponse(
                            **document.model_dump(),
                            job_id=job_details.uuid,
                        )
            if (
                (document.step == DocumentStep.UPLOAD and document.status == DocumentStatus.UPLOADED)
                or
                (document.step == DocumentStep.PARSE and
                 (document.status == DocumentStatus.FAILED or document.status == DocumentStatus.PARSING)
                )
            ):
                # Create a new parsing job
                job = await self.job_service.create_job(
                    job_uuid=job_uuid,
                    message=f"Parsing document: {document_uuid}",
                    file=document.name,
                    type=JobType.PARSE,
                    status=JobStatus.PENDING,
                )
                document.step = DocumentStep.PARSE
                document.status = DocumentStatus.PARSING
                self.session.add(document)
                self.session.flush()
                self.session.refresh(document)

                document_jobs = DocumentJobs(document_uuid=document.uuid, job_uuid=job.uuid)
                self.session.add(document_jobs)
                self.session.flush()
                self.session.commit()
                self.session.refresh(document)
                # Submit parsing task
                parse_document.apply_async(
                    args=[
                        document.source
                    ],
                    task_id=job_uuid,
                )

                return DocumentResponse(
                    **document.model_dump(),job_id = job_uuid
                )
            raise HTTPException(
                status_code=400, detail=f"Document is not in a valid state for parsing (current state: {document.step, document.status})"
            )

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Rollback and set failure status
            self.session.rollback()
            
            if 'job' in locals():
                await self.job_service.update_job(
                    job_uuid=job_uuid,
                    task={"error": str(e)},
                    status=JobStatus.FAILED,
                    message=f"Failed to pasre document: {str(e)}",
                )
                
            logger.error(f"Error pasre document: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to pasre document: {str(e)}"
            )   
    async def get_document(self, document_uuid: str) -> Document:
        """Retrieve a document by UUID"""
        try:
            statement = select(Document).where(Document.uuid == document_uuid)
            document = self.session.exec(statement).first()
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")
            return document
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error getting document: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get document: {str(e)}"
            )

    # Add a new endpoint to check the status of a job
    async def get_document_status(self, job_uuid: str) -> JobResponse:
        """Get the current status of a job"""
        try:
            job = await self.job_service.get_job_by_uuid(job_uuid)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
                
            # If the job is complete and successful, get related document
            if job.status == JobStatus.COMPLETED:
                # Find the document related to this job
                statement = (
                    select(Document)
                    .join(DocumentJobs, DocumentJobs.document_uuid == Document.uuid)
                    .join(Job, DocumentJobs.job_uuid == Job.uuid)
                    .where(Job.uuid == job_uuid)
                )
                document = self.session.exec(statement).first()
                
                if document:
                    return JobResponse(**job.model_dump())
            
            # Otherwise return just the job status
            return JobResponse(**job.model_dump())
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting job status: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get job status: {str(e)}"
            )
