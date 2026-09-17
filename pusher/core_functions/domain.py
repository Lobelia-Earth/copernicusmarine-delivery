from pathlib import Path
from typing import Literal, NewType

from pydantic import BaseModel, Field, field_validator

from delivery_common.domain import (
    DeleteFile,
    ErrorResponseFile,
    InvalidFile,
    OperationNames,
    PushingEntity,
)
from pusher.logger import logger

# Represents an S3 Path stripped of `data/delivery_id`
S3KeySuffix = NewType("S3KeySuffix", str)

S3Path = NewType("S3Path", str)


def get_s3_key_suffix(s3_path: S3Path) -> S3KeySuffix:
    return S3KeySuffix("/".join(s3_path.split("/")[2:]))


class FileToUpload(BaseModel):
    """Pre-upload file: checksum not known yet, only available once the upload completes.
    file_path is a local path, not S3 related yet."""

    file_size_mb: int
    local_path: str


class ToUploadOperation(BaseModel):
    """Pre-upload counterpart to UploadOperation: files not uploaded yet, so no checksum."""

    operation: OperationNames = Field(default=OperationNames.upload)
    files: list[FileToUpload] = Field(default_factory=list)
    anchor: str | None


class S3File(BaseModel):
    local_path: Path
    ingestion_system_s3_path: S3Path
    e_tag: str
    upload_start_time: str
    upload_end_time: str


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
    files_uploaded: list[tuple[Path, S3KeySuffix]] = Field(default_factory=list)
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
                (file.local_path, get_s3_key_suffix(file.ingestion_system_s3_path))
                for file in result_upload.successful_files
            ],
            files_failed=result_upload.errored_files,
        )


class ResponseDelete(BaseResponse):
    """Metadata returned when using :func:`~pusher.delete`"""

    files_to_delete: list[DeleteFile] = Field(default_factory=list)

    @classmethod
    def create_from_fatal_error(cls, fatal_error: str) -> "ResponseDelete":
        return cls(fatal_error=fatal_error)

    @classmethod
    def create(
        cls, delivery_id: str, files_to_delete: list[DeleteFile]
    ) -> "ResponseDelete":
        return cls(
            delivery_id=delivery_id,
            files_to_delete=files_to_delete,
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


class Upload(BaseOperation):
    operation: Literal[OperationNames.upload] = OperationNames.upload
    anchor: str | None = None


class Delete(BaseOperation):
    operation: Literal[OperationNames.delete] = OperationNames.delete


class DeliveryFile(BaseModel):
    delivery: list[Upload | Delete]


######
# Exceptions
######


class NoSuccessfulUploadsError(Exception):
    """
    Raised when an error occurs during the upload process.
    Will list the files and their errors that failed to upload.
    """

    def __init__(self, error_files: list[ErrorFile]):
        for file in error_files:
            logger.error(f"Invalid file: {file}")
        super().__init__(
            f"All uploads failed. Errored files: {[file.local_path for file in error_files]}"
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


class InvalidFilesError(Exception):
    """
    Raised when an error occurs during the validation of files.
    Will list the files and their errors that failed validation.
    """

    def __init__(self, invalid_files: list[InvalidFile]):
        for file in invalid_files:
            logger.error(f"Invalid file: {file}")
        super().__init__(
            f"Found {len(invalid_files)} invalid files. See logs for details."
        )


# This is a copy from what comes from the API.
# We do not need to, but it helps to type things.
class OIDCConfig(BaseModel):
    oidc_provider_url: str
    oidc_client_id: str
    scope: str = "openid"
    grant_type: str = "password"


class S3Config(BaseModel):
    endpoint_url: str


class GetConfigResponse(BaseModel):
    oidc_config: OIDCConfig


class GetPushingEntityConfigResponse(BaseModel):
    pushing_entity: PushingEntity
    s3_endpoint_url: str
