# api/services/job_service.py
from typing import Any, Dict, Optional, List
from sqlmodel import Session, select
from datetime import datetime, timezone
from src.logger import get_formatted_logger
from src.db import JobStatus, JobType, Job

logger = get_formatted_logger(__name__)


class JobService:
    def __init__(self, session: Session):
        self.session = session

    async def create_job(
        self,
        job_uuid: str,
        message: str,
        progress: int = 0,
        file: str = None,
        type: JobType = JobType.PARSE,
        status: JobStatus = JobStatus.PENDING,
    ) -> Job:
        try:
            job = Job(
                uuid=job_uuid,
                type=type,
                status=status,
                progress=progress,
                message=message,
                file=file,
            )
            self.session.add(job)
            self.session.commit()
            self.session.refresh(job)
            return job
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating job: {str(e)}")
            raise e

    async def update_job(
        self,
        job_uuid: str,
        message: Optional[str] = None,
        progress: Optional[int] = None,
        status: Optional[JobStatus] = None,
        task: Optional[Dict[str, Any]] = {},
    ) -> Job:
        try:
            statement = select(Job).where(Job.uuid == job_uuid)
            result = self.session.exec(statement).first()
            if result:
                if status:
                    result.status = status
                if message:
                    result.message = message
                if progress is not None:
                    result.progress = progress
                if task:
                    result.task = task
                result.updated_at = datetime.now(timezone.utc)
                self.session.add(result)
                self.session.commit()
                self.session.refresh(result)
                return result
            logger.error(f"Error updating job: job not found for uuid: {job_uuid}")
            return None
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating job: {str(e)}")
            raise e

    async def get_job_by_uuid(self, job_uuid: str) -> Optional[Job]:
        try:
            return self.session.exec(select(Job).where(Job.uuid == job_uuid)).first()
        except Exception as e:
            logger.error(f"Error getting job: {str(e)}")
            raise e

    async def get_job_by_id(self, job_id: int) -> Optional[Job]:
        try:
            return self.session.exec(select(Job).where(Job.id == job_id)).first()
        except Exception as e:
            logger.error(f"Error getting job: {str(e)}")
            raise e

    async def get_jobs_by_type(self, job_type: JobType = JobType.PARSE) -> List[Job]:
        try:
            return self.session.exec(select(Job).where(Job.type == job_type)).all()
        except Exception as e:
            logger.error(f"Error listing jobs: {str(e)}")
            raise e
     
