from collections import Counter
from pathlib import Path

from copernicusmarine_delivery.core_functions.domain import (
    APILimits,
    InvalidDeliverySizeError,
    InvalidFilesError,
    ToUploadOperation,
)
from copernicusmarine_delivery.core_functions.utils import local_path_to_key_suffix
from copernicusmarine_delivery.logger import logger
from delivery_common.domain import (
    FORBIDDEN_KEY_SUFFIX_PATTERNS,
    InvalidFile,
    T,
    raise_on_wrong_key_suffix,
)

SUPPORTED_FILE_EXTENTIONS = {".txt", ".shp", ".zip", ".nc"}


# TODO: move these to the common validation


def file_exists(file_path: Path) -> bool:
    return file_path.exists()


def file_not_empty(file_path: Path) -> bool:
    return file_path.stat().st_size > 0


def file_type_supported(file_path: Path) -> bool:
    return file_path.suffix in SUPPORTED_FILE_EXTENTIONS


def acceptable_key_suffix(file_path_str: str, anchor: str | None) -> bool:
    try:
        raise_on_wrong_key_suffix(local_path_to_key_suffix(file_path_str, anchor))
    except ValueError:
        return False
    return True


def duplicate_files(files: list[T]) -> list[T]:
    return [path for path, count in Counter(files).items() if count > 1]


def validate_delete_files(files: list[str]) -> None:
    invalid_files = [
        InvalidFile(local_path=Path(file_), reason="Duplicate file path.") for file_ in duplicate_files(files)
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
            invalid_files.append(InvalidFile(local_path=file, reason="File path does not exist."))
            continue
        if not file_not_empty(file):
            invalid_files.append(InvalidFile(local_path=file, reason="File is empty."))
            continue
        if anchor and anchor not in file.parts:
            invalid_files.append(
                InvalidFile(
                    local_path=file,
                    reason=f"Expected anchor ({anchor}) was not found in local path: {file}",
                )
            )
            continue
        if not anchor:
            if dataset_id in file.parts or product_id in file.parts:
                invalid_files.append(
                    InvalidFile(
                        local_path=file,
                        reason=(
                            f"No anchor specified and product_id ({product_id}) or dataset_id ({dataset_id}) found in local path: {file}. "
                            "This will most probably produce an invalid S3 MDS suffix. For specific cases, please contact User Support."
                        ),
                    )
                )
                continue
            if file.is_absolute():
                invalid_files.append(
                    InvalidFile(
                        local_path=file,
                        reason=(
                            f"Absolute paths are only allowed if an anchor is given: {file}"
                            "This will most probably produce an invalid S3 MDS suffix. For specific cases, please contact User Support."
                        ),
                    )
                )
                continue
            if not acceptable_key_suffix(str(file_str), anchor):
                invalid_files.append(
                    InvalidFile(
                        local_path=file,
                        reason=(
                            f"Key suffix derived from local path is not acceptable: {file}. Forbidden patterns are: {FORBIDDEN_KEY_SUFFIX_PATTERNS}"
                        ),
                    )
                )
        if not file_type_supported(file):
            # Just a warning for now
            logger.warning(
                "File extension is not supported. There might be some issues downstream. "
                f"Supported file extensions are: {SUPPORTED_FILE_EXTENTIONS}"
            )
            continue
    invalid_files += [
        InvalidFile(local_path=Path(file), reason="Duplicate file path.") for file in duplicate_files(files)
    ]
    if invalid_files:
        raise InvalidFilesError(
            invalid_files=invalid_files,
        )


def validate_delivery_sizes(api_limits: APILimits, to_upload_operations: list[ToUploadOperation]) -> None:
    number_of_files_in_delivery = 0
    delivery_size_in_gb = 0.0
    files_above_file_limit = []
    api_max_size_mb = api_limits.max_file_size_gb * 1024

    for operation in to_upload_operations:
        for file in operation.files:
            number_of_files_in_delivery += 1
            delivery_size_in_gb += file.file_size_mb / 1024
            if file.file_size_mb > api_max_size_mb:
                files_above_file_limit.append(file)

    if number_of_files_in_delivery > api_limits.max_number_of_files_per_delivery:
        raise InvalidDeliverySizeError(
            limit_raised="Maximum number of files exceeded",
            details=f"The number of files in delivery ({number_of_files_in_delivery}) exceeded the limit ({api_limits.max_number_of_files_per_delivery})",
        )
    if delivery_size_in_gb > api_limits.max_delivery_size_gb:
        raise InvalidDeliverySizeError(
            limit_raised="Maximum delivery size exceeded",
            details=f"The delivery size ({delivery_size_in_gb} GB) exceeded the limit ({api_limits.max_delivery_size_gb} GB)",
        )
    if files_above_file_limit:
        raise InvalidDeliverySizeError(
            limit_raised="Maximum file size exceeded",
            details=f"One or more files exceeded the maximum file size limit ({api_limits.max_file_size_gb} GB). Sizes are in MB: { ({file.local_path: file.file_size_mb for file in files_above_file_limit}) }",
        )
