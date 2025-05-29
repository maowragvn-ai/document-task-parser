# This file contains utility functions for the readers module.
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from datetime import datetime
from llama_index.core import Document
import ast
from tqdm import tqdm
from src.config import SUPPORTED_NORMAL_FILE_EXTENSIONS, SUPPORTED_SPECIAL_FILE_EXTENSIONS, SUPPORTED_EXCEL_FILE_EXTENSIONS
from src.logger import get_formatted_logger
from .markitdown import DocumentConverterResult

load_dotenv()
logger = get_formatted_logger(__file__)


def check_valid_extenstion(file_path: str | Path) -> bool:
    """
    Check if the file extension is supported

    Args:
        file_path (str | Path): File path to check

    Returns:
        bool: True if the file extension is supported, False otherwise.
    """
    allowed_extensions = SUPPORTED_NORMAL_FILE_EXTENSIONS + SUPPORTED_SPECIAL_FILE_EXTENSIONS + SUPPORTED_EXCEL_FILE_EXTENSIONS
    return Path(file_path).suffix in allowed_extensions


def get_files_from_folder_or_file_paths(files_or_folders: list[str]) -> list[str]:
    """
    Get all files from the list of file paths or folders

    Args:
        files_or_folders (list[str]): List of file paths or folders

    Returns:
        list[str]: List of valid file paths.
    """
    files = []

    for file_or_folder in files_or_folders:
        if Path(file_or_folder).is_dir():
            files.extend(
                [
                    str(file_path.resolve())
                    for file_path in Path(file_or_folder).rglob("*")
                    if check_valid_extenstion(file_path)
                ]
            )

        else:
            if check_valid_extenstion(file_or_folder):
                files.append(str(Path(file_or_folder).resolve()))
            else:
                logger.warning(f"Invalid file: {file_or_folder}")

    return files

def parse_multiple_files(
    files_or_folder: list[str] | str, extractor: dict[str, Any],
    show_progress: bool = True
) -> list[Document]:
    """
    Read the content of multiple files.

    Args:
        files_or_folder (list[str] | str): List of file paths or folder paths containing files.
        extractor (dict[str, Any]): Extractor to extract content from files.
    Returns:
        list[Document]: List of documents from all files.
    """
    assert extractor, "Extractor is required."

    if isinstance(files_or_folder, str):
        files_or_folder = [files_or_folder]

    valid_files = get_files_from_folder_or_file_paths(files_or_folder)

    if len(valid_files) == 0:
        raise ValueError("No valid files found.")

    logger.info(f"Valid files: {valid_files}")

    documents: list[Document] = []

    files_to_process = tqdm(valid_files, desc="Starting parse files", unit="file") if show_progress else valid_files

    for file in files_to_process:
        file_path_obj = Path(file)
        file_suffix = file_path_obj.suffix.lower()
        file_extractor = extractor[file_suffix]

        if file_suffix in SUPPORTED_SPECIAL_FILE_EXTENSIONS:
            result: DocumentConverterResult = file_extractor.convert(file)
            metadata={
                "title": result.title,
                "created_at": datetime.now().isoformat(),
                "file_name": file_path_obj.name,
            }
            if result.metadata and result.metadata["image_base64"]:
                metadata["image_origin"] = result.metadata["image_base64"]
                
            documents.append(
                Document(
                    text=result.text_content,
                    metadata=metadata,
                )
            )
        elif (file_suffix in SUPPORTED_EXCEL_FILE_EXTENSIONS):
            result: DocumentConverterResult = file_extractor.convert(file)
            metadata={
                "title": result.title,
                "created_at": datetime.now().isoformat(),
                "file_name": file_path_obj.name,
            }
            if result.metadata and result.metadata["image_base64"]:
                metadata["image_origin"] = result.metadata["image_base64"]
            try:
                sheet_excel_texts: list = ast.literal_eval(result.text_content)
                for idx, sheet_excel_text in enumerate(sheet_excel_texts):
                    sheet_metadata = metadata.copy()
                    sheet_metadata["sheet_index"] = idx
                    documents.append(
                        Document(
                            text=sheet_excel_text,
                            metadata=sheet_metadata,
                        )
                    )
            except:
                documents.append(
                    Document(
                        text=result.text_content,
                        metadata=metadata,
                    )
                )
        else:
            results = file_extractor.load_data(file_path_obj)
            documents.extend(results)

    logger.info(f"Parse files successfully with {files_or_folder} split to {len(documents)} documents")
    return documents