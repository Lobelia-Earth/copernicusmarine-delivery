from pathlib import Path
from typing import Literal, NewType

from pydantic import BaseModel, Field

# TODO: Be sure we use this S3 path where we should
# i.e only when sending to S3. All the rest, we want a relative path
# that is used to find the file locally, in the manifest, and
# as the suffix of the S3 key.
S3Path = NewType("S3Path", str)
OperationNames = Literal["upload", "delete"]


class ManifestFile(BaseModel):
    #: Path to the file in the destination storage (e.g., S3 path).
    file_path: Path
    #: Estimation of the size of the file in MB.
    file_size: int | None
    #: checksum of the file to be uploaded.
    checksum: str | None
    #: Status of the file in the OPDV system
    #: todo: The file has not been picked up yet by the OPDV system.
    #: validated: The file has been validated by the OPDV system. Will be processed.
    #: pushed or deleted: The file has been processed following the operation.
    #: backed_up: The file has been backed up.
    #: error: The file failed to be uploaded.
    status: Literal[
        "todo", "validated", "published", "deleted", "backed_up", "error"
    ] = "todo"
    #: last updated status timestamp in ISO 8601 format (UTC)
    status_timestamp: str | None = None
    #: Optional error message if the file failed to be uploaded.
    error: str | None = None


class Operation(BaseModel):
    #: Operation type
    #: upload: The operation is to upload new files to MDS storage.
    #: delete: The operation is to delete files from MDS storage.
    operation: OperationNames
    #: status of the operation in the OPDV system
    #: todo: The operation has not been picked up yet by the OPDV system.
    #: in_progress: The operation is being processed by the OPDV system.
    #: done: The operation has been processed successfully by the OPDV system.
    #: partial_error: The operation has been partially processed by the OPDV system. Some files may have failed.
    #: error: The operation failed to be processed by the OPDV system.
    status: Literal["todo", "in_progress", "done", "partial_error", "error"] = "todo"
    #: last updated status timestamp in ISO 8601 format (UTC)
    status_timestamp: str | None = None
    #: Optional error message if the operation failed to be processed by the OPDV system.
    error: str | None = None
    #: List of files associated with the operation.
    files: list[ManifestFile]


class Manifest(BaseModel):
    #: Unique identifier for the manifest. Contains a date that is not in UTC.
    manifest_id: str
    #: Unique identifier for the pushing entity.
    pushing_entity_id: str
    #: Unique identifier for the product.
    product_id: str
    #: Unique identifier for the dataset.
    dataset_id: str
    #: List of operations associated with the manifest.
    #: These operations will be done sequentially in the order they are listed.
    operations: list[Operation]

    #: ISO 8601 formatted timestamp in UTC
    creation_time: str
    #: status of the manifest in the OPDV system.
    #: todo: The manifest has not been picked up yet by the OPDV system.
    #: in_progress: The manifest is being processed by the OPDV system.
    #: done: The manifest has been processed successfully by the OPDV system.
    #: partial_error: The manifest has been partially processed by the OPDV system. Some files or operations may have failed.
    #: error: The manifest failed to be processed by the OPDV system.
    status: Literal["todo", "in_progress", "done", "partial_error", "error"] = "todo"
    #: last updated status timestamp in ISO 8601 format (UTC)
    status_timestamp: str | None = None
    #: Optional error message if the manifest failed to be processed by the OPDV system.
    error: str | None = None


class S3File(BaseModel):
    local_path: Path
    s3_path: S3Path
    e_tag: str


class ErrorResponseFile(BaseModel):
    """Generic class for any invalid or errored file"""

    path: Path
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


class InvalidFile(ErrorResponseFile): ...


class ErrorFile(ErrorResponseFile): ...


class UploadValidationResult(BaseModel):
    files_valid: list[Path]
    files_invalid: list[InvalidFile]


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
    files_uploaded: list[str] = Field(default_factory=list)
    #: Potential user errors (user must fix).
    #: TODO: I think validation errors should be fatal contrary to upload errors.
    files_invalid: list[InvalidFile] = Field(default_factory=list)
    #: Potential I/O errors, might be on the user side, not necessarily user fault
    files_failed: list[ErrorFile] = Field(default_factory=list)

    # function to initialise the response
    @classmethod
    def create(
        cls,
        delivery_id: str,
        result_validation: UploadValidationResult,
        result_upload: PutFilesResult,
    ) -> "ResponseUpload":
        return cls(
            delivery_id=delivery_id,
            files_uploaded=[
                file_.local_path.name for file_ in result_upload.successful_files
            ],
            files_invalid=result_validation.files_invalid,
            files_failed=result_upload.errored_files,
        )

    @classmethod
    def create_from_fatal_error(cls, fatal_error: str) -> "ResponseUpload":
        return cls(fatal_error=fatal_error)


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

    @classmethod
    def create_from_fatal_error(cls, fatal_error: str) -> "ResponseDelivery":
        return cls(fatal_error=fatal_error)
