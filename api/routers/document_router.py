# api/routers/document_router.py
from fastapi import (
    APIRouter,
    Form,
    UploadFile,
    File,
    HTTPException,
    status,
    Depends,
    Path,
    Query,
)
from fastapi.responses import JSONResponse
from sqlmodel import Session
from dotenv import load_dotenv
from src.logger import get_formatted_logger
from src.config import global_config
from api.services.document_service import DocumentService
from src.db import get_session
from api.schemas.document_schema import DocumentResponse,DocumentCreate
from api.schemas.job_schema import JobResponse

load_dotenv()
logger = get_formatted_logger(__name__)
document_router = APIRouter(prefix="/document", tags=["document"])


def get_document_service(session: Session = Depends(get_session)):
    return DocumentService(session)


@document_router.post(
    "/upload/",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document",
    description="Upload a document and create a job for processing",
)
async def upload_document(
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Upload a document and create a job for processing

    - **file**: The file to upload (must be one of the supported formats)

    Returns:
        Document information and job ID
    """
    extension_allowed = global_config.READER_CONFIG.supported_formats

    if not extension_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No supported file formats configured",
        )

    # Check if filename exists
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename"
        )

    # Convert filename to lowercase for case-insensitive comparison
    filename_lower = file.filename.lower()

    # Check if file extension is supported
    if not any(filename_lower.endswith(ext.lower()) for ext in extension_allowed):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {', '.join(extension_allowed)} files allowed",
        )

    # Check if file size is within the allowed limit
    if file.size > global_config.READER_CONFIG.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds the allowed limit of {global_config.READER_CONFIG.max_file_size/1024/1024}MB",
        )
    try:
        result = await document_service.create_and_upload_document(file)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Document upload processing in background!",
                "uuid": result.uuid,
                "name": result.name,
                "source": result.source,
                "extension": result.extension,
                "extra_info": result.extra_info,
                "job_id": result.job_id,
                "status": result.status,
                "status": result.status,
            }
        )
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}",
        )


@document_router.post(
    "/parse/{document_uuid}",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Parse a document",
    description="Parse a document and extract its content",
)
async def parse_document(
    document_uuid: str = Path(..., description="UUID of the document to parse"),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Parse a document and extract its content

    - **document_uuid**: UUID of the document to parse

    Returns:
        Parsed document content and metadata
    """
    try:
        result = await document_service.parse_document(document_uuid)

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": "Document parse processing in background!",
                "uuid": result.uuid,
                "name": result.name,
                "source": result.source,
                "extension": result.extension,
                "extra_info": result.extra_info,
                "job_id": result.job_id,
                "status": result.status,
                "status": result.status,
            },
        )
    except HTTPException as he:
        # Re-raise HTTP exceptions with their original status code
        raise he
    except Exception as e:
        logger.error(f"Error parsing document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing document: {str(e)}",
        )
@document_router.get("/job/status/{job_uuid}",
                    response_model=JobResponse,
                    summary="Get document",
                    description="Get a document by UUID")
async def get_document_status(
    job_uuid: str = Path(..., description="UUID of the job to retrieve"),
    document_service: DocumentService = Depends(get_document_service)
):
    """Get a document by UUID"""
    try:
        job = await document_service.get_document_status(job_uuid)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "file": job.file,
                "progress": job.progress,
                "task": job.task,
                "message": job.message,
                "status": job.status,
                "uuid": job.uuid,
            }
        )
    except HTTPException as he:
        # Re-raise HTTP exceptions with their original status code
        raise he
    except Exception as e:
        logger.error(f"Error getting document status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting document status: {str(e)}"
        )

# @document_router.get("/get-pagi/",
#                     summary="List documents",
#                     description="Get a list of all documents")
# async def list_documents(
#     status: Optional[str] = Query(None, description="Filter by document status"),
#     limit: int = Query(10, description="Number of documents to return"),
#     offset: int = Query(0, description="Number of documents to skip"),
#     document_service: DocumentService = Depends(get_document_service)
# ):
#     """List all documents with optional filtering"""
#     try:
#         # This is a placeholder - you'll need to implement list_documents in DocumentService
#         # documents = await document_service.list_documents(status=status, limit=limit, offset=offset)

#         # For now, return a placeholder response
#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={
#                 "message": "List documents endpoint - Not yet implemented",
#                 "documents": []
#             }
#         )
#     except Exception as e:
#         logger.error(f"Error listing documents: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error listing documents: {str(e)}"
#         )

# @document_router.get("/get/{document_uuid}",
#                     summary="Get document",
#                     description="Get a document by UUID")
# async def get_document(
#     document_uuid: str = Path(..., description="UUID of the document to retrieve"),
#     document_service: DocumentService = Depends(get_document_service)
# ):
#     """Get a document by UUID"""
#     try:
#         document = await document_service.get_document(document_uuid)

#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content=document.model_dump()
#         )
#     except HTTPException as he:
#         # Re-raise HTTP exceptions with their original status code
#         raise he
#     except Exception as e:
#         logger.error(f"Error getting document: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error getting document: {str(e)}"
#         )
