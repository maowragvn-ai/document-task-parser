# src/tasks/document_task.py
import os
import tempfile
from pathlib import Path
from typing import Any, Dict
import uuid
from datetime import datetime
import celery
from sqlmodel import Session, select
import traceback
from asgiref.sync import async_to_sync
from src.celery_worker import celery_app
# from src.db.aws import get_aws_s3_client
from src.readers import FileExtractor, parse_multiple_files
from src.config import global_config
from src.logger import get_formatted_logger
from src.db import Job, Document,DocumentChunk, DocumentJobs,JobStatus, DocumentStatus,get_local_session
from src.tasks.utils import count_tokens_from_string,clean_text_for_db, TaskResponse

logger = get_formatted_logger(__file__)

# Initialize services that will be used by tasks
# s3_client = get_aws_s3_client()

@celery_app.task(name="document.upload", bind=True, max_retries=3)
def upload_document(
    self: celery.Task,
    bucket_name: str,
    file_content: bytes,
    filename: str,
    session: Session = None,
) -> Dict[str, Any]:
    """
    Upload a document to storage

    Args:
        bucket_name: S3 bucket name or storage location identifier
        file_content: Binary content of the file
        filename: Original filename
        session: Database session (optional)

    Returns:
        TaskResponse object with upload results
    """
    # Use provided session or create a new one
    db_session = session or get_local_session()
    temp_file = None
    
    try:
        # Fetch job and related document in a single operation
        statement = (
            select(Job, Document)
            .join(DocumentJobs, DocumentJobs.job_uuid == Job.uuid)
            .join(Document, DocumentJobs.document_uuid == Document.uuid)
            .where(Job.uuid == self.request.id)
        )
        result = db_session.exec(statement).first()
        if not result:
            raise ValueError(f"Job with UUID {self.request.id} not found")
            
        job, document = result
        
        # Update state and job status
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100})
        job.status = JobStatus.PROCESSING
        db_session.add(job)
        db_session.flush()
        
        # Generate storage path
        original_filename = Path(filename)
        extension = original_filename.suffix.lower() if original_filename.suffix else ".unknown"
        date_path = datetime.now().strftime("%Y/%m/%d")
        file_name = f"{uuid.uuid4()}_{filename}"
        
        # Create temp directory
        temp_dir = Path(tempfile.gettempdir()) / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Use context manager for temp file handling
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension, dir=temp_dir) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            self.update_state(state="PROGRESS", meta={"current": 50, "total": 100})
            
            # Set up storage path
            # file_path = os.path.join(date_path, file_name)
            
            # Uncomment and use this for S3 storage when needed
            # file_path_in_s3 = s3_client.upload_file(
            #     bucket_name=bucket_name,
            #     object_name=file_path,
            #     file_path=temp_file_path,
            # )
            # document.source = file_path_in_s3
            
            # For local storage
            
            local_upload_path = os.path.join("data/upload/", date_path)
            os.makedirs(local_upload_path, exist_ok=True)
            file_path = os.path.join(local_upload_path, file_name)
            # Copy file to local storage
            with open(file_path, "wb") as f:
                f.write(file_content)
                
            document.source = file_path
            document.status = DocumentStatus.UPLOADED
            
            # Update state and create response
            self.update_state(state="PROGRESS", meta={"current": 100, "total": 100})
            
            task_response = TaskResponse(
                status="success",
                task_id=self.request.id,
                task_name=self.request.task,
                task_retry=self.request.retries,
                task_info={
                    "document_uuid": document.uuid,
                    "bucket_name": bucket_name,
                    "file_source": file_path,
                    "file_name": filename,
                },
                message="Document uploaded successfully",
            )
            
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.message = "Document uploaded successfully"
            job.task = task_response.model_dump()
            
            # Save changes
            db_session.add(job)
            db_session.add(document)
            
            return task_response.model_dump()
            
        finally:
            # Clean up temp file - moved to finally block for better handling
            if os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        logger.error(traceback.format_exc())
        
        try:
            # Try to retry the task
            logger.info(f"Retrying task {self.request.id}, attempt {self.request.retries + 1}")
            self.retry(countdown=10 * (self.request.retries + 1), exc=e)
        except self.MaxRetriesExceededError:
            # Handle max retries case
            task_response = TaskResponse(
                    status="error",
                    task_id=self.request.id,
                    task_name=self.request.task,
                    task_retry=self.request.retries,
                    task_info={
                        "document_uuid": document.uuid,
                        "bucket_name": bucket_name,
                        "file_source": "",
                        "file_name": filename,
                    },
                    message=f"Task failed after {self.request.retries} retries: {str(e)}",
                )
            if 'document' in locals() and 'job' in locals():
                document.status = DocumentStatus.FAILED
                job.status = JobStatus.FAILED
                job.progress = 0
                job.message = "Document uploaded failed"
        
                job.task = task_response.model_dump()
                db_session.add(job)
                db_session.add(document)
            
            return task_response.model_dump()
    
    finally:
        # Only commit if we created the session
        if session is None and db_session:
            try:
                db_session.commit()
            except Exception as commit_error:
                logger.error(f"Error committing transaction: {str(commit_error)}")
                db_session.rollback()
                
                # Re-raise if this wasn't already an error case
                if 'e' not in locals():
                    raise
            finally:
                db_session.close()
                
