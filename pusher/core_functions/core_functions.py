import os
from pathlib import Path

import yaml

from delivery_common.domain import (
    DeleteFile,
    DeleteOperation,
    DeleteValidationResult,
    Manifest,
    Operation,
    OperationNames,
    UploadFile,
    UploadOperation,
    UploadValidationResult,
    ValidationError,
    ValidationResult,
)
from delivery_common.manifest import create_manifest, create_manifest_id
from delivery_common.validation import validate_delivery_ids
from pusher.core_functions.constants import (
    DEFAULT_CHUNK_SIZE_MB,
    DONE_MANIFESTS_PATH,
    FAILED_MANIFESTS_PATH,
    IN_PROGRESS_MANIFESTS_PATH,
    NEW_DATA_BUCKET_PATH,
    NEW_MANIFESTS_PATH,
)
from pusher.core_functions.delivery_validator import (
    delete_files_validation,
    fetch_pushing_entities,
    upload_files_validation,
)
from pusher.core_functions.domain import (
    PutFilesResult,
    ResponseDelete,
    ResponseDelivery,
    ResponseUpload,
)
from pusher.core_functions.utils import get_ingestion_bucket_name, megabytes_to_bytes
from pusher.logger import logger
from pusher.s3_client import S3Client, get_s3_ingestion_client


def get_local_path_s3_keys_mapping(
    list_of_files: list[str],
    manifest_id: str,
    product_id: str,
    dataset_id: str,
) -> dict[Path, str]:
    return {
        Path(file_path): NEW_DATA_BUCKET_PATH.format(
            manifest_id=manifest_id,
            product_id=product_id,
            dataset_id=dataset_id,
            file_name=file_path,
        )
        for file_path in list_of_files
    }


def get_manifest_destination_key(manifest_id: str) -> str:
    return NEW_MANIFESTS_PATH.format(manifest_id=manifest_id)


def upload(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    files: list[str],
    max_concurrent_uploads: int,
    chunk_size_bytes: int,
    chunk_concurrency: int,
) -> tuple[ResponseUpload, Manifest | None]:
    """
    1. Quick-validate all files, keep track of invalid files. If no valid files, return early.
    2. Try and upload all files given. Keep track of errored files. If no successful uploads, return early.
    3. Create Manifest with successful ones (in the future there might be a flag to abort if errors). Use ETag as checksum.
    """

    logger.debug(
        f"Creating release for:\n\tPU: {pushing_entity_id}\n\tProduct ID: {product_id}\n\tDataset ID: {dataset_id}"
        f"\n\tFiles: {[Path(file).name for file in files]}"
    )

    pushing_entities = fetch_pushing_entities()
    invalid_delivery_ids_response = validate_delivery_ids(
        pushing_entity_id, product_id, dataset_id, pushing_entities
    )
    if invalid_delivery_ids_response:
        logger.error(
            "The ids provided for this delivery did not match our records, "
            f"see: {invalid_delivery_ids_response.reason}"
        )
        return (
            ResponseUpload.create_from_fatal_error(
                invalid_delivery_ids_response.reason
            ),
            None,
        )

    upload_operation, validation_result = create_and_validate_upload_operation(
        [Path(file_) for file_ in files]
    )

    if validation_result.duplicate_files:
        duplicate_files_error_response = (
            "The following files are duplicated. No manifest will be created.\n"
            f"{validation_result.duplicate_files}"
        )
        logger.error(duplicate_files_error_response)
        return (
            ResponseUpload.create_from_fatal_error(duplicate_files_error_response),
            None,
        )

    if not validation_result.files_valid:
        no_valid_files_fatal_error_response = (
            "No file passed the validation. No manifest will be created."
        )
        logger.error(no_valid_files_fatal_error_response)
        return (
            ResponseUpload.create_from_fatal_error(no_valid_files_fatal_error_response),
            None,
        )
    ingestion_bucket_name = get_ingestion_bucket_name(
        pushing_entity_id, pushing_entities
    )
    if not ingestion_bucket_name:
        return (
            ResponseUpload.create_from_fatal_error(
                f"{pushing_entity_id} is not associated with any ingestion bucket."
            ),
            None,
        )
    s3_client = get_s3_ingestion_client(
        pushing_entity_id, ingestion_bucket_name, chunk_concurrency=chunk_concurrency
    )
    manifest_id = create_manifest_id(product_id)
    put_files_result = _put_files_to_ingestion_system(
        s3_client,
        manifest_id=manifest_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operation=upload_operation,
        chunk_size=chunk_size_bytes,
        max_concurrent_uploads=max_concurrent_uploads,
    )

    if not put_files_result.successful_files:
        no_valid_files_fatal_error_response = (
            "No successful uploads - no data were sent."
        )
        logger.error(no_valid_files_fatal_error_response)
        return (
            ResponseUpload.create_from_fatal_error(no_valid_files_fatal_error_response),
            None,
        )
    _update_operation_with_put_results(upload_operation, put_files_result)

    manifest = _create_and_upload_manifest(
        s3_client,
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=[upload_operation],
        manifest_id=manifest_id,
    )

    return (
        ResponseUpload.create(
            delivery_id=manifest.manifest_id,
            result_validation=validation_result,
            result_upload=put_files_result,
        ),
        manifest,
    )


