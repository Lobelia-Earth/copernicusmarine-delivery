from pathlib import Path
from typing import Literal

from cloudpathlib import S3Path
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
    local_path: Path


class ErrorResponseFile(BaseModel):
    """Generic class for any invalid or errored file"""

    path: Path | S3Path
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


class InvalidFile(ErrorResponseFile): ...


class ErrorFile(ErrorResponseFile): ...


class ValidateResult(BaseModel):
    files_valid: list[Path | S3Path]
    files_invalid: list[InvalidFile]


class PutFilesResult(BaseModel):
    successful_files: list[S3File] = Field(default_factory=list)
    errored_files: list[ErrorFile] = Field(default_factory=list)


class ResponseUpload(BaseModel):
    """Metadata returned when using :func:`~pusher.upload`"""

    files_uploaded: list[str] = Field(default_factory=list)
    # Potential user errors (user must fix)
    files_invalid: list[InvalidFile] = Field(default_factory=list)
    # Potential I/O errors, might be on user side, not necessarily user failt
    files_failed: list[ErrorFile] = Field(default_factory=list)
    #: Manifest of such upload
    manifest: Manifest | None = None
    #: Any error that may prematurely stop the upload.
    fatal_error: str | None = None
