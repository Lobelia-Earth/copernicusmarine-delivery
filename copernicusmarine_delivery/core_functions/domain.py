from pathlib import Path
from typing import Literal, NewType

from pydantic import BaseModel, ConfigDict, Field, field_validator

from copernicusmarine_delivery.logger import logger
from delivery_common.domain import (
    DeleteFile,
    ErrorResponseFile,
    InvalidFile,
    OperationNames,
    PushingEntity,
)

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


class GetSummaryResponse(BaseModel):
    message: str
    uploads: int
    failed_uploads: int
    deletes: int


class BaseResponse(BaseModel):
    #: Delivery ID.
    delivery_id: str | None = None
    #: Product ID.
    product_id: str | None = None
    #: Dataset ID.
    dataset_id: str | None = None
    #: Pushing entity ID.
    pushing_entity_id: str | None = None
    #: Any error that may prematurely stop the delivery.
    fatal_error: str | None = None
    #: Dry run flag, if True, no actual operation was performed in S3.
    dry_run: bool | None = None

    def _get_summary(self) -> GetSummaryResponse:
        """
        Return the summary message and the upload/failed/delete counts.

        :return: A tuple containing the summary message, number of uploads, number of failed uploads, and number of deletes.
            message: str - The summary message.
            uploads: int - The number of successful uploads.
            failed_uploads: int - The number of failed uploads.
            deletes: int - The number of deletes.
        """
        raise NotImplementedError("This method should be implemented in subclasses.")

    def __str__(self) -> str:
        to_print: str = ""
        prefix = "[DRY RUN] " if self.dry_run else ""
        verb = "would be" if self.dry_run else "have been"
        if self.dry_run:
            to_print += f"\n{prefix}The following operations {verb} submitted:\n"

        summary = self._get_summary()
        saw_upload_operation = bool(summary.uploads or summary.failed_uploads)
        if self.dry_run:
            to_print += summary.message

        to_print += f"\n{prefix}Delivery summary:\n\n"
        to_print += f"\tdelivery_id: {self.delivery_id}\n"
        to_print += f"\tpushing_entity_id: {self.pushing_entity_id}\n"
        to_print += f"\tproduct_id: {self.product_id}\n"
        to_print += f"\tdataset_id: {self.dataset_id}\n"
        deletes_message = (
            f"{summary.deletes} file{'s' if summary.deletes != 1 else ''} to delete" if summary.deletes else ""
        )
        if saw_upload_operation:
            uploads_message = (
                f"{summary.uploads} file{'s' if summary.uploads != 1 else ''} to upload"
                if self.dry_run
                else f"{summary.uploads} files uploaded"
            )
            if deletes_message:
                deletes_message = ", " + deletes_message
        else:
            uploads_message = ""
        failed_uploads_message = (
            f", {summary.failed_uploads} file{'s' if summary.failed_uploads != 1 else ''} failed to upload"
            if summary.failed_uploads
            else ""
        )
        to_print += f"\n\tTotal: {uploads_message}{failed_uploads_message}{deletes_message}.\n"
        if summary.failed_uploads:
            to_print += (
                f"\n{prefix}WARNING: {summary.failed_uploads} file{'s' if summary.failed_uploads != 1 else ''} "
                "failed to upload. The delivery completed with errors, check the logs for details.\n"
            )
        return to_print


class ResponseUpload(BaseResponse):
    """Metadata returned when using :func:`~copernicusmarine_delivery.upload`"""

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
        product_id: str,
        dataset_id: str,
        pushing_entity_id: str,
        dry_run: bool,
        result_upload: PutFilesResult,
    ) -> "ResponseUpload":
        return cls(
            delivery_id=delivery_id,
            product_id=product_id,
            pushing_entity_id=pushing_entity_id,
            dataset_id=dataset_id,
            dry_run=dry_run,
            files_uploaded=[
                (file.local_path, get_s3_key_suffix(file.ingestion_system_s3_path))
                for file in result_upload.successful_files
            ],
            files_failed=result_upload.errored_files,
        )

    def _get_summary(self) -> GetSummaryResponse:
        message = ""
        for local_file_path, s3_key_suffix in self.files_uploaded:
            message += f"\t[UPLOAD] {local_file_path} -> {s3_key_suffix}\n"
        return GetSummaryResponse(
            message=message,
            uploads=len(self.files_uploaded),
            failed_uploads=len(self.files_failed),
            deletes=0,
        )