def delete(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    files: list[str],
) -> tuple[ResponseDelete, Manifest | None]:
    """
    Create manifest with deletes and push it. Deletes happen in main S3; toolbox has no direct access.
    """
    logger.debug(
        f"Creating release for:\n\tPU: {pushing_entity_id}\n\tProduct ID: {product_id}\n\tDataset ID: {dataset_id}"
        f"\n\tFiles: {files}"
    )
    pushing_entities = fetch_pushing_entities()
    invalid_delivery_ids_response = validate_delivery_ids(
        pushing_entity_id, product_id, dataset_id, pushing_entities
    )

    delete_operation, validation_result = create_and_validate_delete_operation(files)

    if validation_result.duplicate_files:
        duplicate_files_error_response = (
            "The following files are duplicated. No manifest will be created.\n"
            f"{validation_result.duplicate_files}"
        )
        logger.error(duplicate_files_error_response)
        return (
            ResponseDelete.create_from_fatal_error(duplicate_files_error_response),
            None,
        )

    if invalid_delivery_ids_response:
        logger.error(
            "The ids provided for this delivery did not match our records, "
            f"see: {invalid_delivery_ids_response.reason}"
        )
        return (
            ResponseDelete.create_from_fatal_error(
                invalid_delivery_ids_response.reason
            ),
            None,
        )

    ingestion_bucket_name = get_ingestion_bucket_name(
        pushing_entity_id, pushing_entities
    )
    if not ingestion_bucket_name:
        return (
            ResponseDelete.create_from_fatal_error(
                f"{pushing_entity_id} is not associated with any ingestion bucket."
            ),
            None,
        )
    s3_client = get_s3_ingestion_client(pushing_entity_id, ingestion_bucket_name)

    manifest = _create_and_upload_manifest(
        s3_client,
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=[delete_operation],
    )
    return ResponseDelete.create(delivery_id=manifest.manifest_id), manifest


def create_and_validate_delete_operation(
    files: list[str],
) -> tuple[DeleteOperation, DeleteValidationResult]:
    validation_result = delete_files_validation(files)
    return (
        DeleteOperation(
            files=[DeleteFile(key_suffix=file) for file in files],
        ),
        validation_result,
    )


