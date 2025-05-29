from dataclasses import dataclass
import enum
from typing import Any, Dict
from pydantic import BaseModel
import dotenv

dotenv.load_dotenv()
import os
from src.prompt import LLM_SYSTEM_PROMPT

ETL_FILE_EXTENSIONS = {
    "tradelane": [".jsonl", ".json", ".txt"],
    "port": [".jsonl", ".json", ".xlsx", ".csv"],
}
SUPPORTED_NORMAL_FILE_EXTENSIONS = [
    ".pdf",
    ".docx",
    ".txt",
    ".json",
    ".html",
    # ".pptx",
    ".csv",
    ".md",
    ".ipynb",
    ".mbox",
    ".xml",
    ".rtf",
]
SUPPORTED_SPECIAL_FILE_EXTENSIONS = [
    ".wav",
    ".mp3",
    ".m4a",
    ".mp4",
    ".jpg",
    ".jpeg",
    ".png",
    ".msg",
]
SUPPORTED_EXCEL_FILE_EXTENSIONS = [
    ".xlsx",
    ".xls",
]
ACCEPTED_MIME_MEDIA_TYPE_PREFIXES = [
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp4",
    "video/mp4",
    "image/jpeg",
    "image/png",
]


class LLMProviderType(enum.Enum):
    GOOGLE = "google"
    OPENAI = "openai"


class LLMConfig(BaseModel):
    api_key: str
    provider: LLMProviderType
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = "You are a helpful assistant."


class ReaderConfig(BaseModel):
    """Configuration for Reader"""

    num_threads: int = 4
    image_resolution_scale: float = 2.0
    enable_ocr: bool = True
    enable_tables: bool = True
    max_pages: int = 100
    max_file_size: int = 20971520  # 20MB
    supported_formats: list[str] = (
        SUPPORTED_NORMAL_FILE_EXTENSIONS
        + SUPPORTED_SPECIAL_FILE_EXTENSIONS
        + SUPPORTED_EXCEL_FILE_EXTENSIONS
    )  # For future extension


class Config:
    CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", "")
    OPENAI_CONFIG = LLMConfig(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        provider=LLMProviderType.OPENAI,
        model_id="models/gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=2048,
        system_prompt=LLM_SYSTEM_PROMPT,
    )

    GEMINI_CONFIG = LLMConfig(
        api_key=os.environ.get("GOOGLE_API_KEY", ""),
        provider=LLMProviderType.GOOGLE,
        model_id="models/gemini-2.0-flash",
        temperature=0.1,
        max_tokens=8192,
        system_prompt=LLM_SYSTEM_PROMPT,
    )
    READER_CONFIG = ReaderConfig()


global_config = Config()


def get_llm_config(llm_type: LLMProviderType) -> LLMConfig:
    if llm_type == LLMProviderType.OPENAI:
        return global_config.OPENAI_CONFIG
    elif llm_type == LLMProviderType.GOOGLE:
        return global_config.GEMINI_CONFIG
    else:
        raise ValueError(f"Unsupported LLM type: {llm_type}")
