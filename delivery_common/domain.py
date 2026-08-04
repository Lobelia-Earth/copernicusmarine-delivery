import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generic, Literal, NewType, TypeVar

import yaml
from pydantic import BaseModel, Field, SerializeAsAny, field_validator, model_validator

##############
# Utils
##############


def now_in_utc_isoformat() -> str:
    """Returns the current time in UTC in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


#############

# TODO: Be sure we use this S3 path where we should
# i.e only when sending to S3. All the rest, we want a relative path
# that is used to find the file locally, in the manifest, and
# as the suffix of the S3 key.
S3Path = NewType("S3Path", str)
# TODO: see if an Enum wouldn't be better to avoid the type ignore
OperationNames = Literal["upload", "delete"]

T = TypeVar("T")
# Generic type for ManifestFile and its subclasses
F = TypeVar("F", bound="ManifestFile")


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

        We need to make sure we retrieve and save the right path in the manifest.
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

    #: last updated status timestamp in ISO 8601 format (UTC)
    status_timestamp: str | None = None
    #: Optional error message if the file failed to be uploaded.
    error: str | None = None

    def set_success_status(self) -> None:
        raise NotImplementedError("This method should be implemented in subclasses.")

    def set_backup_success_status(self) -> None:
        raise NotImplementedError("This method should be implemented in subclasses.")

    def set_error_status(self, error_message: str) -> None:
        self.status = "error"
        self.error = error_message


class UploadFile(ManifestFile):
    #: Status of the file in the OPDV system
    #: todo: The file has not been picked up yet by the OPDV system.
    #: validated: The file has been validated by the OPDV system. Will be processed.
    #: published: The file has been published to MDS service.
    #: error: The file failed to be uploaded.
    status: Literal["todo", "validated", "published", "error"] = "todo"
    #: Estimation of the size of the file in MB.
    file_size_mb: int | None
    #: checksum of the file to be uploaded.
    checksum: str | None
    #: Upload time from the users machine to the OPDV system in seconds.
    upload_duration_seconds: float | None

    def set_success_status(self) -> None:
        self.status = "published"


class DeleteFile(ManifestFile):
    #: Status of the file in the OPDV system
    #: todo: The file has not been picked up yet by the OPDV system.
    #: validated: The file has been validated by the OPDV system. Will be processed.
    #: deleted: The file has been deleted from the MDS service.
    #: error: The file failed to be deleted.
    status: Literal["todo", "validated", "deleted", "error"] = "todo"

    def set_success_status(self) -> None:
        self.status = "deleted"


class OperationChangelogEntry(BaseModel):
    #: Different steps for an operation.
    #: creation: The operation is being created by the user.
    #: push: The operation is being push from a user to the OPDV system.
    #: validate: The operation is being validated by the OPDV system.
    #: publish and delete: The operation is being processed by the OPDV system.
    #: backup: The operation is being backed up by the OPDV system.
    step: Literal["creation", "push", "validate", "publish", "delete", "backup"]
    #: ISO 8601 formatted
    timestamp: str = Field(default_factory=now_in_utc_isoformat)
    #: status of the operation in the OPDV system
    step_status: Literal["success", "partial_error", "error"]
    #: Optional error message if the operation failed to be processed by the OPDV system.
    error: str | None = None
    #: Optional comment for the operation step.
    #: Can be especially useful for the backup step, there might be different backup strategies
    #: and we might want to keep track of which one was used.
    comment: str | None = None


class Operation(BaseModel, Generic[F]):
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
    #: Changelog of the operation. Allows to keep track of the status changes and error messages.
    #: intended for debugging and auditing purposes. Not intended for the user.
    changelog: list[OperationChangelogEntry] = []
    #: List of files associated with the operation.
    files: list[F]

    def __init__(self, **data):
        super().__init__(**data)
        if not self.changelog:
            self.add_changelog_entry(step="creation", step_status="success")

    def add_changelog_entry(
        self,
        step: Literal["creation", "push", "validate", "publish", "delete", "backup"],
        step_status: Literal["success", "partial_error", "error"],
        error: str | None = None,
        comment: str | None = None,
    ) -> None:

        self.changelog.append(
            OperationChangelogEntry(
                step=step,
                step_status=step_status,
                error=error,
                comment=comment,
            )
        )


class UploadOperation(Operation[UploadFile]):
    operation: OperationNames = "upload"
    #: Upload time from the users machine to the OPDV system in seconds for the whole operation.
    upload_duration_seconds: float | None

    def total_size(self) -> int:
        """Returns the total size of the files in the operation in MB."""
        return sum(f.file_size_mb or 0 for f in self.files)


class DeleteOperation(Operation[DeleteFile]):
    operation: OperationNames = "delete"


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
    operations: list[SerializeAsAny[Operation]]

    @model_validator(mode="before")
    @classmethod
    def _parse_operations(cls, data: Any) -> Any:
        if isinstance(data, dict) and "operations" in data:
            parsed = []
            for op in data["operations"]:
                if isinstance(op, dict):
                    op_type = op.get("operation")
                    if op_type == "upload":
                        model_cls = UploadOperation
                    elif op_type == "delete":
                        model_cls = DeleteOperation
                    else:
                        model_cls = Operation
                    parsed.append(model_cls(**op))
                else:
                    parsed.append(op)
            data["operations"] = parsed
        return data

    #: ISO 8601 formatted timestamp in UTC for the creation of the delivery.
    #: It corresponds to the moment the manifest is sent to the OPDV system.
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


class ErrorResponseFile(BaseModel):
    """Generic class for any invalid or errored file"""

    local_path: Path
    reason: str

    def __str__(self) -> str:
        return f"{self.local_path}: {self.reason}"

    __repr__ = __str__


class InvalidFile(ErrorResponseFile): ...


class ValidationResult(BaseModel, Generic[T]):
    duplicate_files: list[T]


class ValidationError(BaseModel, Generic[T]):
    reason: str  # invalid, duplicates, etc
    files: list[T]

    def __str__(self) -> str:
        return f"{self.reason} - {', '.join(str(f) for f in self.files)}"

    __repr__ = __str__
