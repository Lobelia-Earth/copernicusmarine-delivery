from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from delivery_common.domain import (
    ErrorResponseFile,
    OperationNames,
    S3Path,
)
from pusher.logger import logger


class S3File(BaseModel):
    local_path: Path
    s3_path: S3Path
    e_tag: str
    upload_time: float


class ErrorFile(ErrorResponseFile): ...


class PutFilesResult(BaseModel):
    successful_files: list[S3File] = Field(default_factory=list)
    errored_files: list[ErrorFile] = Field(default_factory=list)


class BaseResponse(BaseModel):
    #: Delivery ID.
    delivery_id: str | None = None
    #: Any error that may prematurely stop the delivery.
    fatal_error: str | None = None


class ResponseUpload(BaseResponse):
    """Metadata returned when using :func:`~pusher.upload`"""

    #: Successful uploaded file names
    files_uploaded: list[Path] = Field(default_factory=list)
    #: Potential I/O errors, might be on the user side, not necessarily user fault
    files_failed: list[ErrorFile] = Field(default_factory=list)

    @field_validator("files_uploaded")
    @classmethod
    def sort_lists(cls, v: list) -> list:
        return sorted(v)

    # function to initialise the response
    @classmethod
    def create(
        cls,
        delivery_id: str,
        result_upload: PutFilesResult,
    ) -> "ResponseUpload":
        return cls(
            delivery_id=delivery_id,
            files_uploaded=[
                file_.local_path for file_ in result_upload.successful_files
            ],
            files_failed=result_upload.errored_files,
        )


class ResponseDelete(BaseResponse):
    """Metadata returned when using :func:`~pusher.delete`"""

    @classmethod
    def create_from_fatal_error(cls, fatal_error: str) -> "ResponseDelete":
        return cls(fatal_error=fatal_error)

    @classmethod
    def create(
        cls,
        delivery_id: str,
    ) -> "ResponseDelete":
        return cls(
            delivery_id=delivery_id,
        )


class ResponseDelivery(BaseResponse):
    """Metadata returned when using :func:`~pusher.delivery`"""

    #: List of responses for each operation in the delivery.
    operations_responses: list[ResponseUpload | ResponseDelete] = Field(
        default_factory=list
    )

    @classmethod
    def create(
        cls,
        delivery_id: str,
        operations_responses: list[ResponseUpload | ResponseDelete],
    ) -> "ResponseDelivery":
        return cls(
            delivery_id=delivery_id,
            operations_responses=operations_responses,
        )


class BaseOperation(BaseModel):
    operation: OperationNames
    files: list[str]

    def add(self, file: str) -> None:
        self.files.append(file)


class DeliveryFile(BaseModel):
    delivery: list[BaseOperation]


######
# Exceptions
######


class UploadError(Exception):
    """
    Raised when an error occurs during the upload process.
    Will list the files and their errors that failed to upload.
    """

    def __init__(self, error_files: list[ErrorFile]):
        for file in error_files:
            logger.error(f"Invalid file: {file}")
        super().__init__(
            f"All uploads failed. Errored files: {[file_.local_path for file_ in error_files]}"
        )


class NoIngestionBucketError(Exception):
    """
    Raised when the ingestion bucket is not found.
    """

    def __init__(self, pushing_entity_id: str):
        super().__init__(
            f"No ingestion bucket found for pushing entity: {pushing_entity_id} "
            f"Please contact User Support."
        )
