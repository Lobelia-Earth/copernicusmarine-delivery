from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, NewType

import yaml
from pydantic import BaseModel, Field

S3Path = NewType("S3Path", str)


class Product(BaseModel):
    product_id: str = Field(..., alias="name")
    datasets: list[str]


class PushingEntity(BaseModel):
    name: str
    products: list[Product]


class InvalidDeliveryIds(BaseModel):
    reason: str


class PushingEntities(BaseModel):
    pushing_entities: list[PushingEntity] = Field(..., alias="pushing-entities")

    @classmethod
    def from_stream(cls, bytes: bytes) -> "PushingEntities":
        data = yaml.safe_load(bytes)
        return cls(**data)

    @classmethod
    def from_file(cls, path: Path) -> "PushingEntities":
        if not path.is_file():
            raise FileNotFoundError(
                f"Could not open file in given path: {path.as_posix()}"
            )
        with open(path) as input_config_file:
            data = yaml.safe_load(input_config_file)
        return cls(**data)


class ManifestFile(BaseModel):
    #: Path to the file in the destination storage (e.g., S3 path).
    s3_path: S3Path
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
    operation: Literal["upload", "delete"]
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


@dataclass
class RequestUpload:
    files: list[S3File]
    operation_type: Literal["upload"] = field(default="upload", init=False)


@dataclass
class RequestDelete:
    files: list[S3Path]
    operation_type: Literal["delete"] = field(default="delete", init=False)


class ErrorResponseFile(BaseModel):
    """Generic class for any invalid or errored file"""

    path: Path
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


class InvalidFile(ErrorResponseFile): ...


class ErrorFile(ErrorResponseFile): ...


class ValidateResult(BaseModel):
    files_valid: list[Path]
    files_invalid: list[InvalidFile]


class PutFilesResult(BaseModel):
    successful_files: list[S3File] = Field(default_factory=list)
    errored_files: list[ErrorFile] = Field(default_factory=list)


class BaseResponse(BaseModel):
    #: Transaction ID.
    transaction_id: str | None = None
    #: Manifest of such upload
    delivery: Manifest | None = None
    #: Any error that may prematurely stop the delivery.
    fatal_error: str | None = None


class ResponseUpload(BaseResponse):
    """Metadata returned when using :func:`~pusher.upload`"""

    #: Successful uploaded file names
    files_uploaded: list[str] = Field(default_factory=list)
    # Potential user errors (user must fix)
    files_invalid: list[InvalidFile] = Field(default_factory=list)
    # Potential I/O errors, might be on the user side, not necessarily user fault
    files_failed: list[ErrorFile] = Field(default_factory=list)


class ResponseDelete(BaseResponse):
    """Metadata returned when using :func:`~pusher.delete`"""