def delivery(
    operations: list[tuple[OperationNames, list[str]]],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    max_concurrent_uploads: int,
    chunk_size_bytes: int,
    chunk_concurrency: int,
) -> tuple[ResponseDelivery, Manifest | None]:

    pushing_entities = fetch_pushing_entities()
    invalid_delivery_ids_response = validate_delivery_ids(
        pushing_entity_id, product_id, dataset_id, pushing_entities
    )
    if invalid_delivery_ids_response:
        logger.error(
            "The ids provided for this delivery did not match our records, "
            f"see: {invalid_delivery_ids_response.reason}"
        )
        return (
            ResponseDelivery.create_from_fatal_error(
                invalid_delivery_ids_response.reason
            ),
            None,
        )

    manifest_id = create_manifest_id(product_id)
    all_operations: list[Operation] = []
    validation_results: list[ValidationResult] = []
    ingestion_bucket_name = get_ingestion_bucket_name(
        pushing_entity_id, pushing_entities
    )
    if not ingestion_bucket_name:
        return (
            ResponseDelivery.create_from_fatal_error(
                f"{pushing_entity_id} is not associated with any ingestion bucket."
            ),
            None,
        )
    s3_client = get_s3_ingestion_client(
        pushing_entity_id, ingestion_bucket_name, chunk_concurrency=chunk_concurrency
    )
    for operation_name, sources in operations:
        if operation_name == "delete":
            operation, validation_result = create_and_validate_delete_operation(sources)
            all_operations.append(operation)
            validation_results.append(validation_result)
        elif operation_name == "upload":
            operation, validation_result = create_and_validate_upload_operation(
                [Path(file_) for file_ in sources]
            )
            all_operations.append(operation)
            validation_results.append(validation_result)
    if validation_errors := _get_validation_errors(validation_results):
        # TODO: this needs to be consistent accross the toolbox.
        # For now, any validation error will cancel the delivery.
        logger.error(
            f"Some files failed validation: {validation_errors}. Delivery cancelled. No manifest will be created."
        )
        return (
            ResponseDelivery.create_from_fatal_error(
                fatal_error=f"Some files failed validation: {validation_errors}. Delivery cancelled. No manifest will be created."
            ),
            None,
        )
    all_responses: list[ResponseUpload | ResponseDelete] = []
    for operation, validation_result in zip(all_operations, validation_results):
        if isinstance(operation, UploadOperation):
            put_files_result = _put_files_to_ingestion_system(
                s3_client,
                manifest_id=manifest_id,
                product_id=product_id,
                dataset_id=dataset_id,
                operation=operation,
                chunk_size=chunk_size_bytes,
                max_concurrent_uploads=max_concurrent_uploads,
            )
            _update_operation_with_put_results(operation, put_files_result)
            all_responses.append(
                ResponseUpload.create(
                    delivery_id=manifest_id,
                    result_validation=validation_result,  # type: ignore
                    result_upload=put_files_result,
                )
            )
        elif isinstance(operation, DeleteOperation):
            all_responses.append(ResponseDelete.create(delivery_id=manifest_id))

    manifest = _create_and_upload_manifest(
        s3_client,
        pushing_entity_id,
        product_id,
        dataset_id,
        all_operations,
        manifest_id,
    )
    return (
        ResponseDelivery.create(
            delivery_id=manifest_id, operations_responses=all_responses
        ),
        manifest,
    )


def create_and_validate_upload_operation(
    files: list[Path],
) -> tuple[UploadOperation, UploadValidationResult]:
    validation_result = upload_files_validation(files)
    return (
        UploadOperation(
            files=[
                UploadFile(
                    key_suffix=str(file),
                    file_size=os.path.getsize(file) // (1024 * 1024),
                    checksum=None,  # ETag will be filled in after upload
                    upload_time=None,  # will be filled in after upload
                )
                for file in validation_result.files_valid
            ],
        ),
        validation_result,
    )


def _get_validation_errors(
    validation_results: list[ValidationResult],
) -> list[ValidationError]:
    errors = [
        ValidationError(reason="duplicates", files=validation_result.duplicate_files)
        for validation_result in validation_results
        if validation_result.duplicate_files
    ]
    errors += [
        ValidationError(reason="invalid", files=validation_result.files_invalid)
        for validation_result in validation_results
        if isinstance(validation_result, UploadValidationResult)
        and validation_result.files_invalid
    ]
    return errors


