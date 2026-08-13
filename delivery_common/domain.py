import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, TypeVar, Union

import yaml
from pydantic import BaseModel, Discriminator, Field, Tag, field_validator

##############
# Utils
##############


def now_in_utc_isoformat() -> str:
    """Returns the current time in UTC in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


#############


T = TypeVar("T")


class Product(BaseModel):
    product_id: str = Field(..., alias="name")
    datasets: list[str]


class PushingEntity(BaseModel):
    name: str
    bucket: str
    products: list[Product]


class InvalidDeliveryIdsError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class PushingEntities(BaseModel):
    """
    TODO: create an endpoint on OPDV side to get this information.
    """

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


# DeliveryStatus = Literal["pending", "validated", "completed", "failed"]
# OperationNames = Literal["upload", "delete"]


class DeliveryStatus(str, Enum):
    pending = "pending"
    validated = "validated"
    completed = "completed"
    failed = "failed"


class OperationNames(str, Enum):
    upload = "upload"
    delete = "delete"


class DeliveryFile(BaseModel):
    #: File path. Only the part specific to the dataset and defined by the pushing entity.
    #: Example: "subfolder/file.nc" or "file.nc"
    #: In the case of an upload, it will be uploaded to the Marine datastore as "/{product_id}/{dataset_id}/{key_suffix}".
    #: Similarly for a delete, the file will be deleted from the Marine datastore at "/{product_id}/{dataset_id}/{key_suffix}".
    key_suffix: str

    @field_validator("key_suffix")
    @classmethod
    def ensure_relative_path(cls, v: str) -> str:
        """
        From Claude. Not sure it is a good idea but I will leave it there as a TODO.

        We need to make sure we retrieve and save the right path in the delivery.
        The right path is the relative path that we will apply in S3. Without product/dataset prefix.
        Examples:
        - datasetID/filename.txt => wrong s3 path
        - subfolder/filename.txt => good path
        - /absolute/path/to/filename.txt => wrong path, should be relative to the current working directory
        - onlylocalfolder/filename.txt => wrong because we don't want it in s3

        UX wise: All the above is our problem and our convention ie we need to send this to the OPDV.
        But we can imagine various interfaces that helps the user understand this.
        Examples:
        - we ask for s3 folder structure
        - we force the user to have locally the same structure as s3 and we just take the relative path to the current working directory (as done now)
        - we ask for the full path and we strip the product/dataset prefix if it exists so we use the datasetID as anchor.
        - etc
        """
        if os.path.isabs(v):
            return os.path.relpath(v).replace(
                "../", ""
            )  # disgusting but good enough for now
        return v

    #: Optional error message if the file failed.
    error_message: str | None = None


class UploadFile(DeliveryFile):
    file_size_mb: int
    #: checksum of uploaded file.
    checksum: str
    #: Upload start time from the users machine to the OPDV system in seconds.
    upload_start_time: str | None
    #: Upload end time from the users machine to the OPDV system in seconds.
    upload_end_time: str | None


class FileToUpload(DeliveryFile):
    """Pre-upload file: checksum not known yet, only available once the upload completes."""

    file_size_mb: int


class DeleteFile(DeliveryFile):
    pass


class UploadOperation(BaseModel):
    operation: OperationNames = Field(default=OperationNames.upload)
    files: list[UploadFile] = Field(default_factory=list)

    def total_size(self) -> int:
        """Returns the total size of all files in MB."""
        return sum(file.file_size_mb or 0 for file in self.files)


class ToUploadOperation(BaseModel):
    """Pre-upload counterpart to UploadOperation: files not uploaded yet, so no checksum."""

    operation: OperationNames = Field(default=OperationNames.upload)
    files: list[FileToUpload] = Field(default_factory=list)


class DeleteOperation(BaseModel):
    operation: OperationNames = Field(default=OperationNames.delete)
    files: list[DeleteFile] = Field(default_factory=list)


def operation_discriminator(value: Any) -> str:
    """
    Discriminator function for the Operation union type.
    Determines the operation type based on the "operation" field in the input dictionary.
    """
    if isinstance(value, dict):
        if "operation" not in value:
            raise ValueError("Missing 'operation' field in operation data.")
        return value["operation"]
    return getattr(value, "operation")


Operation = Annotated[
    Union[
        Annotated[UploadOperation, Tag(OperationNames.upload)],
        Annotated[DeleteOperation, Tag(OperationNames.delete)],
    ],
    Field(discriminator=Discriminator(operation_discriminator)),
]


class Delivery(BaseModel):
    #: Unique identifier for the delivery. Contains a date that is not in UTC.
    delivery_id: str
    #: Unique identifier for the pushing entity.
    pushing_entity_id: str
    #: Unique identifier for the product.
    product_id: str
    #: Unique identifier for the dataset.
    dataset_id: str
    #: List of operations associated with the delivery.
    #: These operations will be done sequentially in the order they are listed.
    operations: list[Operation] = Field(default_factory=list)

    #: status of the delivery in the OPDV system.
    #: todo: The delivery has not been picked up yet by the OPDV system.
    #: in_progress: The delivery is being processed by the OPDV system.
    #: done: The delivery has been processed successfully by the OPDV system.
    #: partial_error: The delivery has been partially processed by the OPDV system. Some files or operations may have failed.
    #: error: The delivery failed to be processed by the OPDV system.
    status: DeliveryStatus = Field(default=DeliveryStatus.pending)
    #: last updated status timestamp in ISO 8601 format (UTC)
    status_timestamp: str | None = None
    #: Optional error message if something failed or partially failed.
    #: Please check the individual files for more details.
    #: For further help, please contact the User Support team.
    error_message: str | None = None


class ErrorResponseFile(BaseModel):
    """Generic class for any invalid or errored file"""

    local_path: Path
    reason: str

    def __str__(self) -> str:
        return f"{self.local_path}: {self.reason}"

    __repr__ = __str__


class InvalidFile(ErrorResponseFile): ...
