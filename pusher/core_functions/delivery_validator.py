from collections import Counter
from pathlib import Path

from delivery_common.domain import (
    InvalidFile,
    PushingEntities,
    T,
)
from pusher.core_functions.constants import PUSHING_ENTITIES_PATH
from pusher.logger import logger
from pusher.s3_client import get_s3_metadata_client

SUPPORTED_FILE_EXTENTIONS = {".txt", ".shp", ".zip", ".nc"}


def file_exists(file_path: Path) -> bool:
    return file_path.exists()


def file_not_empty(file_path: Path) -> bool:
    return file_path.stat().st_size > 0


def file_type_supported(file_path: Path) -> bool:
    return file_path.suffix in SUPPORTED_FILE_EXTENTIONS


def duplicate_files(files: list[T]) -> list[T]:
    return [path for path, count in Counter(files).items() if count > 1]


def validate_delete_files(files: list[str]) -> None:
    pass


def validate_upload_files(files: list[Path]) -> None:
    invalid_files = []
    for file in files:
        if not file_exists(file):
            invalid_files.append(
                InvalidFile(local_path=file, reason="File path does not exist.")
            )
            continue
        if not file_not_empty(file):
            invalid_files.append(InvalidFile(local_path=file, reason="File is empty."))
            continue
        if not file_type_supported(file):
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

    for invalid_file in invalid_files:
        logger.error(f"Invalid file: {invalid_file}")
    if invalid_files:
        raise ValueError(
            f"Found {len(invalid_files)} invalid files. See logs for details."
        )


def fetch_pushing_entities():
    metadata_s3_client = get_s3_metadata_client()
    pushing_entities_raw = metadata_s3_client.get_file_stream(
        path_to_file=PUSHING_ENTITIES_PATH
    )
    return PushingEntities.from_stream(pushing_entities_raw)
