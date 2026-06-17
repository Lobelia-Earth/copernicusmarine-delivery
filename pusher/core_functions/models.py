from typing import Literal

from pydantic import BaseModel, Field


class ManifestFile(BaseModel):
    #: Path to the file in the destination storage (e.g., S3 path).
    s3_path: str
    #: Estimation of the size of the file in MB.
    file_size: int | None
    #: checksum of the file to be uploaded.
    checksum: str
    #: Status of the file in the OPDV system
    #: todo: The file has not been picked up yet by the OPDV system.
    #: validated: The file has been validated by the OPDV system. Will be processed.
    #: pushed or deleted: The file has been processed following the operation.
    #: backed_up: The file has been backed up.
    #: error: The file failed to be uploaded.
    status: Literal["todo", "validated", "pushed", "deleted", "backed_up", "error"] = (
        "todo"
    )
    #: last updated status timestamp in ISO 8601 format (UTC)
    status_timestamp: str | None = None
    #: Optional error message if the file failed to be uploaded.
    error: str | None = None


class Operation(BaseModel):
    #: Operation type
    #: upload: The operation is to upload new files to MDS storage.
    #: delete: The operation is to delete files from MDS storage.
    operation: Literal["upload", "delete"]
    #: status of the operation in the OPDV system
    #: todo: The operation has not been picked up yet by the OPDV system.
    #: in_progress: The operation is being processed by the OPDV system.
    #: done: The operation has been processed successfully by the OPDV system.
    #: error: The operation failed to be processed by the OPDV system.
    status: Literal["todo", "in_progress", "done", "error"] = "todo"
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


class S3FileObj(BaseModel):
    s3_path: str
    e_tag: str


class S3File(S3FileObj):
    local_path: str


class ErrorPutFileObj(BaseModel):
    error: str


class ErrorPutFile(ErrorPutFileObj):
    local_path: str


class PutFilesResult(BaseModel):
    success: list[S3File] = Field(default_factory=list)
    error: list[ErrorPutFile] = Field(default_factory=list)


# TODO: document. Also, get rid of the manifest vocabulary?
class ResponseUpload(BaseModel):
    """Metadata returned when using :func:`~pusher.upload`"""

    #: Successful uploaded file names
    files: list[str] = Field(default_factory=list)
    #: List of files that failed to be uploaded.
    files_errored: list[str] = Field(default_factory=list)
    #: Transaction ID.
    transaction_id: str | None = None
    #: Manifest of such upload
    manifest: Manifest | None = None
    #: Any error that may prematurely stop the upload.
    error: str | None = None
