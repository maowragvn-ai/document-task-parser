# src/services/base.py
from abc import abstractmethod
from sqlmodel import Session, select
from src.db import get_session
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any, Union
from fastapi import HTTPException, status
from src.logger import get_formatted_logger
T = TypeVar('T')

class BaseService(Generic[T]):
    """
    Generic base service for database operations
    """
    def __init__(self, model: Type[T], session: Optional[Session] = None):
        self.model = model
        self.session = session or get_session()
        self.logger = get_formatted_logger(__name__)
        self.logger.debug(f"BaseService initialized for model: {model.__name__}")
        # self.logger.debug(f"Model attributes: {model.__table__.columns.keys()}")
    @abstractmethod 
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        try:
            statement = select(self.model).offset(skip).limit(limit)
            results = self.session.exec(statement).all()
            return results
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error fetching all {self.model.__name__} records: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error"
            )
    @abstractmethod 
    async def get_by_uuid(self, uuid: str) -> Optional[T]:
        statement = select(self.model).where(self.model.uuid == uuid)
        result = self.session.exec(statement).first()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} with id {uuid} not found"
            )
        return result
    @abstractmethod 
    async def create(self, obj_data: Dict[str, Any]) -> T:
        obj = self.model(**obj_data)
        try:
            self.session.add(obj)
            self.session.commit()
            self.session.refresh(obj)
            return obj
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error creating {self.model.__name__} record: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error"
            )
    @abstractmethod 
    async def update(self, uuid: str, obj_data: Dict[str, Any]) -> T:
        try:
            statement = select(self.model).where(self.model.uuid == uuid)
            result = self.session.exec(statement).first()
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.model.__name__} with id {uuid} not found"
                )
            
            for key, value in obj_data.items():
                setattr(result, key, value)
            
                
            self.session.add(result)
            self.session.commit()
            self.session.refresh(result)
            return result
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error updating {self.model.__name__} record: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error"
            )
    @abstractmethod 
    async def delete(self, uuid: str) -> Dict[str, bool]:
        try:
            statement = select(self.model).where(self.model.uuid == uuid)
            result = self.session.exec(statement).first()
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.model.__name__} with id {uuid} not found"
                )
            
            self.session.delete(result)
            self.session.commit()
            return {"success": True}
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error deleting {self.model.__name__} record: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error"
            )