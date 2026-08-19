from collections import Counter
from pathlib import Path

from delivery_common.domain import InvalidFile, PushingEntities, T
from pusher.core_functions.constants import PUSHING_ENTITIES_PATH
from pusher.core_functions.domain import InvalidFilesError
from pusher.logger import logger
from pusher.s3_client import get_s3_metadata_client

SUPPORTED_FILE_EXTENTIONS = {".txt", ".shp", ".zip", ".nc"}


# TODO: move these to the common validation


def file_exists(file_path: Path) -> bool:
    return file_path.exists()


def file_not_empty(file_path: Path) -> bool:
    return file_path.stat().st_size > 0


def file_type_supported(file_path: Path) -> bool:
    return file_path.suffix in SUPPORTED_FILE_EXTENTIONS


def duplicate_files(files: list[T]) -> list[T]:
    return [path for path, count in Counter(files).items() if count > 1]


def validate_delete_files(files: list[str]) -> None:
    invalid_files = [
        InvalidFile(local_path=Path(file_), reason="Duplicate file path.")
        for file_ in duplicate_files(files)
    ]
    if invalid_files:
        raise InvalidFilesError(
            invalid_files=invalid_files,
        )


def validate_upload_files(files: list[str], dataset_id: str, product_id: str, anchor: str | None) -> None:
    invalid_files = []
    for file_str in files:
        file = Path(file_str)
        if not file_exists(file):
            invalid_files.append(
                InvalidFile(local_path=file, reason="File path does not exist.")
            )
            continue
        if not file_not_empty(file):
            invalid_files.append(InvalidFile(local_path=file, reason="File is empty."))
            continue
        if anchor and anchor not in file.parts:
            invalid_files.append(
                InvalidFile(
                    local_path=file,
                    reason=f"Expected anchor ({anchor}) was not found in local path: {file.as_posix()}",
                )
            )
            continue
        if not anchor and (dataset_id in file.parts or product_id in file.parts):
            invalid_files.append(
                InvalidFile(
                    local_path=file,
                    reason=(
                        f"No anchor specified and product_id ({product_id}) or dataset_id ({dataset_id}) found in local path: {file.as_posix()}. "
                        "This will produce unexpected results in S3 MDS Suffixes."
                    )
                )
            )
            continue
        if not file_type_supported(file):
            # Just a warning for now
            logger.warning(
                "File extension is not supported. There might be some issues downstream. "
                f"Supported file extensions are: {SUPPORTED_FILE_EXTENTIONS}"
            )
            continue
    invalid_files += [
        InvalidFile(local_path=Path(file), reason="Duplicate file path.")
        for file in duplicate_files(files)
    ]
    if invalid_files:
        raise InvalidFilesError(
            invalid_files=invalid_files,
        )


def fetch_pushing_entities():
    metadata_s3_client = get_s3_metadata_client()
    pushing_entities_raw = metadata_s3_client.get_file_stream(
        path_to_file=PUSHING_ENTITIES_PATH
    )
    return PushingEntities.from_stream(pushing_entities_raw)
