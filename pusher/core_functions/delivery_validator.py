from pathlib import Path

from delivery_common.domain import PushingEntities
from pusher.core_functions.constants import PUSHING_ENTITIES_PATH
from pusher.core_functions.models import (
    InvalidFile,
    UploadValidationResult,
)
from pusher.logger import logger
from pusher.s3_client import get_s3_metadata_client

SUPPORTED_FILE_EXTENTIONS = {".txt", ".shp", ".zip", ".nc"}


def file_exists(file_path: Path) -> bool:
    return file_path.exists()


def file_not_empty(file_path: Path) -> bool:
    return file_path.stat().st_size > 0


def file_type_supported(file_path: Path) -> bool:
    return file_path.suffix in SUPPORTED_FILE_EXTENTIONS


def upload_files_validation(files: list[Path]) -> UploadValidationResult:
    valid_files = []
    invalid_files = []
    for file_ in files:
        if not file_exists(file_):
            invalid_files.append(
                InvalidFile(local_path=file_, reason="File path does not exist.")
            )
            continue
        if not file_not_empty(file_):
            invalid_files.append(InvalidFile(local_path=file_, reason="File is empty."))
            continue
        if not file_type_supported(file_):
            # Just a warning for now
            logger.warning(
                "File extension is not supported. There might be some issues downstream. "
                f"Supported file extensions are: {SUPPORTED_FILE_EXTENTIONS}"
            )
            # invalid_files.append(
            #     InvalidFile(
            #         path=file_,
            #         reason=f"File extension not supported. Supported extensions are: {SUPPORTED_FILE_EXTENTIONS}",
            #     )
            # )
            # continue
        valid_files.append(file_)
    return UploadValidationResult(files_valid=valid_files, files_invalid=invalid_files)


def fetch_pushing_entities():
    metadata_s3_client = get_s3_metadata_client()
    pushing_entities_raw = metadata_s3_client.get_file_stream(
        path_to_file=PUSHING_ENTITIES_PATH
    )
    return PushingEntities.from_stream(pushing_entities_raw)
