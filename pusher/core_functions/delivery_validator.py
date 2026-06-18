from pathlib import Path

from cloudpathlib import S3Path

from pusher.core_functions.models import InvalidFile, ValidateResult
from pusher.logger import logger

SUPPORTED_FILE_EXTENTIONS = {".txt", ".shp", ".zip", ".nc"}


## The below are upload requirements
def file_exists(file_path: Path | S3Path) -> bool:
    return file_path.exists()


def file_not_empty(file_path: Path | S3Path) -> bool:
    return file_path.stat().st_size > 0


def file_type_supported(file_path: Path | S3Path) -> bool:
    return file_path.suffix in SUPPORTED_FILE_EXTENTIONS


def validate_upload_file_requirements(files: list[Path | S3Path]) -> ValidateResult:
    valid_files = []
    invalid_files = []
    for file in files:
        if not file_exists(file):
            invalid_files.append(
                InvalidFile(path=file, reason="File path does not exist.")
            )
            continue
        if not file_not_empty(file):
            invalid_files.append(InvalidFile(path=file, reason="File is empty."))
            continue
        if not file_type_supported(file):
            # Just a warning for now
            logger.warning(
                "File extension is not supported. There might be some issues downstream. "
                f"Supported file extensions are: {SUPPORTED_FILE_EXTENTIONS}"
            )
            # invalid_files.append(
            #     InvalidFile(
            #         path=file,
            #         reason=f"File extension not supported. Supported extensions are: {SUPPORTED_FILE_EXTENTIONS}",
            #     )
            # )
            # continue
        valid_files.append(file)
    return ValidateResult(files_valid=valid_files, files_invalid=invalid_files)
