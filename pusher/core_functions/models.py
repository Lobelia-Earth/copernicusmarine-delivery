from typing import Literal

from pydantic import BaseModel, Field


class ManifestFile(BaseModel):
    #: Path to the file in the destination storage (e.g., S3 path).
    s3_path: str
    #: Estimation of the size of the file in MB.
    file_size: int | None
    #: checksum of the file to be uploaded.
    checksum: str


class Operation(BaseModel):
    operation: Literal["upload", "delete"]
    files: list[ManifestFile]


class Manifest(BaseModel):
    #: Unique identifier for the manifest. Contains a date that is not in UTC.
    manifest_id: str
    pushing_entity_id: str
    product_id: str
    dataset_id: str
    operations: list[Operation]

    #: ISO 8601 formatted timestamp in UTC
    creation_time: str


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


class ResponseUpload(BaseModel):
    """Metadata returned when using :func:`~pusher.upload`"""

    #: Successful uploaded files
    files: list[S3File] = Field(default_factory=list)
    #: List of files that failed to be uploaded.
    files_errored: list[str] = Field(default_factory=list)
    #: Manifest of such upload
    manifest: Manifest | None = None
    #: Any error that may prematurely stop the upload.
    error: str | None = None