class ResponseDelete(BaseResponse):
    """Metadata returned when using :func:`~copernicusmarine_delivery.delete`"""

    files_to_delete: list[DeleteFile] = Field(default_factory=list)

    @classmethod
    def create_from_fatal_error(cls, fatal_error: str) -> "ResponseDelete":
        return cls(fatal_error=fatal_error)

    @classmethod
    def create(
        cls,
        delivery_id: str,
        product_id: str,
        dataset_id: str,
        pushing_entity_id: str,
        dry_run: bool,
        files_to_delete: list[DeleteFile],
    ) -> "ResponseDelete":
        return cls(
            delivery_id=delivery_id,
            product_id=product_id,
            dataset_id=dataset_id,
            dry_run=dry_run,
            pushing_entity_id=pushing_entity_id,
            files_to_delete=files_to_delete,
        )

    def _get_summary(self) -> GetSummaryResponse:
        message = ""
        for file in self.files_to_delete:
            message += f"\t[DELETE] {file.key_suffix}\n"
        return GetSummaryResponse(message=message, uploads=0, failed_uploads=0, deletes=len(self.files_to_delete))


class ResponseDelivery(BaseResponse):
    """Metadata returned when using :func:`~copernicusmarine_delivery.delivery`"""

    #: List of responses for each operation in the delivery.
    operations_responses: list[ResponseUpload | ResponseDelete] = Field(default_factory=list)

    @classmethod
    def create(
        cls,
        delivery_id: str,
        product_id: str,
        dataset_id: str,
        pushing_entity_id: str,
        dry_run: bool,
        operations_responses: list[ResponseUpload | ResponseDelete],
    ) -> "ResponseDelivery":
        return cls(
            delivery_id=delivery_id,
            product_id=product_id,
            dataset_id=dataset_id,
            pushing_entity_id=pushing_entity_id,
            dry_run=dry_run,
            operations_responses=operations_responses,
        )

    def _get_summary(self) -> GetSummaryResponse:
        message, uploads, failed_uploads, deletes = "", 0, 0, 0
        for response in self.operations_responses:
            response_summary = response._get_summary()
            message += response_summary.message
            uploads += response_summary.uploads
            failed_uploads += response_summary.failed_uploads
            deletes += response_summary.deletes
        return GetSummaryResponse(message=message, uploads=uploads, failed_uploads=failed_uploads, deletes=deletes)


class _BaseOperation(BaseModel):
    files: list[str]

    def add(self, file: str) -> None:
        """Add a file to the operation.

        :param file: Path of the file. See `File paths and anchors` in the documentation.
        """
        self.files.append(file)


class Upload(_BaseOperation):
    operation: Literal[OperationNames.upload] = OperationNames.upload
    anchor: str | None = None


class Delete(_BaseOperation):
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
        super().__init__(f"All uploads failed. Errored files: {[file.local_path for file in error_files]}")


class NoIngestionBucketError(Exception):
    """
    Raised when the ingestion bucket is not found.
    """

    def __init__(self, pushing_entity_id: str):
        super().__init__(
            f"No ingestion bucket found for pushing entity: {pushing_entity_id} Please contact User Support."
        )


class InvalidFilesError(Exception):
    """
    Raised when an error occurs during the validation of files.
    Will list the files and their errors that failed validation.
    """

    def __init__(self, invalid_files: list[InvalidFile]):
        for file in invalid_files:
            logger.error(f"Invalid file: {file}")
        super().__init__(f"Found {len(invalid_files)} invalid files. See logs for details.")


class OIDCConfig(BaseModel):
    oidc_provider_url: str
    oidc_client_id: str
    scope: str = "openid"
    grant_type: str = "password"


# model_config to allow extra fields to allow us to potentially add them without
# breaking the toolbox in the future.
class GetConfigResponse(BaseModel):
    oidc_config: OIDCConfig

    model_config = ConfigDict(extra="allow")


class GetPushingEntityConfigResponse(BaseModel):
    pushing_entity: PushingEntity
    s3_endpoint_url: str

    model_config = ConfigDict(extra="allow")
