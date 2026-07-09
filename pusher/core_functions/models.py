from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from delivery_common.domain import (
    ErrorResponseFile,
    InvalidFile,
    PushingEntities,
    S3Path,
    UploadValidationResult,
)


def get_ingestion_bucket_name(
    pushing_entity_id: str, pushing_entities: PushingEntities
) -> str | None:
    return next(
        (
            pu.bucket
            for pu in pushing_entities.pushing_entities
            if pu.name == pushing_entity_id
        ),
        None,
    )


class S3File(BaseModel):
    local_path: Path
    s3_path: S3Path
    e_tag: str


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
    files_uploaded: list[str] = Field(default_factory=list)
    #: Potential user errors (user must fix).
    #: TODO: I think validation errors should be fatal contrary to upload errors.
    files_invalid: list[InvalidFile] = Field(default_factory=list)
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