def _create_and_upload_manifest(
    s3_client: S3Client,
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    operations: list[Operation],
    manifest_id: str | None = None,
) -> Manifest:
    if not manifest_id:
        manifest_id = create_manifest_id(product_id)
    manifest = create_manifest(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=operations,
        manifest_id=manifest_id,
    )
    manifest_bucket_path = get_manifest_destination_key(manifest.manifest_id)
    logger.debug(f"Uploading delivery document to {manifest_bucket_path}")
    s3_client.upload_fileobj(
        key=manifest_bucket_path,
        file=manifest.model_dump_json().encode(),
        chunk_size=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
    )
    return manifest


def _put_files_to_ingestion_system(
    s3_client: S3Client,
    manifest_id: str,
    product_id: str,
    dataset_id: str,
    operation: UploadOperation,
    chunk_size: int,
    max_concurrent_uploads: int,
) -> PutFilesResult:

    local_path_s3_keys_mapping = get_local_path_s3_keys_mapping(
        [file_.key_suffix for file_ in operation.files],
        manifest_id,
        product_id,
        dataset_id,
    )
    put_files_result = s3_client.upload_multiple_files(
        local_path_s3_keys_mapping,
        chunk_size,
        max_concurrent_uploads,
    )
    return put_files_result


def _update_operation_with_put_results(
    operation: UploadOperation, put_files_result: PutFilesResult
) -> None:
    """
    TODO: add the possibility for users to abort the delivery if there are any errors. For now, we just log them and continue.

    Might be the default one.
    """
    successful_files_dict = {
        str(file.local_path): file for file in put_files_result.successful_files
    }
    errored_files_dict = {
        str(file.local_path): file for file in put_files_result.errored_files
    }
    index_files_to_remove = []
    for i, manifest_file in enumerate(operation.files):
        if manifest_file.key_suffix in successful_files_dict:
            successful_s3_file = successful_files_dict[manifest_file.key_suffix]
            manifest_file.checksum = successful_s3_file.e_tag
            manifest_file.upload_time = successful_s3_file.upload_time
        elif manifest_file.key_suffix in errored_files_dict:
            logger.error(
                f"File {manifest_file.key_suffix} failed to upload: {errored_files_dict[manifest_file.key_suffix].reason}"
            )
            index_files_to_remove.append(i)
    for index in reversed(index_files_to_remove):
        del operation.files[index]


def get_manifest(
    delivery_id: str,
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
) -> Manifest:
    pushing_entities = fetch_pushing_entities()
    ingestion_bucket_name = get_ingestion_bucket_name(
        pushing_entity_id, pushing_entities
    )
    if not ingestion_bucket_name:
        raise ValueError(
            f"{pushing_entity_id} is not associated with any ingestion bucket."
        )
    s3_client = get_s3_ingestion_client(pushing_entity_id, ingestion_bucket_name)
    manifest_new = _get_manifest(
        s3_client, NEW_MANIFESTS_PATH.format(manifest_id=delivery_id)
    )
    if manifest_new:
        return manifest_new
    manifest_in_progress = _get_manifest(
        s3_client,
        IN_PROGRESS_MANIFESTS_PATH.format(manifest_id=delivery_id),
    )
    if manifest_in_progress:
        return manifest_in_progress
    manifest_failed = _get_manifest(
        s3_client,
        FAILED_MANIFESTS_PATH.format(
            product_id=product_id, dataset_id=dataset_id, manifest_id=delivery_id
        ),
    )
    if manifest_failed:
        return manifest_failed
    manifest_done = _get_manifest(
        s3_client,
        DONE_MANIFESTS_PATH.format(
            product_id=product_id, dataset_id=dataset_id, manifest_id=delivery_id
        ),
    )
    if manifest_done:
        return manifest_done
    raise ValueError(
        f"Manifest with id {delivery_id} not found for pushing entity {pushing_entity_id}."
    )


def _get_manifest(
    s3_client: S3Client,
    key: str,
) -> Manifest | None:
    try:
        manifest_stream = s3_client.get_file_stream(key)
        return Manifest.model_validate(yaml.safe_load(manifest_stream))
    except Exception:
        logger.debug(f"Manifest not found at {key}")
        return None