@celery_app.task(name="document.parse", bind=True, max_retries=3)
def parse_document(
    self: celery.Task,
    file_path: str,
    session: Session = None,
) -> Dict[str, Any]:
    """
    Parse a document and extract its content

    Args:
        file_path: Path to the document file
        session: Database session (optional)

    Returns:
        TaskResponse with extracted documents and token count
    """
    # Use provided session or create a new one
    db_session = session or get_local_session()
    
    try:
        # Fetch job and related document in a single operation
        statement = (
            select(Job, Document)
            .join(DocumentJobs, DocumentJobs.job_uuid == Job.uuid)
            .join(Document, DocumentJobs.document_uuid == Document.uuid)
            .where(Job.uuid == self.request.id)
        )
        result = db_session.exec(statement).first()
        if not result:
            raise ValueError(f"Job with UUID {self.request.id} not found")
            
        job, document = result
        
        # Update state and job status
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100})
        job.status = JobStatus.PROCESSING
        job.progress = 10
        job.message = "Processing document"
        db_session.add(job)
        db_session.flush()

        # Verify file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        file_extractor = FileExtractor()
        # Process the document using FileExtractor
        extractor = file_extractor.get_extractor_for_file(file_path)
        if not extractor:
            raise ValueError(f"No suitable extractor found for file: {file_path}")

        self.update_state(state="PROGRESS", meta={"current": 30, "total": 100})
        job.progress = 30
        job.message = "Extracting content from document"
        db_session.add(job)
        db_session.flush()
        # Parse the files
        documents = parse_multiple_files(file_path, extractor)
        if not documents:
            logger.warning(f"No content extracted from file: {file_path}")
            documents = []  # Ensure documents is at least an empty list

        self.update_state(state="PROGRESS", meta={"current": 70, "total": 100})
        job.progress = 70
        job.message = "Parse content from list of chunk document"
        db_session.add(job)
        db_session.flush()
        # Count tokens for all documents
        total_tokens = 0
        serializable_documents = []

        for idx, doc in enumerate(documents):
            doc_tokens = count_tokens_from_string(doc.text)
            total_tokens += doc_tokens
            chunk_uuid = str(uuid.uuid4())
            # Convert Document objects to serializable dictionaries
            serializable_documents.append(
                {
                    "id": chunk_uuid,
                    "text": clean_text_for_db(doc.text),
                    "metadata": doc.metadata,
                    "token_count": doc_tokens,
                }
            )
            
            doc_chunk = DocumentChunk(
                uuid=chunk_uuid,
                document_uuid=document.uuid,
                chunk_index=idx,
                text=clean_text_for_db(doc.text),
                extra_info=doc.metadata,
                token_count=doc_tokens,
            )
            db_session.add(doc_chunk)

        # Update document status
        document.status = DocumentStatus.PARSED
        db_session.add(document)
        
        # Update job status and task info
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.message = "Document parsed successfully"
        task_response = TaskResponse(
            status="success",
            task_id=self.request.id,
            task_name=self.request.task,
            task_retry=self.request.retries,
            task_info={
                "document_uuid": document.uuid,
                "file_path": file_path,
                "chunks": serializable_documents,
                "total_tokens": total_tokens,
                "chunk_count": len(documents),
            },
            message="Document parsed successfully",
        )
        job.task = task_response.model_dump()
        db_session.add(job)
        
        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100})
        
        # Only commit if we created the session
        if session is None:
            db_session.commit()
            
        return task_response.model_dump()
        
    except Exception as e:
        # Special handling for missing files
        logger.error(f"Error processing document: {file_path}")
        logger.error(traceback.format_exc())
        try:
            # Try to retry the task
            logger.info(f"Retrying task {self.request.id}, attempt {self.request.retries + 1}")
            self.retry(countdown=10 * (self.request.retries + 1), exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for task {self.request.id}")
            if 'job' in locals() and 'document' in locals():
                error_response = TaskResponse(
                        status="error",
                        task_id=self.request.id,
                        task_name=self.request.task,
                        task_retry=self.request.retries,
                        task_info={
                            "document_uuid": document.uuid,
                            "file_path": file_path,
                            "documents": [],
                            "total_tokens": 0,
                            "document_count": 0,
                        },
                        message=f"Error processing document: {file_path}, with max retries {self.request.retries}",
                    )
                document.status = DocumentStatus.FAILED
                job.status = JobStatus.FAILED
                job.message = f"Error processing document: {file_path}, with max retries {self.request.retries}"
                job.task = error_response.model_dump()
                
                db_session.add(job)
                db_session.add(document)
                
                if session is None:
                    db_session.commit()     
            return error_response.model_dump()
    finally:
        # Only close if we created the session
        if session is None and 'db_session' in locals():
            db_session.close()
